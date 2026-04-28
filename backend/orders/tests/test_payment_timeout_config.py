from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from catalog.models import Brand, Category, Product
from orders.models import Order, Payment


class PaymentTimeoutConfigTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='timeout_user', password='pass')
        self.category = Category.objects.create(name='家电', level=Category.LEVEL_MAJOR)
        self.brand = Brand.objects.create(name='品牌A')
        self.product = Product.objects.create(
            name='测试商品',
            category=self.category,
            brand=self.brand,
            price=Decimal('99.00'),
            stock=10,
        )
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total_amount=Decimal('99.00'),
            actual_amount=Decimal('99.00'),
            status='pending',
            snapshot_contact_name='张三',
            snapshot_phone='13800000000',
            snapshot_address='地址',
        )

    @override_settings(ORDER_PAYMENT_TIMEOUT_MINUTES=1440)
    def test_create_for_order_uses_24h_timeout_from_settings(self):
        created_before = timezone.now()
        payment = Payment.create_for_order(self.order, method='wechat')
        created_after = timezone.now()

        min_expected = created_before + timedelta(minutes=1440)
        max_expected = created_after + timedelta(minutes=1440)

        self.assertGreaterEqual(payment.expires_at, min_expected)
        self.assertLessEqual(payment.expires_at, max_expected)
