from django.test import TestCase
from orders.models import Order, Payment
from users.models import User, CreditAccount, AccountTransaction
from orders.serializers import OrderSerializer
from catalog.models import Product
from decimal import Decimal

class OrderSerializerPaymentMethodTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.product = Product.objects.create(name='Test Product', price=100, stock=10)
        
    def test_payment_method_online(self):
        order = Order.objects.create(
            user=self.user,
            product=self.product,
            total_amount=100,
            actual_amount=100
        )
        Payment.objects.create(
            order=order,
            amount=100,
            method='wechat',
            status='succeeded',
            expires_at='2099-01-01 00:00:00+00:00'
        )
        
        serializer = OrderSerializer(order)
        self.assertEqual(serializer.data['payment_method'], 'wechat')
        
    def test_payment_method_credit(self):
        # Create credit account
        CreditAccount.objects.create(user=self.user, credit_limit=1000)
        
        order = Order.objects.create(
            user=self.user,
            product=self.product,
            total_amount=100,
            actual_amount=100
        )
        
        # Create credit transaction
        AccountTransaction.objects.create(
            credit_account=self.user.credit_account,
            transaction_type='purchase',
            amount=100,
            balance_after=900,
            order_id=order.id
        )
        
        serializer = OrderSerializer(order)
        self.assertEqual(serializer.data['payment_method'], 'credit')

    def test_payment_method_unknown(self):
        order = Order.objects.create(
            user=self.user,
            product=self.product,
            total_amount=100,
            actual_amount=100
        )
        serializer = OrderSerializer(order)
        self.assertEqual(serializer.data['payment_method'], 'unknown')
