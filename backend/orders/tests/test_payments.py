from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from orders.models import Payment, Order
from orders.payment_service import PaymentService
from catalog.models import Category, Brand, Product
from users.models import Notification


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u1', password='pass')
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

    def test_ensure_payment_startable_expired(self):
        payment = Payment.create_for_order(self.order, method='wechat', ttl_minutes=0)
        # 手动将过期时间设置到过去
        payment.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        payment.save(update_fields=['expires_at'])

        ok, reason = PaymentService.ensure_payment_startable(payment)
        self.assertFalse(ok)
        self.assertIn('过期', reason)

    @override_settings(PAYMENT_MAX_AMOUNT=Decimal('50'))
    def test_amount_threshold_blocks_large_payment(self):
        ok, msg = PaymentService.check_amount_threshold(self.order)
        self.assertFalse(ok)
        self.assertIn('上限', msg)

    def test_client_frequency_limits(self):
        ok1, _ = PaymentService.check_client_frequency(self.user, client_ip='1.1.1.1', device_id='dev1', window_seconds=30, limit=1)
        ok2, msg2 = PaymentService.check_client_frequency(self.user, client_ip='1.1.1.1', device_id='dev1', window_seconds=30, limit=1)
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertIn('过于频繁', msg2)

    def test_process_payment_success_updates_order_and_notification(self):
        payment = Payment.create_for_order(self.order, method='wechat', ttl_minutes=10)
        PaymentService.process_payment_success(payment.id, transaction_id='tx-123', operator=self.user)

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(payment.status, 'succeeded')
        self.assertEqual(self.order.status, 'paid')
        # 通知已写入
        self.assertTrue(Notification.objects.filter(user=self.user, type='payment', status='pending').exists())

    def test_validate_callback_amount_supports_wechat_amount_dict(self):
        payment = Payment.create_for_order(self.order, method='wechat', ttl_minutes=5)
        data = {'amount': {'total': int(payment.amount * 100)}}

        ok, msg = PaymentService.validate_callback_amount(payment, data)

        self.assertTrue(ok)
        self.assertEqual(msg, '')
