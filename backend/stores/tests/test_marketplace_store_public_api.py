from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, HomeBanner, MediaImage, Product, SpecialZone, SpecialZoneProduct
from stores.models import Store


class MarketplaceStorePublicAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

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

    def test_platform_store_and_partner_store_membership_semantics(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        partner = Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
        )

        self.assertTrue(platform.is_main)
        self.assertEqual(platform.store_type, Store.TYPE_SELF_OPERATED)
        self.assertIsNone(platform.platform_store)
        self.assertEqual(partner.platform_store, platform)

    def test_only_one_main_store_but_many_partner_stores_are_allowed(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
        )
        Store.objects.create(
            name="Haier",
            code="haier",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
        )

        duplicate_main = Store(
            name="Another main",
            code="another-main",
            is_main=True,
            store_type=Store.TYPE_SELF_OPERATED,
        )
        with self.assertRaises(Exception):
            duplicate_main.save()

        self.assertEqual(Store.objects.filter(is_main=True).count(), 1)
        self.assertEqual(Store.objects.filter(store_type=Store.TYPE_PARTNER).count(), 2)

    def test_partner_store_cannot_enable_haier_capability(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        partner = Store(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            allow_haier=True,
        )

        with self.assertRaises(ValidationError):
            partner.full_clean()

    def test_public_partners_returns_only_visible_active_partners_for_platform(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        visible_second = Store.objects.create(
            name="Second",
            code="second",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            show_on_home=True,
            home_order=20,
        )
        visible_first = Store.objects.create(
            name="First",
            code="first",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            show_on_home=True,
            home_order=10,
        )
        Store.objects.create(
            name="Hidden",
            code="hidden",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            show_on_home=False,
        )
        Store.objects.create(
            name="Disabled",
            code="disabled",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            show_on_home=True,
            status=Store.STATUS_DISABLED,
        )
        other_platform = Store.objects.create(
            name="Other platform",
            code="other-platform",
            store_type=Store.TYPE_SELF_OPERATED,
        )
        Store.objects.create(
            name="Other partner",
            code="other-partner",
            store_type=Store.TYPE_PARTNER,
            platform_store=other_platform,
            show_on_home=True,
        )

        response = self.client.get(f"/api/stores/public/partners/?platform={platform.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [visible_first.id, visible_second.id])

    def test_public_store_detail_aggregates_only_selected_store_data(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        partner = Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            show_on_home=True,
            description="Partner store",
        )
        other = Store.objects.create(
            name="Other",
            code="other",
            store_type=Store.TYPE_PARTNER,
            platform_store=platform,
            show_on_home=True,
        )
        product = self.create_store_product(partner, "Zhibang product")
        other_product = self.create_store_product(other, "Other product")
        zone = SpecialZone.objects.create(
            store=partner,
            title="Zhibang zone",
            slug="zhibang-zone",
            kind=SpecialZone.KIND_STORE_ACTIVITY,
            show_on_home=True,
            is_active=True,
        )
        SpecialZoneProduct.objects.create(zone=zone, product=product)
        other_zone = SpecialZone.objects.create(
            store=other,
            title="Other zone",
            slug="other-zone",
            kind=SpecialZone.KIND_STORE_ACTIVITY,
            show_on_home=True,
            is_active=True,
        )
        SpecialZoneProduct.objects.create(zone=other_zone, product=other_product)
        media = MediaImage.objects.create(file="images/banner.png", original_name="banner.png")
        HomeBanner.objects.create(store=partner, image=media, title="Partner banner", is_active=True)
        HomeBanner.objects.create(store=other, image=media, title="Other banner", is_active=True)

        response = self.client.get(f"/api/stores/public/{partner.id}/detail/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["store"]["id"], partner.id)
        self.assertEqual([item["name"] for item in response.data["products"]], ["Zhibang product"])
        self.assertEqual([item["title"] for item in response.data["special_zones"]], ["Zhibang zone"])
        self.assertEqual([item["title"] for item in response.data["banners"]], ["Partner banner"])
        self.assertEqual([item["name"] for item in response.data["categories"]], ["Zhibang product major"])
