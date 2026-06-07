from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product, ProductSKU
from orders.services import create_order_with_split
from stores.models import (
    Store,
    StoreCustomerGroup,
    StoreCustomerGroupMember,
    StoreCustomerGroupPrice,
    StoreMember,
)
from users.models import Address, User


class StoreCustomerGroupPricingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.store_a = Store.objects.create(
            name="Store A",
            code="store-a",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.store_b = Store.objects.create(
            name="Store B",
            code="store-b",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.user = User.objects.create_user(username="buyer", password="password", phone="13800000000")
        self.admin = User.objects.create_user(username="store-admin", password="password", is_staff=True, role="admin")
        StoreMember.objects.create(user=self.admin, store=self.store_a, role=StoreMember.ROLE_STORE_ADMIN)

    def create_product(self, store, name, price="100.00", *, source=Product.SOURCE_LOCAL):
        category = Category.objects.create(name=f"{name} category", store=store, level=Category.LEVEL_MAJOR)
        brand = Brand.objects.create(name=f"{name} brand", store=store)
        kwargs = {}
        if source == Product.SOURCE_HAIER:
            kwargs["product_code"] = f"H{name}"
        return Product.objects.create(
            name=name,
            category=category,
            brand=brand,
            store=store,
            price=Decimal(price),
            stock=10,
            source=source,
            **kwargs,
        )

    def create_address(self):
        return Address.objects.create(
            user=self.user,
            contact_name="Tester",
            phone="13800000000",
            province="Zhejiang",
            city="Hangzhou",
            district="Xihu",
            detail="No.1",
        )

    def test_user_can_belong_to_one_group_per_store_and_multiple_stores(self):
        group_a = StoreCustomerGroup.objects.create(store=self.store_a, name="A VIP")
        group_b = StoreCustomerGroup.objects.create(store=self.store_b, name="B Project")
        StoreCustomerGroupMember.objects.create(store=self.store_a, group=group_a, user=self.user)
        StoreCustomerGroupMember.objects.create(store=self.store_b, group=group_b, user=self.user)

        duplicate = StoreCustomerGroupMember(store=self.store_a, group=group_a, user=self.user, phone="13900000000")

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

        self.assertEqual(StoreCustomerGroupMember.objects.filter(user=self.user).count(), 2)

    def test_product_display_price_uses_store_group_price_and_falls_back_to_default(self):
        group_a = StoreCustomerGroup.objects.create(store=self.store_a, name="A VIP")
        StoreCustomerGroupMember.objects.create(store=self.store_a, group=group_a, user=self.user)
        product_a = self.create_product(self.store_a, "A product", "100.00")
        product_b = self.create_product(self.store_b, "B product", "200.00")
        StoreCustomerGroupPrice.objects.create(group=group_a, product=product_a, price=Decimal("88.00"))

        self.client.force_authenticate(self.user)
        response_a = self.client.get(f"/api/catalog/products/{product_a.id}/", {"store_id": self.store_a.id})
        response_b = self.client.get(f"/api/catalog/products/{product_b.id}/", {"store_id": self.store_b.id})

        self.assertEqual(response_a.status_code, 200, response_a.content)
        self.assertEqual(Decimal(str(response_a.data["display_price"])), Decimal("88.00"))
        self.assertEqual(response_a.data["customer_group_name"], "A VIP")
        self.assertEqual(Decimal(str(response_b.data["display_price"])), Decimal("200.00"))
        self.assertIsNone(response_b.data["customer_group_id"])

    def test_pending_phone_membership_is_resolved_when_user_browses(self):
        group = StoreCustomerGroup.objects.create(store=self.store_a, name="Phone group")
        membership = StoreCustomerGroupMember.objects.create(
            store=self.store_a,
            group=group,
            phone="13800000000",
        )
        product = self.create_product(self.store_a, "Phone product", "100.00")
        StoreCustomerGroupPrice.objects.create(group=group, product=product, price=Decimal("66.00"))

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/catalog/products/{product.id}/", {"store_id": self.store_a.id})

        membership.refresh_from_db()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(membership.user_id, self.user.id)
        self.assertEqual(Decimal(str(response.data["display_price"])), Decimal("66.00"))

    def test_sku_display_price_uses_sku_group_price(self):
        group = StoreCustomerGroup.objects.create(store=self.store_a, name="SKU group")
        StoreCustomerGroupMember.objects.create(store=self.store_a, group=group, user=self.user)
        product = self.create_product(self.store_a, "SKU product", "100.00")
        sku = ProductSKU.objects.create(product=product, name="Large", sku_code="L", price=Decimal("120.00"), stock=5)
        StoreCustomerGroupPrice.objects.create(group=group, product=product, sku=sku, price=Decimal("90.00"))

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/catalog/products/{product.id}/", {"store_id": self.store_a.id})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Decimal(str(response.data["display_price"])), Decimal("90.00"))
        self.assertEqual(Decimal(str(response.data["skus"][0]["display_price"])), Decimal("90.00"))

    def test_sku_group_price_falls_back_to_product_group_price(self):
        group = StoreCustomerGroup.objects.create(store=self.store_a, name="SKU fallback group")
        StoreCustomerGroupMember.objects.create(store=self.store_a, group=group, user=self.user)
        product = self.create_product(self.store_a, "SKU fallback product", "100.00")
        ProductSKU.objects.create(product=product, name="Large", sku_code="LF", price=Decimal("120.00"), stock=5)
        StoreCustomerGroupPrice.objects.create(group=group, product=product, price=Decimal("95.00"))

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/catalog/products/{product.id}/", {"store_id": self.store_a.id})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Decimal(str(response.data["skus"][0]["display_price"])), Decimal("95.00"))

    def test_haier_product_does_not_accept_group_price(self):
        group = StoreCustomerGroup.objects.create(store=self.store_a, name="Haier group")
        StoreCustomerGroupMember.objects.create(store=self.store_a, group=group, user=self.user)
        product = self.create_product(self.store_a, "Haier", "300.00", source=Product.SOURCE_HAIER)
        price = StoreCustomerGroupPrice(group=group, product=product, price=Decimal("1.00"))

        with self.assertRaises(ValidationError):
            price.full_clean()

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/catalog/products/{product.id}/", {"store_id": self.store_a.id})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.data["customer_group_id"])

    def test_order_locks_customer_group_price(self):
        group = StoreCustomerGroup.objects.create(store=self.store_a, name="Order group")
        StoreCustomerGroupMember.objects.create(store=self.store_a, group=group, user=self.user)
        product = self.create_product(self.store_a, "Order product", "100.00")
        StoreCustomerGroupPrice.objects.create(group=group, product=product, price=Decimal("75.00"))
        address = self.create_address()

        order = create_order_with_split(
            self.user,
            items=[{"product_id": product.id, "quantity": 2}],
            address_id=address.id,
        )
        item = order.items.first()

        self.assertEqual(item.unit_price, Decimal("75.00"))
        self.assertEqual(item.actual_amount, Decimal("150.00"))
        self.assertEqual(order.actual_amount, Decimal("150.00"))

    def test_store_admin_can_manage_own_group_but_not_other_store_group(self):
        self.client.force_authenticate(self.admin)

        own_response = self.client.post(
            "/api/stores/customer-groups/",
            {"store": self.store_a.id, "name": "Own group", "status": "active"},
            format="json",
        )
        other_response = self.client.post(
            "/api/stores/customer-groups/",
            {"store": self.store_b.id, "name": "Other group", "status": "active"},
            format="json",
        )

        self.assertEqual(own_response.status_code, 201, own_response.content)
        self.assertEqual(other_response.status_code, 403)

    def test_store_admin_can_toggle_group_name_display_only(self):
        self.client.force_authenticate(self.admin)

        toggle_response = self.client.patch(
            f"/api/stores/{self.store_a.id}/",
            {"show_customer_group_name": True},
            format="json",
        )
        rename_response = self.client.patch(
            f"/api/stores/{self.store_a.id}/",
            {"name": "Renamed"},
            format="json",
        )

        self.store_a.refresh_from_db()
        self.assertEqual(toggle_response.status_code, 200, toggle_response.content)
        self.assertTrue(self.store_a.show_customer_group_name)
        self.assertEqual(rename_response.status_code, 403)

    def test_backend_account_can_bind_only_one_non_platform_store(self):
        user = User.objects.create_user(username="single-store-admin", password="password", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.store_a, role=StoreMember.ROLE_STORE_ADMIN)

        with self.assertRaises(ValidationError):
            StoreMember.objects.create(user=user, store=self.store_b, role=StoreMember.ROLE_STORE_STAFF)
