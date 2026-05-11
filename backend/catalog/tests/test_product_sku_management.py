from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product, ProductSKU
from stores.models import Store, StoreMember


class ProductSKUManagementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.partner = Store.objects.create(
            name="志邦门店",
            code="zhibang-sku",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.other_store = Store.objects.create(
            name="其他门店",
            code="other-sku",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.platform_admin = get_user_model().objects.create_superuser(
            username="sku-platform-admin",
            password="password",
        )
        self.partner_admin = self.create_store_user("sku-partner-admin", self.partner)
        self.other_admin = self.create_store_user("sku-other-admin", self.other_store)
        self.product = self.create_product(self.partner, "志邦冰箱")
        self.other_product = self.create_product(self.other_store, "其他冰箱")

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
            price=Decimal("2999.00"),
            stock=10,
        )

    def test_store_admin_can_create_update_and_list_own_product_skus(self):
        self.client.force_authenticate(self.partner_admin)

        create_response = self.client.post(
            "/api/catalog/product-skus/",
            {
                "product_id": self.product.id,
                "name": "标准款",
                "sku_code": "ZB-FRIDGE-STD",
                "specs": {"容量": "520L", "颜色": "银色"},
                "price": "2999.00",
                "stock": 8,
                "image": "https://example.com/sku.jpg",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201, create_response.content)
        sku_id = create_response.data["id"]
        self.assertEqual(create_response.data["product"], self.product.id)
        self.assertEqual(create_response.data["specs"], {"容量": "520L", "颜色": "银色"})

        list_response = self.client.get("/api/catalog/product-skus/", {"product": self.product.id})
        self.assertEqual(list_response.status_code, 200, list_response.content)
        self.assertEqual([item["id"] for item in list_response.data["results"]], [sku_id])

        update_response = self.client.patch(
            f"/api/catalog/product-skus/{sku_id}/",
            {"stock": 6, "price": "2799.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.content)
        self.assertEqual(update_response.data["stock"], 6)
        self.assertEqual(update_response.data["price"], "2799.00")

    def test_store_admin_cannot_manage_cross_store_skus(self):
        sku = ProductSKU.objects.create(
            product=self.product,
            name="标准款",
            sku_code="ZB-FORBIDDEN",
            specs={"容量": "520L"},
            price=Decimal("2999.00"),
            stock=8,
        )
        self.client.force_authenticate(self.other_admin)

        create_response = self.client.post(
            "/api/catalog/product-skus/",
            {
                "product_id": self.product.id,
                "name": "越权款",
                "sku_code": "CROSS-STORE",
                "specs": {"颜色": "白色"},
                "price": "1999.00",
                "stock": 1,
            },
            format="json",
        )
        update_response = self.client.patch(
            f"/api/catalog/product-skus/{sku.id}/",
            {"stock": 1},
            format="json",
        )

        self.assertEqual(create_response.status_code, 403, create_response.content)
        self.assertEqual(update_response.status_code, 404, update_response.content)

    def test_public_product_detail_only_returns_active_skus(self):
        active = ProductSKU.objects.create(
            product=self.product,
            name="标准款",
            sku_code="ZB-ACTIVE",
            specs={"容量": "520L"},
            price=Decimal("2999.00"),
            stock=8,
            is_active=True,
        )
        ProductSKU.objects.create(
            product=self.product,
            name="停用款",
            sku_code="ZB-INACTIVE",
            specs={"容量": "450L"},
            price=Decimal("2499.00"),
            stock=3,
            is_active=False,
        )

        response = self.client.get(f"/api/catalog/products/{self.product.id}/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in response.data["skus"]], [active.id])
