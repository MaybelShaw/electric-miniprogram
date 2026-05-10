from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from stores.models import Store
from users.models import User


class ProductPublicStoreScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        major = Category.objects.create(
            name="Test category",
            level=Category.LEVEL_MAJOR,
            store=self.store,
        )
        self.category = Category.objects.create(
            name="Test item",
            level=Category.LEVEL_MINOR,
            parent=major,
            store=self.store,
        )
        self.brand = Brand.objects.create(name="Test brand", store=self.store)
        self.product = Product.objects.create(
            name="Test product",
            category=self.category,
            brand=self.brand,
            store=self.store,
            price=Decimal("9999.00"),
            stock=112,
            is_active=True,
        )
        self.partner_store = Store.objects.create(
            name="Partner store",
            code="partner-store",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.store,
        )
        partner_major = Category.objects.create(
            name="Partner category",
            level=Category.LEVEL_MAJOR,
            store=self.partner_store,
        )
        partner_category = Category.objects.create(
            name="Partner item",
            level=Category.LEVEL_MINOR,
            parent=partner_major,
            store=self.partner_store,
        )
        partner_brand = Brand.objects.create(name="Partner brand", store=self.partner_store)
        self.partner_product = Product.objects.create(
            name="Partner product",
            category=partner_category,
            brand=partner_brand,
            store=self.partner_store,
            price=Decimal("1999.00"),
            stock=8,
            is_active=True,
        )
        self.customer = User.objects.create_user(
            openid="customer-openid",
            username="customer",
        )

    def test_logged_in_customer_without_store_membership_sees_all_public_products(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/catalog/products/?page=1&page_size=20")

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [self.product.id, self.partner_product.id],
        )

    def test_logged_in_customer_without_store_membership_can_open_any_public_product_detail(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(f"/api/catalog/products/{self.partner_product.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.partner_product.id)
