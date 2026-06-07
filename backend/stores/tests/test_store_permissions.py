from decimal import Decimal
from datetime import date
import re
from pathlib import Path

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from catalog.models import Brand, Case, Category, HomeBanner, MediaImage, Product, SpecialZone
from orders.models import Invoice, Order, Payment
from stores.models import Store, StoreMember
from stores.permissions import (
    PERMISSION_ORDERS_ADJUST_AMOUNT,
    PERMISSION_ORDERS_SHIP,
    PERMISSION_FINANCE_VIEW,
    PERMISSION_CUSTOMER_GROUPS_MANAGE,
    PERMISSION_STORE_MEMBERS_MANAGE,
    STORE_OPERATION_PERMISSIONS,
    can_manage_store,
    get_accessible_stores,
    get_membership_permissions,
    is_platform_admin,
)
from users.models import AccountStatement, AccountTransaction, Address, CreditAccount, User


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
            "/api/stores/payment-configs/",
            "/api/stores/settlement-rules/",
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_role_permission_presets_are_exposed_on_membership(self):
        admin = StoreMember.objects.create(user=self.create_user("admin"), store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        sub_admin = StoreMember.objects.create(user=self.create_user("sub-admin"), store=self.partner, role=StoreMember.ROLE_STORE_SUB_ADMIN)

        self.assertIn(PERMISSION_ORDERS_ADJUST_AMOUNT, get_membership_permissions(admin))
        self.assertIn(PERMISSION_ORDERS_SHIP, get_membership_permissions(sub_admin))
        self.assertNotIn(PERMISSION_ORDERS_ADJUST_AMOUNT, get_membership_permissions(sub_admin))
        self.assertTrue(can_manage_store(sub_admin.user, self.partner))

    def test_merchant_route_permission_map_uses_backend_permission_codes(self):
        repo_root = Path(__file__).resolve().parents[3]
        permissions_file = repo_root / "merchant" / "src" / "utils" / "permissions.ts"
        permission_map_text = permissions_file.read_text(encoding="utf-8")
        merchant_permission_codes = set(re.findall(r":\s*'([^']+)'", permission_map_text))
        backend_permission_codes = STORE_OPERATION_PERMISSIONS | {
            PERMISSION_STORE_MEMBERS_MANAGE,
            PERMISSION_CUSTOMER_GROUPS_MANAGE,
        }

        self.assertTrue(merchant_permission_codes)
        self.assertEqual(merchant_permission_codes - backend_permission_codes, set())

    def test_store_admin_can_adjust_own_store_pending_order(self):
        admin = self.create_user("partner-admin", is_staff=True, role="admin")
        customer = self.create_user("customer")
        StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        product = self.create_store_product(self.partner, "Own product")
        order = Order.objects.create(
            user=customer,
            product=product,
            store=self.partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
            status="pending",
        )

        self.client.force_authenticate(admin)
        response = self.client.post(
            f"/api/orders/{order.id}/adjust_amount/",
            {"actual_amount": "90.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertEqual(order.actual_amount, Decimal("90.00"))

    def test_store_sub_admin_can_ship_but_cannot_adjust_amount(self):
        sub_admin = self.create_user("partner-sub-admin", is_staff=True, role="admin")
        customer = self.create_user("customer")
        StoreMember.objects.create(user=sub_admin, store=self.partner, role=StoreMember.ROLE_STORE_SUB_ADMIN)
        product = self.create_store_product(self.partner, "Own product")
        order = Order.objects.create(
            user=customer,
            product=product,
            store=self.partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
            status="paid",
        )

        self.client.force_authenticate(sub_admin)
        adjust_response = self.client.post(
            f"/api/orders/{order.id}/adjust_amount/",
            {"actual_amount": "90.00"},
            format="json",
        )
        ship_response = self.client.patch(
            f"/api/orders/{order.id}/ship/",
            {"express_company": "STO", "logistics_no": "STO123456"},
            format="json",
        )

        self.assertEqual(adjust_response.status_code, 403)
        self.assertEqual(ship_response.status_code, 200, ship_response.content)
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")

    def test_store_admin_can_create_sub_admin_for_own_store_only(self):
        admin = self.create_user("partner-admin", is_staff=True, role="admin")
        sub_admin = self.create_user("new-sub-admin")
        platform_member = self.create_user("new-platform-member")
        StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

        self.client.force_authenticate(admin)
        create_response = self.client.post(
            "/api/stores/members/",
            {
                "user": sub_admin.id,
                "store": self.partner.id,
                "role": StoreMember.ROLE_STORE_SUB_ADMIN,
                "status": StoreMember.STATUS_ACTIVE,
            },
            format="json",
        )
        platform_response = self.client.post(
            "/api/stores/members/",
            {
                "user": platform_member.id,
                "store": self.partner.id,
                "role": StoreMember.ROLE_PLATFORM_ADMIN,
                "status": StoreMember.STATUS_ACTIVE,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201, create_response.content)
        self.assertEqual(platform_response.status_code, 403)

    def test_store_staff_with_staff_flag_still_sees_only_own_store_payments_and_invoices(self):
        user = self.create_user("legacy-staff", is_staff=True, role="admin")
        customer = self.create_user("customer")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_STAFF)
        own_product = self.create_store_product(self.partner, "Own product")
        other_product = self.create_store_product(self.other_partner, "Other product")
        own_order = Order.objects.create(
            user=customer,
            product=own_product,
            store=self.partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
        )
        other_order = Order.objects.create(
            user=customer,
            product=other_product,
            store=self.other_partner,
            quantity=1,
            total_amount=Decimal("200.00"),
            actual_amount=Decimal("200.00"),
        )
        Payment.create_for_order(own_order)
        Payment.create_for_order(other_order)
        Invoice.objects.create(
            order=own_order,
            user=customer,
            title="Own invoice",
            amount=Decimal("100.00"),
        )
        Invoice.objects.create(
            order=other_order,
            user=customer,
            title="Other invoice",
            amount=Decimal("200.00"),
        )

        self.client.force_authenticate(user)
        payments_response = self.client.get("/api/payments/")
        invoices_response = self.client.get("/api/invoices/")

        self.assertEqual(payments_response.status_code, 200, payments_response.content)
        self.assertEqual(invoices_response.status_code, 200, invoices_response.content)
        payments = payments_response.data["results"]
        invoices = invoices_response.data["results"]
        self.assertEqual([item["order"] for item in payments], [own_order.id])
        self.assertEqual([item["title"] for item in invoices], ["Own invoice"])

    def test_store_admin_cannot_start_customer_payment(self):
        admin = self.create_user("partner-admin-payment", is_staff=True, role="admin")
        customer = self.create_user("customer-payment")
        StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        product = self.create_store_product(self.partner, "Payment product")
        order = Order.objects.create(
            user=customer,
            product=product,
            store=self.partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
            status="pending",
        )
        payment = Payment.create_for_order(order)

        self.client.force_authenticate(admin)
        response = self.client.post(f"/api/payments/{payment.id}/start/", {}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_store_staff_cannot_create_order_for_another_user_with_staff_flag(self):
        user = self.create_user("legacy-order-staff", is_staff=True, role="admin")
        customer = self.create_user("target-customer")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_STAFF)
        product = self.create_store_product(self.partner, "Create order product")
        address = Address.objects.create(
            user=user,
            contact_name="Tester",
            phone="13800000000",
            province="Zhejiang",
            city="Hangzhou",
            district="Xihu",
            detail="No.1",
        )

        self.client.force_authenticate(user)
        response = self.client.post(
            "/api/orders/create_order/",
            {
                "product_id": product.id,
                "address_id": address.id,
                "quantity": 1,
                "user_id": customer.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_store_admin_cannot_manage_global_cases(self):
        user = self.create_user("partner-case-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        media = MediaImage.objects.create(file="images/case.png", original_name="case.png")

        self.client.force_authenticate(user)
        response = self.client.post(
            "/api/catalog/cases/",
            {"title": "Store case", "cover_image_id": media.id, "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Case.objects.filter(title="Store case").exists())

    def test_finance_permission_filters_store_account_data(self):
        staff = self.create_user("finance-staff", is_staff=True, role="admin")
        admin = self.create_user("finance-admin", is_staff=True, role="admin")
        customer = self.create_user("finance-customer", role="dealer")
        StoreMember.objects.create(user=staff, store=self.partner, role=StoreMember.ROLE_STORE_STAFF)
        admin_membership = StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        product = self.create_store_product(self.partner, "Finance product")
        order = Order.objects.create(
            user=customer,
            product=product,
            store=self.partner,
            quantity=1,
            total_amount=Decimal("100.00"),
            actual_amount=Decimal("100.00"),
        )
        account = CreditAccount.objects.create(user=customer, credit_limit=Decimal("1000.00"))
        statement = AccountStatement.objects.create(
            credit_account=account,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            current_purchases=Decimal("100.00"),
            period_end_balance=Decimal("100.00"),
        )
        AccountTransaction.objects.create(
            credit_account=account,
            statement=statement,
            order_id=order.id,
            transaction_type="purchase",
            amount=Decimal("100.00"),
            balance_after=Decimal("100.00"),
        )

        self.assertIn(PERMISSION_FINANCE_VIEW, get_membership_permissions(admin_membership))

        self.client.force_authenticate(staff)
        staff_statements = self.client.get("/api/account-statements/")
        staff_transactions = self.client.get("/api/account-transactions/")

        self.client.force_authenticate(admin)
        admin_statements = self.client.get("/api/account-statements/")
        admin_transactions = self.client.get("/api/account-transactions/")
        admin_confirm = self.client.post(f"/api/account-statements/{statement.id}/confirm/")

        self.assertEqual(staff_statements.status_code, 200, staff_statements.content)
        self.assertEqual(staff_transactions.status_code, 200, staff_transactions.content)
        self.assertEqual(staff_statements.data["results"], [])
        self.assertEqual(staff_transactions.data["results"], [])
        self.assertEqual([item["id"] for item in admin_statements.data["results"]], [statement.id])
        self.assertEqual([item["id"] for item in admin_transactions.data["results"]], [statement.transactions.first().id])
        self.assertEqual(admin_confirm.status_code, 403)
        statement.refresh_from_db()
        self.assertEqual(statement.status, "draft")

    def test_store_admin_can_export_only_own_store_products(self):
        admin = self.create_user("partner-product-export-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        self.create_store_product(self.partner, "Own export product")
        self.create_store_product(self.other_partner, "Other export product")

        self.client.force_authenticate(admin)
        response = self.client.get("/api/catalog/products/export/")

        self.assertEqual(response.status_code, 200, response.content)

    def test_store_admin_can_manage_store_activity_but_not_platform_activity(self):
        admin = self.create_user("partner-zone-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

        self.client.force_authenticate(admin)
        create_store_zone = self.client.post(
            "/api/catalog/special-zones/",
            {
                "store_id": self.partner.id,
                "title": "Store activity",
                "slug": "store-activity",
                "kind": "store_activity",
                "is_active": True,
                "show_on_home": True,
            },
            format="json",
        )
        create_platform_zone = self.client.post(
            "/api/catalog/special-zones/",
            {
                "store_id": self.partner.id,
                "title": "Platform activity",
                "slug": "platform-activity",
                "kind": "platform_activity",
                "is_active": True,
                "show_on_home": True,
            },
            format="json",
        )

        self.assertEqual(create_store_zone.status_code, 201, create_store_zone.content)
        self.assertEqual(create_platform_zone.status_code, 403)

    def test_store_admin_cannot_delete_global_media_image(self):
        admin = self.create_user("partner-media-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=admin, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)
        media = MediaImage.objects.create(file="images/global.png", original_name="global.png")

        self.client.force_authenticate(admin)
        delete_response = self.client.delete(f"/api/catalog/media-images/{media.id}/")
        upload_response = self.client.post(
            "/api/catalog/media-images/",
            {"file": SimpleUploadedFile("evidence.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(upload_response.status_code, 201, upload_response.content)
        self.assertTrue(MediaImage.objects.filter(id=media.id).exists())

    def test_store_admin_with_staff_flag_cannot_access_support_backend(self):
        user = self.create_user("legacy-support-store-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

        self.client.force_authenticate(user)
        conversations_response = self.client.get("/api/support/chat/conversations/")
        templates_response = self.client.get("/api/support/reply-templates/")

        self.assertEqual(conversations_response.status_code, 403)
        self.assertEqual(templates_response.status_code, 403)

    def test_store_admin_with_staff_flag_cannot_access_integrations_backend(self):
        user = self.create_user("legacy-integration-store-admin", is_staff=True, role="admin")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

        self.client.force_authenticate(user)
        config_response = self.client.get("/api/haier/config/")
        delivery_company_response = self.client.get("/api/haier/wechat/delivery-companies/")

        self.assertEqual(config_response.status_code, 403)
        self.assertEqual(delivery_company_response.status_code, 403)

    def test_support_password_login_preserves_support_role(self):
        self.create_user("platform-login-admin", is_staff=True, is_superuser=True, role="admin")
        support = self.create_user("support-login-user", is_staff=True, role="support")

        response = self.client.post(
            "/api/admin/login/",
            {"username": "support-login-user", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        support.refresh_from_db()
        self.assertEqual(support.role, "support")

    def test_store_member_password_login_without_existing_staff_does_not_promote_to_platform_admin(self):
        user = self.create_user("first-store-login")
        StoreMember.objects.create(user=user, store=self.partner, role=StoreMember.ROLE_STORE_ADMIN)

        response = self.client.post(
            "/api/admin/login/",
            {"username": "first-store-login", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(is_platform_admin(user))
