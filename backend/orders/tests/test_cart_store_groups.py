from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from orders.models import Cart, CartItem
from stores.models import Store


class CartStoreGroupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="cart-buyer", password="pwd")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.cart = Cart.objects.create(user=self.user)

        self.main_store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.partner_store = Store.objects.create(
            name="Partner Store",
            code="partner-cart-store",
            store_type=Store.TYPE_PARTNER,
        )
        self.main_product = self._create_product(self.main_store, "Main Product")
        self.partner_product = self._create_product(self.partner_store, "Partner Product")
        self.partner_second_product = self._create_product(self.partner_store, "Partner Second Product")

    def _create_product(self, store, name):
        category = Category.objects.create(store=store, name=f"{name} Category", level=Category.LEVEL_MAJOR)
        brand = Brand.objects.create(store=store, name=f"{name} Brand")
        return Product.objects.create(
            store=store,
            name=name,
            category=category,
            brand=brand,
            price=Decimal("100.00"),
            stock=10,
        )

    def test_my_cart_groups_items_by_store_in_cart_item_order(self):
        CartItem.objects.create(cart=self.cart, product=self.partner_product, quantity=1)
        CartItem.objects.create(cart=self.cart, product=self.main_product, quantity=2)
        CartItem.objects.create(cart=self.cart, product=self.partner_second_product, quantity=3)

        response = self.client.get(reverse("cart-my-cart"))

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 3)
        self.assertEqual(
            [group["store_id"] for group in payload["store_groups"]],
            [self.partner_store.id, self.main_store.id],
        )
        self.assertEqual(payload["store_groups"][0]["store_name"], "Partner Store")
        self.assertFalse(payload["store_groups"][0]["store_is_main"])
        self.assertEqual(payload["store_groups"][0]["item_count"], 2)
        self.assertEqual(payload["store_groups"][0]["total_quantity"], 4)
        self.assertEqual(payload["store_groups"][1]["item_count"], 1)
        self.assertTrue(payload["store_groups"][1]["store_is_main"])
        self.assertEqual(payload["store_groups"][1]["items"][0]["store_id"], self.main_store.id)
        self.assertTrue(payload["store_groups"][1]["items"][0]["store_is_main"])

    def test_my_cart_marks_inactive_product_unavailable(self):
        self.partner_product.is_active = False
        self.partner_product.save(update_fields=["is_active"])
        CartItem.objects.create(cart=self.cart, product=self.partner_product, quantity=1)

        response = self.client.get(reverse("cart-my-cart"))

        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()["store_groups"][0]["items"][0]
        self.assertFalse(item["is_available"])
        self.assertTrue(item["unavailable_reason"])
