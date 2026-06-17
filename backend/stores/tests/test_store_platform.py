from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from orders.models import Order
from stores.models import Store, StoreMember
from stores.permissions import get_accessible_stores, is_platform_admin
from users.models import User


class StorePlatformFoundationTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_user(self, username, **kwargs):
        return User.objects.create_user(username=username, password="password", **kwargs)

    def create_store_product(self, store, name):
        major = Category.objects.create(name=f"{name} major", level=Category.LEVEL_MAJOR, store=store)
        category = Category.objects.create(
            name=f"{name} minor",
            level=Category.LEVEL_MINOR,
            parent=major,
            store=store,
        )
        brand = Brand.objects.create(name=f"{name} brand", store=store)
        return Product.objects.create(
            name=name,
            category=category,
            brand=brand,
            store=store,
            price=Decimal("100.00"),
            stock=10,
        )

    def test_default_main_store_exists_and_allows_haier(self):
        main_store = Store.objects.get(code="main_store")

        self.assertEqual(main_store.name, "main_store")
        self.assertTrue(main_store.is_main)
        self.assertTrue(main_store.allow_haier)
        self.assertEqual(Store.objects.filter(is_main=True).count(), 1)

    def test_only_main_store_can_enable_haier_capability(self):
        store = Store(name="Branch", code="branch", allow_haier=True)

        with self.assertRaises(ValidationError):
            store.full_clean()

    def test_platform_admin_can_create_store_and_current_context_lists_all(self):
        admin = self.create_user("platform-admin", role="admin", is_staff=True, is_superuser=True)
        self.client.force_authenticate(admin)

        create_response = self.client.post(
            "/api/stores/",
            {"name": "Zhibang", "code": "zhibang", "status": Store.STATUS_ACTIVE},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        context_response = self.client.get("/api/stores/current/")
        self.assertEqual(context_response.status_code, 200)
        self.assertTrue(context_response.data["is_platform_admin"])
        self.assertEqual(context_response.data["default_store"]["code"], "main_store")
        self.assertEqual(
            {store["code"] for store in context_response.data["stores"]},
            {"main_store", "zhibang"},
        )

    def test_store_member_context_is_limited_to_own_store(self):
        zhibang = Store.objects.create(name="Zhibang", code="zhibang")
        other = Store.objects.create(name="Other", code="other")
        user = self.create_user("zhibang-admin")
        StoreMember.objects.create(user=user, store=zhibang, role=StoreMember.ROLE_STORE_ADMIN)
        self.client.force_authenticate(user)

        self.assertFalse(is_platform_admin(user))
        self.assertEqual(list(get_accessible_stores(user)), [zhibang])

        response = self.client.get("/api/stores/current/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["default_store"]["code"], "zhibang")
        self.assertEqual([store["code"] for store in response.data["stores"]], ["zhibang"])
        self.assertNotIn(other.code, [store["code"] for store in response.data["stores"]])

    def test_store_member_can_password_login_for_merchant_backend(self):
        zhibang = Store.objects.create(name="Zhibang", code="zhibang")
        self.create_user("existing-admin", role="admin", is_staff=True, is_superuser=True)
        user = self.create_user("zhibang-login")
        StoreMember.objects.create(user=user, store=zhibang, role=StoreMember.ROLE_STORE_ADMIN)

        response = self.client.post(
            "/api/admin/login/",
            {"username": "zhibang-login", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["store_roles"][0]["role"], StoreMember.ROLE_STORE_ADMIN)

    def test_store_member_lists_only_own_store_products_and_orders(self):
        zhibang = Store.objects.create(name="Zhibang", code="zhibang")
        other = Store.objects.create(name="Other", code="other")
        store_user = self.create_user("zhibang-staff")
        customer = self.create_user("customer")
        StoreMember.objects.create(user=store_user, store=zhibang, role=StoreMember.ROLE_STORE_STAFF)

        zhibang_product = self.create_store_product(zhibang, "Zhibang product")
        other_product = self.create_store_product(other, "Other product")
        Order.objects.create(
            user=customer,
            product=zhibang_product,
            store=zhibang,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
        )
        Order.objects.create(
            user=customer,
            product=other_product,
            store=other,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
        )

        self.client.force_authenticate(store_user)

        product_response = self.client.get("/api/catalog/products/")
        self.assertEqual(product_response.status_code, 200)
        product_names = [item["name"] for item in product_response.data["results"]]
        self.assertEqual(product_names, ["Zhibang product"])

        order_response = self.client.get("/api/orders/")
        self.assertEqual(order_response.status_code, 200)
        order_products = [item["product"]["name"] for item in order_response.data["results"]]
        self.assertEqual(order_products, ["Zhibang product"])
