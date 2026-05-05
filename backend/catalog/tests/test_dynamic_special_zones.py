from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Brand, Category, HomeBanner, MediaImage, Product, SpecialZone, SpecialZoneProduct
from stores.models import Store, StoreMember


class DynamicSpecialZoneTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.main_store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.zhibang = Store.objects.create(name="志邦家具", code="zhibang")
        self.other_store = Store.objects.create(name="其他店铺", code="other")
        self.platform_admin = get_user_model().objects.create_superuser(
            username="platform-admin",
            password="password",
        )
        self.zhibang_admin = self.create_store_user("zhibang-admin", self.zhibang)
        self.other_admin = self.create_store_user("other-admin", self.other_store)

    def create_store_user(self, username, store):
        user = get_user_model().objects.create_user(username=username, password="password")
        StoreMember.objects.create(user=user, store=store, role=StoreMember.ROLE_STORE_ADMIN)
        return user

    def create_product(self, store, name, **overrides):
        major = Category.objects.create(name=f"{name}品类", level=Category.LEVEL_MAJOR, store=store)
        category = Category.objects.create(
            name=f"{name}子类",
            level=Category.LEVEL_MINOR,
            parent=major,
            store=store,
        )
        brand = Brand.objects.create(name=f"{name}品牌", store=store)
        data = {
            "store": store,
            "name": name,
            "category": category,
            "brand": brand,
            "price": Decimal("100.00"),
            "stock": 10,
            "is_active": True,
        }
        data.update(overrides)
        return Product.objects.create(**data)

    def create_zone(self, store, title, **overrides):
        data = {
            "store": store,
            "title": title,
            "slug": title.lower().replace(" ", "-"),
            "kind": SpecialZone.KIND_ACTIVITY,
            "subtitle": "",
            "cover_image": "",
            "is_active": True,
            "show_on_home": True,
            "home_order": 0,
        }
        data.update(overrides)
        return SpecialZone.objects.create(**data)

    def create_media(self, filename):
        return MediaImage.objects.create(
            file=f"images/{filename}",
            original_name=filename,
            content_type="image/jpeg",
            size=128,
        )

    def results(self, response):
        data = response.json()
        if isinstance(data, list):
            return data
        return data.get("results", data)

    def test_public_special_zone_list_filters_by_requested_store(self):
        zhibang_zone = self.create_zone(self.zhibang, "618大促", slug="618-sale")
        self.create_zone(self.main_store, "主店活动", slug="main-sale")

        response = self.client.get("/api/catalog/special-zones/", {"store": self.zhibang.id})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in self.results(response)], [zhibang_zone.id])

    def test_public_special_zone_list_only_returns_visible_home_zones(self):
        now = timezone.now()
        visible = self.create_zone(self.zhibang, "可见专区", slug="visible", home_order=2)
        earlier = self.create_zone(self.zhibang, "更靠前专区", slug="earlier", home_order=1)
        self.create_zone(self.zhibang, "未启用专区", slug="inactive", is_active=False)
        self.create_zone(self.zhibang, "不展示首页", slug="hidden-home", show_on_home=False)
        self.create_zone(self.zhibang, "未开始专区", slug="future", start_at=now + timedelta(days=1))
        self.create_zone(self.zhibang, "已结束专区", slug="expired", end_at=now - timedelta(days=1))
        self.create_zone(self.other_store, "其他店铺专区", slug="other")

        response = self.client.get("/api/catalog/special-zones/", {"store": self.zhibang.id})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in self.results(response)], [earlier.id, visible.id])

    def test_store_permissions_control_special_zone_management(self):
        self.client.force_authenticate(self.platform_admin)
        create_response = self.client.post(
            "/api/catalog/special-zones/",
            {
                "store_id": self.zhibang.id,
                "title": "夏季大促",
                "slug": "summer-sale",
                "kind": SpecialZone.KIND_PROMOTION,
                "show_on_home": True,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.content)
        zone_id = create_response.json()["id"]

        self.client.force_authenticate(self.zhibang_admin)
        own_response = self.client.patch(
            f"/api/catalog/special-zones/{zone_id}/",
            {"title": "夏季大促更新"},
            format="json",
        )
        self.assertEqual(own_response.status_code, 200, own_response.content)
        self.assertEqual(own_response.json()["title"], "夏季大促更新")

        self.client.force_authenticate(self.other_admin)
        forbidden_response = self.client.patch(
            f"/api/catalog/special-zones/{zone_id}/",
            {"title": "越权修改"},
            format="json",
        )
        self.assertEqual(forbidden_response.status_code, 403, forbidden_response.content)

    def test_special_zone_products_return_active_bindings_in_order(self):
        zone = self.create_zone(self.zhibang, "瓷砖专区", slug="tile-zone")
        first = self.create_product(self.zhibang, "优先商品")
        second = self.create_product(self.zhibang, "次序商品")
        hidden = self.create_product(self.zhibang, "隐藏商品")
        SpecialZoneProduct.objects.create(zone=zone, product=second, order=20)
        SpecialZoneProduct.objects.create(zone=zone, product=first, order=10)
        SpecialZoneProduct.objects.create(zone=zone, product=hidden, order=5, is_active=False)

        response = self.client.get(f"/api/catalog/special-zones/{zone.id}/products/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in self.results(response)], [first.id, second.id])

    def test_special_zone_product_binding_rejects_cross_store_product(self):
        zone = self.create_zone(self.zhibang, "床垫专区", slug="mattress-zone")
        cross_store_product = self.create_product(self.other_store, "其他店铺商品")
        self.client.force_authenticate(self.zhibang_admin)

        response = self.client.post(
            f"/api/catalog/special-zones/{zone.id}/products/",
            {"product_id": cross_store_product.id, "order": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("product_id", response.json())

    def test_home_banners_can_filter_by_dynamic_special_zone(self):
        zone = self.create_zone(self.zhibang, "新品专区", slug="new-zone")
        other_zone = self.create_zone(self.zhibang, "清仓专区", slug="clearance-zone")
        target_banner = HomeBanner.objects.create(
            store=self.zhibang,
            image=self.create_media("target.jpg"),
            title="专区轮播",
            special_zone=zone,
            order=1,
        )
        HomeBanner.objects.create(
            store=self.zhibang,
            image=self.create_media("other.jpg"),
            title="其他专区轮播",
            special_zone=other_zone,
            order=2,
        )

        response = self.client.get("/api/catalog/home-banners/", {"special_zone": zone.id})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in self.results(response)], [target_banner.id])

    def test_product_list_can_filter_by_dynamic_special_zone(self):
        zone = self.create_zone(self.zhibang, "品牌专区", slug="brand-zone")
        bound = self.create_product(self.zhibang, "专区商品")
        inactive_binding = self.create_product(self.zhibang, "绑定隐藏商品")
        unrelated = self.create_product(self.zhibang, "普通商品")
        SpecialZoneProduct.objects.create(zone=zone, product=bound, order=1)
        SpecialZoneProduct.objects.create(zone=zone, product=inactive_binding, order=2, is_active=False)

        response = self.client.get(
            "/api/catalog/products/",
            {"special_zone": zone.id, "page_size": 10},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["results"][0]["id"], bound.id)
        self.assertNotEqual(response.json()["results"][0]["id"], unrelated.id)
