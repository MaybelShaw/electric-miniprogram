from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, HomeStoreCard, Product, SpecialZone, SpecialZoneProduct
from stores.models import Store, StoreMember


class ActivityHomeStoreCardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.main_store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.partner = Store.objects.create(
            name="Partner",
            code="partner",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.main_store,
            show_on_home=True,
        )
        self.other_store = Store.objects.create(name="Other", code="other")
        self.platform_admin = get_user_model().objects.create_superuser("admin", password="password")
        self.partner_admin = get_user_model().objects.create_user("partner-admin", password="password")
        StoreMember.objects.create(user=self.partner_admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

    def create_category(self, store, name):
        major = Category.objects.create(name=name, level=Category.LEVEL_MAJOR, store=store)
        minor = Category.objects.create(name=f"{name}-minor", level=Category.LEVEL_MINOR, parent=major, store=store)
        return major, minor

    def create_product(self, store, name, *, is_active=True):
        major, minor = self.create_category(store, name)
        brand = Brand.objects.create(name=f"{name}-brand", store=store)
        product = Product.objects.create(
            store=store,
            name=name,
            category=minor,
            brand=brand,
            price=Decimal("100.00"),
            stock=10,
            is_active=is_active,
        )
        return product, major

    def test_platform_activity_allows_cross_store_product_binding(self):
        zone = SpecialZone.objects.create(
            store=self.main_store,
            title="Platform",
            slug="platform",
            kind=SpecialZone.KIND_PLATFORM_ACTIVITY,
        )
        product, _ = self.create_product(self.partner, "Partner Product")
        self.client.force_authenticate(self.platform_admin)

        response = self.client.post(
            f"/api/catalog/special-zones/{zone.id}/products/",
            {"product_id": product.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(SpecialZoneProduct.objects.filter(zone=zone, product=product).exists())

    def test_partner_cannot_create_activity(self):
        self.client.force_authenticate(self.partner_admin)

        response = self.client.post(
            "/api/catalog/special-zones/",
            {
                "store_id": self.partner.id,
                "title": "Partner Activity",
                "slug": "partner-activity",
                "kind": SpecialZone.KIND_STORE_ACTIVITY,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403, response.content)

    def test_product_activities_are_limited_for_partner_admin(self):
        platform_zone = SpecialZone.objects.create(
            store=self.main_store,
            title="Platform",
            slug="platform",
            kind=SpecialZone.KIND_PLATFORM_ACTIVITY,
            is_active=True,
        )
        store_zone = SpecialZone.objects.create(
            store=self.partner,
            title="Store",
            slug="store",
            kind=SpecialZone.KIND_STORE_ACTIVITY,
            is_active=True,
        )
        other_zone = SpecialZone.objects.create(
            store=self.other_store,
            title="Other",
            slug="other",
            kind=SpecialZone.KIND_STORE_ACTIVITY,
            is_active=True,
        )
        product, _ = self.create_product(self.partner, "Partner Product")
        self.client.force_authenticate(self.partner_admin)

        response = self.client.get(f"/api/catalog/products/{product.id}/activities/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            {item["id"] for item in response.json()["available"]},
            {platform_zone.id, store_zone.id},
        )
        self.assertNotIn(other_zone.id, {item["id"] for item in response.json()["available"]})

    def test_home_store_card_requires_one_main_four_secondary_and_three_categories(self):
        products = []
        category_ids = []
        for index in range(5):
            product, major = self.create_product(self.partner, f"Product {index}")
            products.append(product)
            category_ids.append(major.id)
        self.client.force_authenticate(self.platform_admin)

        response = self.client.post(
            "/api/catalog/home-store-cards/",
            {
                "store_id": self.partner.id,
                "title": "宋式美学",
                "subtitle": "合作店铺精选",
                "main_product_id": products[0].id,
                "secondary_product_ids": [product.id for product in products[1:]],
                "category_ids": category_ids[:3],
                "order": 1,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(HomeStoreCard.objects.count(), 1)
        self.assertFalse(response.json()["has_inactive_products"])

    def test_public_home_store_cards_only_return_active_cards_with_inactive_product_flag(self):
        products = []
        category_ids = []
        for index in range(5):
            product, major = self.create_product(self.partner, f"Product {index}", is_active=index != 4)
            products.append(product)
            category_ids.append(major.id)
        card = HomeStoreCard.objects.create(store=self.partner, title="Active", order=1, is_active=True)
        for index, product in enumerate(products):
            role = "main" if index == 0 else "secondary"
            card.card_products.create(product=product, role=role, order=index)
        for index, category_id in enumerate(category_ids[:3]):
            card.card_categories.create(category_id=category_id, order=index)
        HomeStoreCard.objects.create(store=self.partner, title="Hidden", order=0, is_active=False)

        response = self.client.get("/api/catalog/home-store-cards/")

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        results = data["results"] if isinstance(data, dict) and "results" in data else data
        self.assertEqual([item["id"] for item in results], [card.id])
        self.assertTrue(results[0]["has_inactive_products"])
