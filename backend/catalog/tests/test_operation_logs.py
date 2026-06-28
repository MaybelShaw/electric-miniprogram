from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, InventoryLog, Product, SearchLog
from stores.models import Store, StoreMember


class CatalogOperationLogAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.partner = Store.objects.create(
            name="志邦运营店",
            code="zhibang-logs",
            store_type=Store.TYPE_PARTNER,
        )
        self.other_store = Store.objects.create(
            name="其他运营店",
            code="other-logs",
            store_type=Store.TYPE_PARTNER,
        )
        self.platform_admin = get_user_model().objects.create_superuser(
            username="logs-platform-admin",
            password="password",
        )
        self.partner_admin = self.create_store_user("logs-partner-admin", self.partner)
        self.customer = get_user_model().objects.create_user(username="logs-customer", password="password")
        self.product = self.create_product(self.partner, "志邦洗衣机")
        self.other_product = self.create_product(self.other_store, "其他洗衣机")

    def create_store_user(self, username, store):
        user = get_user_model().objects.create_user(username=username, password="password")
        StoreMember.objects.create(user=user, store=store, role=StoreMember.ROLE_STORE_ADMIN)
        return user

    def create_product(self, store, name):
        major = Category.objects.create(name=f"{name}大类", level=Category.LEVEL_MAJOR, store=store)
        category = Category.objects.create(
            name=f"{name}小类",
            level=Category.LEVEL_MINOR,
            parent=major,
            store=store,
        )
        brand = Brand.objects.create(name=f"{name}品牌", store=store)
        return Product.objects.create(
            name=name,
            category=category,
            brand=brand,
            store=store,
            price=Decimal("1999.00"),
            stock=10,
        )

    def test_search_log_list_is_not_public_but_hot_keywords_remains_public(self):
        SearchLog.objects.create(keyword="冰箱", user=self.customer)

        self.client.force_authenticate(self.customer)
        list_response = self.client.get("/api/catalog/search-logs/")
        self.client.force_authenticate(user=None)
        hot_response = self.client.get("/api/catalog/search-logs/hot_keywords/")

        self.assertEqual(list_response.status_code, 403, list_response.content)
        self.assertEqual(hot_response.status_code, 200, hot_response.content)

    def test_store_admin_cannot_read_search_logs(self):
        SearchLog.objects.create(keyword="冰箱", user=self.customer)
        self.client.force_authenticate(self.partner_admin)

        response = self.client.get("/api/catalog/search-logs/")

        self.assertEqual(response.status_code, 403, response.content)

    def test_store_admin_can_only_read_own_inventory_logs(self):
        own_log = InventoryLog.objects.create(
            product=self.product,
            change_type="adjust",
            quantity=5,
            reason="盘点调整",
            created_by=self.partner_admin,
        )
        InventoryLog.objects.create(
            product=self.other_product,
            change_type="adjust",
            quantity=3,
            reason="其他店铺盘点",
        )
        self.client.force_authenticate(self.partner_admin)

        own_response = self.client.get("/api/catalog/inventory-logs/")
        cross_response = self.client.get("/api/catalog/inventory-logs/", {"store": self.other_store.id})

        self.assertEqual(own_response.status_code, 200, own_response.content)
        self.assertEqual([item["id"] for item in own_response.data["results"]], [own_log.id])
        self.assertEqual(cross_response.status_code, 403, cross_response.content)

    def test_platform_admin_can_read_all_inventory_logs(self):
        first = InventoryLog.objects.create(
            product=self.product,
            change_type="adjust",
            quantity=5,
            reason="平台盘点",
        )
        second = InventoryLog.objects.create(
            product=self.other_product,
            change_type="release",
            quantity=2,
            reason="释放库存",
        )
        self.client.force_authenticate(self.platform_admin)

        response = self.client.get("/api/catalog/inventory-logs/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual({item["id"] for item in response.data["results"]}, {first.id, second.id})
