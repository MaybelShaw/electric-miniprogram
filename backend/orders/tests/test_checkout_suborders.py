from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product, ProductSKU
from orders.models import CheckoutOrder, Payment, SubOrder
from orders.payment_service import PaymentService
from orders.services import create_order_with_split
from stores.models import Store
from users.models import Address


class CheckoutSubOrderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="buyer", password="pwd")
        self.main_store = Store.objects.create(
            name="Main Store",
            code="main-store",
            store_type=Store.TYPE_SELF_OPERATED,
        )
        self.partner_store = Store.objects.create(
            name="Partner Store",
            code="partner-store",
            store_type=Store.TYPE_PARTNER,
        )
        self.address = Address.objects.create(
            user=self.user,
            contact_name="Buyer",
            phone="13800000000",
            province="Beijing",
            city="Beijing",
            district="Haidian",
            detail="No.1 Road",
            is_default=True,
        )
        self.store_a_product = self._create_product(
            self.main_store,
            "Store A Product",
            Decimal("100.00"),
            stock=30,
        )
        self.store_a_sku_red = ProductSKU.objects.create(
            product=self.store_a_product,
            name="Red",
            sku_code="A-RED",
            specs={"color": "red"},
            price=Decimal("100.00"),
            stock=10,
        )
        self.store_a_sku_blue = ProductSKU.objects.create(
            product=self.store_a_product,
            name="Blue",
            sku_code="A-BLUE",
            specs={"color": "blue"},
            price=Decimal("120.00"),
            stock=10,
        )
        self.store_a_second_product = self._create_product(
            self.main_store,
            "Store A Second Product",
            Decimal("200.00"),
            stock=10,
        )
        self.store_b_product = self._create_product(
            self.partner_store,
            "Store B Product",
            Decimal("300.00"),
            stock=10,
        )
        self.store_b_sku = ProductSKU.objects.create(
            product=self.store_b_product,
            name="Default",
            sku_code="B-DEFAULT",
            specs={"size": "std"},
            price=Decimal("300.00"),
            stock=10,
        )

    def _create_product(self, store, name, price, stock):
        category = Category.objects.create(
            store=store,
            name=f"{name} Category",
            level=Category.LEVEL_MAJOR,
        )
        brand = Brand.objects.create(store=store, name=f"{name} Brand")
        return Product.objects.create(
            store=store,
            name=name,
            category=category,
            brand=brand,
            price=price,
            stock=stock,
        )

    def _checkout_items(self):
        return [
            {"product_id": self.store_a_product.id, "sku_id": self.store_a_sku_red.id, "quantity": 2},
            {"product_id": self.store_a_product.id, "sku_id": self.store_a_sku_blue.id, "quantity": 1},
            {"product_id": self.store_a_second_product.id, "quantity": 1},
            {"product_id": self.store_b_product.id, "sku_id": self.store_b_sku.id, "quantity": 1},
        ]

    def test_create_checkout_order_splits_items_by_store_and_product(self):
        order = create_order_with_split(
            user=self.user,
            items=self._checkout_items(),
            address_id=self.address.id,
            payment_method="online",
        )

        checkout = order.checkout_order
        self.assertIsNotNone(checkout)
        self.assertEqual(CheckoutOrder.objects.count(), 1)
        self.assertEqual(checkout.user_id, self.user.id)
        self.assertEqual(checkout.total_amount, Decimal("820.00"))
        self.assertEqual(checkout.actual_amount, Decimal("820.00"))

        suborders = SubOrder.objects.filter(checkout_order=checkout).order_by("store_id", "product_id")
        self.assertEqual(suborders.count(), 3)
        grouped = {(sub.store_id, sub.product_id): sub for sub in suborders}
        same_spu_suborder = grouped[(self.main_store.id, self.store_a_product.id)]
        self.assertEqual(same_spu_suborder.items.count(), 2)
        self.assertEqual(same_spu_suborder.total_amount, Decimal("320.00"))
        self.assertEqual(same_spu_suborder.actual_amount, Decimal("320.00"))

        self.store_a_sku_red.refresh_from_db()
        self.store_a_sku_blue.refresh_from_db()
        self.store_a_second_product.refresh_from_db()
        self.store_b_sku.refresh_from_db()
        self.assertEqual(self.store_a_sku_red.stock, 8)
        self.assertEqual(self.store_a_sku_blue.stock, 9)
        self.assertEqual(self.store_a_second_product.stock, 9)
        self.assertEqual(self.store_b_sku.stock, 9)

    def test_payment_success_marks_checkout_and_all_suborders_paid(self):
        order = create_order_with_split(
            user=self.user,
            items=self._checkout_items(),
            address_id=self.address.id,
            payment_method="online",
        )
        payment = Payment.create_for_order(order, method="wechat", ttl_minutes=10)

        PaymentService.process_payment_success(payment.id, transaction_id="tx-001", operator=self.user)

        payment.refresh_from_db()
        order.checkout_order.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(order.checkout_order.payment_status, "succeeded")
        self.assertEqual(order.checkout_order.status, "paid")
        self.assertEqual(
            set(SubOrder.objects.filter(checkout_order=order.checkout_order).values_list("status", flat=True)),
            {"paid"},
        )
        self.assertEqual(
            set(order.child_orders.values_list("status", flat=True)),
            {"paid"},
        )

    def test_user_order_list_defaults_to_suborders(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post(
            reverse("order-create-batch-orders"),
            {
                "address_id": self.address.id,
                "items": self._checkout_items(),
                "payment_method": "online",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        response = client.get(reverse("order-list"))
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload

        self.assertEqual(len(rows), 3)
        self.assertEqual({row["order_type"] for row in rows}, {"local"})
        self.assertNotIn(
            response.json()["order"]["id"] if isinstance(response.json(), dict) and "order" in response.json() else None,
            {row["id"] for row in rows},
        )

    def test_checkout_rejects_inactive_product(self):
        self.store_b_product.is_active = False
        self.store_b_product.save(update_fields=["is_active"])
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            reverse("order-create-batch-orders"),
            {
                "address_id": self.address.id,
                "items": [{"product_id": self.store_b_product.id, "quantity": 1}],
                "payment_method": "online",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("已下架", response.json()["detail"])

    def test_checkout_rejects_inactive_sku(self):
        self.store_a_sku_red.is_active = False
        self.store_a_sku_red.save(update_fields=["is_active"])
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            reverse("order-create-batch-orders"),
            {
                "address_id": self.address.id,
                "items": [
                    {
                        "product_id": self.store_a_product.id,
                        "sku_id": self.store_a_sku_red.id,
                        "quantity": 1,
                    }
                ],
                "payment_method": "online",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("已下架", response.json()["detail"])

    def test_buyer_store_param_and_other_order_id_do_not_expand_scope(self):
        other_user = get_user_model().objects.create_user(username="other-buyer", password="pwd")
        other_address = Address.objects.create(
            user=other_user,
            contact_name="Other",
            phone="13800000001",
            province="Beijing",
            city="Beijing",
            district="Haidian",
            detail="No.2 Road",
        )
        other_order = create_order_with_split(
            user=other_user,
            items=[{"product_id": self.store_b_product.id, "sku_id": self.store_b_sku.id, "quantity": 1}],
            address_id=other_address.id,
            payment_method="online",
        )
        client = APIClient()
        client.force_authenticate(self.user)

        store_filtered_response = client.get(reverse("order-my-orders"), {"store": self.partner_store.id})
        other_detail_response = client.get(reverse("order-detail", args=[other_order.id]))

        self.assertEqual(store_filtered_response.status_code, 403)
        self.assertEqual(other_detail_response.status_code, 404)
