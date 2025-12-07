from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from catalog.models import Category, Brand, Product, ProductSKU
from users.models import Address
from orders.services import create_order, cancel_order
from orders.models import Cart, CartItem


class OrderItemTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='pwd')
        self.category = Category.objects.create(name='家电', level=Category.LEVEL_MAJOR)
        self.brand = Brand.objects.create(name='测试品牌')
        self.product = Product.objects.create(
            name='多规格商品',
            category=self.category,
            brand=self.brand,
            price=Decimal('499.00'),
            stock=50,
        )
        self.sku_red = ProductSKU.objects.create(
            product=self.product,
            name='红色',
            sku_code='RED',
            specs={'颜色': '红'},
            price=Decimal('499.00'),
            stock=5,
        )
        self.sku_blue = ProductSKU.objects.create(
            product=self.product,
            name='蓝色',
            sku_code='BLUE',
            specs={'颜色': '蓝'},
            price=Decimal('599.00'),
            stock=10,
        )
        self.address = Address.objects.create(
            user=self.user,
            contact_name='张三',
            phone='13800000000',
            province='北京',
            city='北京',
            district='海淀',
            detail='中关村大街1号',
            is_default=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_order_with_multiple_skus(self):
        order = create_order(
            user=self.user,
            address_id=self.address.id,
            items=[
                {'product_id': self.product.id, 'sku_id': self.sku_red.id, 'quantity': 2},
                {'product_id': self.product.id, 'sku_id': self.sku_blue.id, 'quantity': 1},
            ],
            payment_method='online',
        )
        order.refresh_from_db()
        self.sku_red.refresh_from_db()
        self.sku_blue.refresh_from_db()

        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.quantity, 3)
        self.assertEqual(order.total_amount, Decimal('1597.00'))  # 499*2 + 599*1
        self.assertEqual(order.discount_amount, Decimal('0'))
        self.assertEqual(order.actual_amount, Decimal('1597.00'))
        self.assertEqual(self.sku_red.stock, 3)
        self.assertEqual(self.sku_blue.stock, 9)

    def test_cancel_order_releases_sku_stock(self):
        order = create_order(
            user=self.user,
            address_id=self.address.id,
            items=[{'product_id': self.product.id, 'sku_id': self.sku_red.id, 'quantity': 2}],
            payment_method='online',
        )
        self.sku_red.refresh_from_db()
        self.assertEqual(self.sku_red.stock, 3)

        cancel_order(order)
        self.sku_red.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.sku_red.stock, 5)

    def test_batch_create_order_api_returns_items_and_payment(self):
        url = reverse('order-create-batch-orders')
        payload = {
            'address_id': self.address.id,
            'items': [{'product_id': self.product.id, 'sku_id': self.sku_red.id, 'quantity': 2}],
            'payment_method': 'online',
        }
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        order = data.get('order') or {}
        payment = data.get('payment') or {}
        self.assertEqual(order.get('quantity'), 2)
        self.assertTrue(order.get('items'))
        self.assertEqual(order['items'][0]['sku_id'], self.sku_red.id)
        self.assertIsNotNone(payment)
        self.assertEqual(Decimal(str(payment['amount'])), Decimal(order['actual_amount']))

    def test_cart_crud_with_sku(self):
        add_url = reverse('cart-add-item')
        update_url = reverse('cart-update-item')
        remove_url = reverse('cart-remove-item')

        # add
        resp = self.client.post(add_url, {'product_id': self.product.id, 'sku_id': self.sku_red.id, 'quantity': 1}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        cart_data = resp.json()
        self.assertEqual(cart_data['items'][0]['sku_id'], self.sku_red.id)

        # update within stock
        resp = self.client.post(update_url, {'product_id': self.product.id, 'sku_id': self.sku_red.id, 'quantity': 3}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['items'][0]['quantity'], 3)

        # update exceeding stock fails
        resp = self.client.post(update_url, {'product_id': self.product.id, 'sku_id': self.sku_red.id, 'quantity': 99}, format='json')
        self.assertEqual(resp.status_code, 400)

        # remove
        resp = self.client.post(remove_url, {'product_id': self.product.id, 'sku_id': self.sku_red.id}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['items'], [])
