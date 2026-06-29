from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from stores.models import Store, StoreMember
from users.models import User


class ProductPublicStoreScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.major = Category.objects.create(
            name="Test category",
            level=Category.LEVEL_MAJOR,
            store=self.store,
        )
        self.category = Category.objects.create(
            name="Test item",
            level=Category.LEVEL_MINOR,
            parent=self.major,
            store=self.store,
        )
        self.brand = Brand.objects.create(name="Test brand", store=self.store)
        self.product = Product.objects.create(
            name="Test product",
            category=self.category,
            brand=self.brand,
            store=self.store,
            price=Decimal("9999.00"),
            supply_price=Decimal("6000.00"),
            invoice_price=Decimal("6500.00"),
            stock_rebate=Decimal("100.00"),
            rebate_money=Decimal("50.00"),
            product_code="HAIER-TEST-001",
            source=Product.SOURCE_HAIER,
            warehouse_code="WH001",
            warehouse_grade="0",
            stock=112,
            is_active=True,
        )
        self.inactive_product = Product.objects.create(
            name="Inactive product",
            category=self.category,
            brand=self.brand,
            store=self.store,
            price=Decimal("8888.00"),
            stock=5,
            is_active=False,
        )
        self.partner_store = Store.objects.create(
            name="Partner store",
            code="partner-store",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
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
        self.hidden_partner_store = Store.objects.create(
            name="Hidden partner store",
            code="hidden-partner-store",
            store_type=Store.TYPE_PARTNER,
            is_visible=False,
            show_on_home=True,
        )
        self.not_home_partner_store = Store.objects.create(
            name="Not home partner store",
            code="not-home-partner-store",
            store_type=Store.TYPE_PARTNER,
            show_on_home=False,
        )
        hidden_partner_major = Category.objects.create(
            name="Hidden partner category",
            level=Category.LEVEL_MAJOR,
            store=self.hidden_partner_store,
        )
        hidden_partner_category = Category.objects.create(
            name="Hidden partner item",
            level=Category.LEVEL_MINOR,
            parent=hidden_partner_major,
            store=self.hidden_partner_store,
        )
        hidden_partner_brand = Brand.objects.create(name="Hidden partner brand", store=self.hidden_partner_store)
        self.hidden_partner_product = Product.objects.create(
            name="Hidden partner product",
            category=hidden_partner_category,
            brand=hidden_partner_brand,
            store=self.hidden_partner_store,
            price=Decimal("2999.00"),
            stock=8,
            is_active=True,
        )
        not_home_partner_major = Category.objects.create(
            name="Not home partner category",
            level=Category.LEVEL_MAJOR,
            store=self.not_home_partner_store,
        )
        not_home_partner_category = Category.objects.create(
            name="Not home partner item",
            level=Category.LEVEL_MINOR,
            parent=not_home_partner_major,
            store=self.not_home_partner_store,
        )
        not_home_partner_brand = Brand.objects.create(name="Not home partner brand", store=self.not_home_partner_store)
        self.not_home_partner_product = Product.objects.create(
            name="Not home partner product",
            category=not_home_partner_category,
            brand=not_home_partner_brand,
            store=self.not_home_partner_store,
            price=Decimal("3999.00"),
            stock=8,
            is_active=True,
        )
        other_major = Category.objects.create(
            name="Other category",
            level=Category.LEVEL_MAJOR,
            store=self.store,
        )
        other_category = Category.objects.create(
            name="Other item",
            level=Category.LEVEL_MINOR,
            parent=other_major,
            store=self.store,
        )
        self.same_brand_other_category_product = Product.objects.create(
            name="Same brand other category",
            category=other_category,
            brand=self.brand,
            store=self.store,
            price=Decimal("2999.00"),
            stock=3,
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
            [
                self.product.id,
                self.partner_product.id,
                self.not_home_partner_product.id,
                self.same_brand_other_category_product.id,
            ],
        )

    def test_by_brand_can_be_limited_to_category_tree(self):
        response = self.client.get(
            "/api/catalog/products/by_brand/",
            {
                "brand": self.brand.name,
                "store": self.store.id,
                "category_id": self.major.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.product.id])

    def test_logged_in_customer_without_store_membership_can_open_any_public_product_detail(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(f"/api/catalog/products/{self.partner_product.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.partner_product.id)

    def test_hidden_partner_store_products_are_not_public(self):
        list_response = self.client.get("/api/catalog/products/?page=1&page_size=20")
        detail_response = self.client.get(f"/api/catalog/products/{self.hidden_partner_product.id}/")
        category_response = self.client.get(
            "/api/catalog/products/by_category/",
            {"category": self.hidden_partner_product.category.name, "store": self.hidden_partner_store.id},
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertNotIn(
            self.hidden_partner_product.id,
            [item["id"] for item in list_response.data["results"]],
        )
        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(category_response.status_code, 200)
        self.assertEqual(category_response.data["results"], [])

    def test_partner_store_products_remain_public_when_only_hidden_from_home(self):
        list_response = self.client.get("/api/catalog/products/?page=1&page_size=20")
        detail_response = self.client.get(f"/api/catalog/products/{self.not_home_partner_product.id}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertIn(
            self.not_home_partner_product.id,
            [item["id"] for item in list_response.data["results"]],
        )
        self.assertEqual(detail_response.status_code, 200)

    def test_public_product_detail_hides_internal_procurement_fields(self):
        response = self.client.get(f"/api/catalog/products/{self.product.id}/")

        self.assertEqual(response.status_code, 200)
        for field in [
            "product_code",
            "supply_price",
            "invoice_price",
            "stock_rebate",
            "rebate_money",
            "warehouse_code",
            "warehouse_grade",
        ]:
            self.assertNotIn(field, response.data)
        self.assertIsNone(response.data["haier_info"])

    def test_customer_cannot_open_inactive_product_detail(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(f"/api/catalog/products/{self.inactive_product.id}/")

        self.assertEqual(response.status_code, 404)

    def test_store_member_can_open_inactive_own_store_product_detail(self):
        admin = User.objects.create_user(username="store-admin")
        StoreMember.objects.create(user=admin, store=self.store, role=StoreMember.ROLE_STORE_ADMIN)
        self.client.force_authenticate(admin)

        inactive_response = self.client.get(f"/api/catalog/products/{self.inactive_product.id}/")
        active_response = self.client.get(f"/api/catalog/products/{self.product.id}/")

        self.assertEqual(inactive_response.status_code, 200)
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.data["product_code"], "HAIER-TEST-001")
        self.assertEqual(active_response.data["haier_info"]["product_code"], "HAIER-TEST-001")
