from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Brand, Category, HomeBanner, MediaImage, Product, SpecialZone
from orders.models import Order
from stores.models import Store, StoreMember
from stores.permissions import get_accessible_stores, is_platform_admin
from users.models import User


class StoreMarketplacePermissionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.partner = Store.objects.create(
            name="Zhibang",
            code="zhibang",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.other_partner = Store.objects.create(
            name="Other",
            code="other",
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )

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

    def test_staff_partner_admin_is_not_platform_admin(self):
        user = self.create_user("partner-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

        self.assertFalse(is_platform_admin(user))
        self.assertEqual(list(get_accessible_stores(user)), [self.partner])

    def test_platform_store_admin_does_not_implicitly_manage_partner_stores(self):
        user = self.create_user("self-operated-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.platform, role=StoreMember.ROLE_STORE_ADMIN)

        self.client.force_authenticate(user)
        response = self.client.get("/api/catalog/products/", {"store": self.partner.id})

        self.assertEqual(response.status_code, 403)

    def test_partner_admin_cannot_read_other_store_operations_data(self):
        user = self.create_user("partner-admin", is_staff=True, role="admin")
        customer = self.create_user("customer")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        own_product = self.create_store_product(self.partner, "Own product")
        other_product = self.create_store_product(self.other_partner, "Other product")
        Order.objects.create(
            user=customer,
            product=own_product,
            store=self.partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
        )
        Order.objects.create(
            user=customer,
            product=other_product,
            store=self.other_partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
        )
        media = MediaImage.objects.create(file="images/banner.png", original_name="banner.png")
        HomeBanner.objects.create(store=self.partner, image=media, title="Own banner")
        HomeBanner.objects.create(store=self.other_partner, image=media, title="Other banner")
        SpecialZone.objects.create(store=self.partner, title="Own zone", slug="own-zone")
        SpecialZone.objects.create(store=self.other_partner, title="Other zone", slug="other-zone")

        self.client.force_authenticate(user)

        own_products = self.client.get("/api/catalog/products/")
        cross_products = self.client.get("/api/catalog/products/", {"store": self.other_partner.id})
        orders = self.client.get("/api/orders/")
        cross_orders = self.client.get("/api/orders/", {"store": self.other_partner.id})
        own_banners = self.client.get("/api/catalog/home-banners/")
        cross_banners = self.client.get("/api/catalog/home-banners/", {"store": self.other_partner.id})
        own_zones = self.client.get("/api/catalog/special-zones/")
        cross_zones = self.client.get("/api/catalog/special-zones/", {"store": self.other_partner.id})

        self.assertEqual([item["name"] for item in own_products.data["results"]], ["Own product"])
        self.assertEqual(cross_products.status_code, 403)
        self.assertEqual([item["product"]["name"] for item in orders.data["results"]], ["Own product"])
        self.assertEqual(cross_orders.status_code, 403)
        self.assertEqual([item["title"] for item in own_banners.data["results"]], ["Own banner"])
        self.assertEqual(cross_banners.status_code, 403)
        self.assertEqual([item["title"] for item in own_zones.data["results"]], ["Own zone"])
        self.assertEqual(cross_zones.status_code, 403)

    def test_partner_admin_cannot_access_platform_management_endpoints(self):
        user = self.create_user("partner-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        self.client.force_authenticate(user)

        urls = [
            "/api/users/",
            "/api/company-info/",
            "/api/credit-accounts/",
            "/api/stores/members/",
            "/api/stores/payment-configs/",
            "/api/stores/settlement-rules/",
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
