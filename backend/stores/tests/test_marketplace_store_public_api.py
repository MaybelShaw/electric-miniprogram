from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, HomeBanner, MediaImage, Product, SpecialZone, SpecialZoneProduct
from stores.models import PartnerEntryConfig, Store, StoreMember
from users.models import User


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

    def test_main_store_and_partner_store_semantics(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        partner = Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
        )

        self.assertTrue(platform.is_main)
        self.assertEqual(platform.store_type, Store.TYPE_SELF_OPERATED)
        self.assertFalse(partner.is_main)
        self.assertEqual(partner.store_type, Store.TYPE_PARTNER)

    def test_only_one_main_store_but_many_partner_stores_are_allowed(self):
        Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
        )
        Store.objects.create(
            name="Haier",
            code="haier",
            store_type=Store.TYPE_PARTNER,
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

    def test_public_partner_entry_config_uses_independent_config(self):
        PartnerEntryConfig.objects.update_or_create(
            pk=1,
            defaults={
                "entry_title": "战略伙伴",
                "entry_subtitle": "供应链优选",
                "section_title": "供应链伙伴",
            },
        )

        response = self.client.get("/api/stores/public/partner-entry-config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["entry_title"], "战略伙伴")
        self.assertEqual(response.data["entry_subtitle"], "供应链优选")
        self.assertEqual(response.data["section_title"], "供应链伙伴")

    def test_platform_admin_can_update_partner_entry_config(self):
        platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        admin = User.objects.create_user(username="platform-admin", password="password", is_staff=True, role="admin")
        StoreMember.objects.create(user=admin, store=platform, role=StoreMember.ROLE_STORE_ADMIN)
        self.client.force_authenticate(admin)

        response = self.client.patch(
            "/api/stores/partner-entry-config/",
            {"entry_title": "战略伙伴", "section_title": "供应链伙伴"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["entry_title"], "战略伙伴")
        self.assertEqual(response.data["section_title"], "供应链伙伴")

    def test_partner_store_cannot_enable_haier_capability(self):
        partner = Store(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            allow_haier=True,
        )

        with self.assertRaises(ValidationError):
            partner.full_clean()

    def test_public_partners_returns_only_visible_active_partners(self):
        visible_second = Store.objects.create(
            name="Second",
            code="second",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
            home_order=20,
        )
        visible_first = Store.objects.create(
            name="First",
            code="first",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
            home_order=10,
        )
        Store.objects.create(
            name="Hidden",
            code="hidden",
            store_type=Store.TYPE_PARTNER,
            is_visible=False,
            show_on_home=True,
        )
        Store.objects.create(
            name="Not on home",
            code="not-on-home",
            store_type=Store.TYPE_PARTNER,
            show_on_home=False,
        )
        Store.objects.create(
            name="Disabled",
            code="disabled",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
            status=Store.STATUS_DISABLED,
        )
        Store.objects.create(
            name="Other platform",
            code="other-platform",
            store_type=Store.TYPE_SELF_OPERATED,
        )
        visible_other_partner = Store.objects.create(
            name="Other partner",
            code="other-partner",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
            home_order=30,
        )

        response = self.client.get("/api/stores/public/partners/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [visible_first.id, visible_second.id, visible_other_partner.id],
        )

    def test_public_store_detail_aggregates_only_selected_store_data(self):
        partner = Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
            description="Partner store",
        )
        other = Store.objects.create(
            name="Other",
            code="other",
            store_type=Store.TYPE_PARTNER,
            show_on_home=True,
        )
        product = self.create_store_product(partner, "Zhibang product")
        second_product = self.create_store_product(partner, "Zhibang newer")
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
        self.assertEqual([item["name"] for item in response.data["products"]], ["Zhibang product", "Zhibang newer"])
        self.assertEqual([item["name"] for item in response.data["new_arrivals"]], ["Zhibang newer", "Zhibang product"])
        self.assertEqual(
            [item["name"] for item in response.data["brands"]],
            ["Zhibang product brand", "Zhibang newer brand"],
        )
        self.assertEqual([item["title"] for item in response.data["special_zones"]], ["Zhibang zone"])
        self.assertEqual([item["title"] for item in response.data["banners"]], ["Partner banner"])
        self.assertEqual(
            [item["name"] for item in response.data["categories"]],
            ["Zhibang product major", "Zhibang newer major"],
        )

        category_response = self.client.get(f"/api/stores/public/{partner.id}/detail/?category_id={product.category.parent_id}")

        self.assertEqual(category_response.status_code, 200)
        self.assertEqual([item["name"] for item in category_response.data["products"]], ["Zhibang product"])
        self.assertEqual([item["name"] for item in category_response.data["brands"]], ["Zhibang product brand"])

    def test_public_store_detail_allows_partner_when_not_shown_on_home(self):
        partner = Store.objects.create(
            name="Not home partner",
            code="not-home-partner-detail",
            store_type=Store.TYPE_PARTNER,
            show_on_home=False,
        )
        self.create_store_product(partner, "Hidden product")

        response = self.client.get(f"/api/stores/public/{partner.id}/detail/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["store"]["id"], partner.id)

    def test_public_store_detail_hides_partner_when_not_visible(self):
        partner = Store.objects.create(
            name="Hidden partner",
            code="hidden-partner-detail",
            store_type=Store.TYPE_PARTNER,
            is_visible=False,
            show_on_home=True,
        )
        self.create_store_product(partner, "Hidden product")

        response = self.client.get(f"/api/stores/public/{partner.id}/detail/")

        self.assertEqual(response.status_code, 404)
