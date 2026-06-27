from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Brand, Category, Product
from orders.models import Payment, StoreProfitSharingEntry
from orders.payment_service import PaymentService
from orders.services import create_order_with_split
from stores.models import Store, StoreMember
from users.models import Address


class ProfitSharingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="buyer-profit", password="pwd")
        self.platform_admin = get_user_model().objects.create_user(username="platform-admin-profit", password="pwd", is_staff=True)
        self.main_store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        StoreMember.objects.create(
            user=self.platform_admin,
            store=self.main_store,
            role=StoreMember.ROLE_PLATFORM_ADMIN,
        )
        self.partner_store = Store.objects.create(
            name="Partner Display",
            code="partner-display-profit",
            store_type=Store.TYPE_PARTNER,
        )
        self.address = Address.objects.create(
            user=self.user,
            contact_name="Buyer",
            phone="13800000000",
            province="Beijing",
            city="Beijing",
            district="Haidian",
            detail="No.1 Road",
            is_default=True,
        )
        self.main_product = self._create_product(self.main_store, "Main Product", Decimal("100.00"))
        self.partner_product = self._create_product(self.partner_store, "Partner Product", Decimal("200.00"))

    def _create_product(self, store, name, price):
        category = Category.objects.create(store=store, name=f"{name} Category", level=Category.LEVEL_MAJOR)
        brand = Brand.objects.create(store=store, name=f"{name} Brand")
        return Product.objects.create(store=store, name=name, category=category, brand=brand, price=price, stock=20)

    def _create_checkout_payment(self):
        order = create_order_with_split(
            user=self.user,
            items=[
                {"product_id": self.main_product.id, "quantity": 1},
            ],
            address_id=self.address.id,
            payment_method="online",
        )
        payment = Payment.create_for_order(order, method="wechat", ttl_minutes=10)
        return order, payment

    def test_payment_for_partner_checkout_uses_plain_wechat_payment(self):
        _, payment = self._create_checkout_payment()

        self.assertFalse(payment.profit_sharing_required)
        self.assertEqual(payment.profit_sharing_status, "not_required")

    def test_payment_success_creates_platform_retained_entry(self):
        order, payment = self._create_checkout_payment()

        PaymentService.process_payment_success(payment.id, transaction_id="tx-profit-001", operator=self.user)

        entries = StoreProfitSharingEntry.objects.filter(checkout_order=order.checkout_order).order_by("store_id")
        self.assertEqual(entries.count(), 1)
        statuses = {entry.store_id: entry.status for entry in entries}
        self.assertEqual(statuses[self.main_store.id], "platform_retained")

        payment.refresh_from_db()
        self.assertEqual(payment.profit_sharing_status, "not_required")

    def test_partner_product_is_display_only(self):
        with self.assertRaisesMessage(ValueError, "仅展示"):
            create_order_with_split(
                user=self.user,
                items=[{"product_id": self.partner_product.id, "quantity": 1}],
                address_id=self.address.id,
                payment_method="online",
            )
