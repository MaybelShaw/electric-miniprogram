from datetime import timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product
from orders.models import (
    Order,
    OrderItem,
    OrderShippingAction,
    OrderShippingSync,
    OrderStatusHistory,
    Payment,
)
from orders.serializers import OrderSerializer
from orders.shipping_action_service import (
    ShippingActionError,
    build_shipping_snapshot,
    cancel_shipping,
    is_haier_order,
)


class ShippingFixtureMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='shipping-buyer',
            password='pwd',
        )
        self.operator = get_user_model().objects.create_user(
            username='shipping-admin',
            password='pwd',
            is_staff=True,
        )
        self.category = Category.objects.create(
            name='发货测试品类',
            level=Category.LEVEL_MAJOR,
        )
        self.brand = Brand.objects.create(name='发货测试品牌')
        self.product = Product.objects.create(
            name='本地测试商品',
            category=self.category,
            brand=self.brand,
            price=Decimal('100.00'),
            stock=10,
            source=Product.SOURCE_LOCAL,
        )
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total_amount=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
            status='shipped',
        )
        self.order.logistics_no = 'KY4001016483553'
        self.order.delivery_record_code = 'DELIVERY-1'
        self.order.sn_code = 'SN-1'
        self.order.shipping_info = {
            'logistics_type': 1,
            'delivery_mode': 1,
            'shipping_list': [{
                'express_company': 'KYSY',
                'tracking_no': 'KY4001016483553',
                'item_desc': '测试商品*1',
            }],
        }
        self.order.delivery_images = ['https://cdn.example.com/delivery.jpg']
        self.order.save()


class ShippingActionModelTests(ShippingFixtureMixin, TestCase):
    def test_only_one_successful_cancel_shipping_action_is_allowed(self):
        OrderShippingAction.objects.create(
            order=self.order,
            action='cancel_shipping',
            status='succeeded',
            operator=self.operator,
            reason='第一次取消',
            shipping_snapshot={'logistics_no': 'SF001'},
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderShippingAction.objects.create(
                    order=self.order,
                    action='cancel_shipping',
                    status='succeeded',
                    operator=self.operator,
                    reason='第二次取消',
                    shipping_snapshot={'logistics_no': 'SF002'},
                )

    def test_failed_cancel_does_not_consume_successful_cancel_slot(self):
        OrderShippingAction.objects.create(
            order=self.order,
            action='cancel_shipping',
            status='failed',
            operator=self.operator,
            reason='失败尝试',
        )

        action = OrderShippingAction.objects.create(
            order=self.order,
            action='cancel_shipping',
            status='succeeded',
            operator=self.operator,
            reason='成功取消',
        )

        self.assertEqual(action.status, 'succeeded')


class CancelShippingServiceTests(ShippingFixtureMixin, TestCase):
    def test_build_shipping_snapshot_contains_all_current_fields(self):
        snapshot = build_shipping_snapshot(self.order)

        self.assertEqual(snapshot['logistics_no'], 'KY4001016483553')
        self.assertEqual(snapshot['delivery_record_code'], 'DELIVERY-1')
        self.assertEqual(snapshot['sn_code'], 'SN-1')
        self.assertEqual(snapshot['shipping_info']['shipping_list'][0]['express_company'], 'KYSY')
        self.assertEqual(snapshot['delivery_images'], ['https://cdn.example.com/delivery.jpg'])

    def test_local_child_order_is_not_treated_as_haier(self):
        self.order.order_type = 'local'
        self.order.save(update_fields=['order_type'])

        self.assertFalse(is_haier_order(self.order))

    def test_haier_order_is_detected_by_legacy_signals(self):
        for field, value in (
            ('order_type', 'haier'),
            ('haier_so_id', 'SO-1'),
            ('haier_order_no', 'H-1'),
            ('haier_status', 'confirmed'),
        ):
            order = Order.objects.get(pk=self.order.pk)
            setattr(order, field, value)
            self.assertTrue(is_haier_order(order), field)

        self.product.source = Product.SOURCE_HAIER
        self.product.save(update_fields=['source'])
        self.assertTrue(is_haier_order(Order.objects.get(pk=self.order.pk)))

    @patch('users.services.create_notification')
    def test_cancel_shipping_restores_paid_and_preserves_snapshot(self, notify):
        action = cancel_shipping(
            order_id=self.order.id,
            operator=self.operator,
            reason='物流单号填写错误',
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertEqual(self.order.logistics_no, '')
        self.assertEqual(self.order.delivery_record_code, '')
        self.assertEqual(self.order.sn_code, '')
        self.assertEqual(self.order.shipping_info, {})
        self.assertEqual(self.order.delivery_images, [])
        self.assertEqual(action.action, 'cancel_shipping')
        self.assertEqual(action.status, 'succeeded')
        self.assertEqual(action.shipping_snapshot['logistics_no'], 'KY4001016483553')
        self.assertTrue(OrderStatusHistory.objects.filter(
            order=self.order,
            from_status='shipped',
            to_status='paid',
            note='取消发货：物流单号填写错误',
        ).exists())
        notify.assert_not_called()

    def test_cancel_shipping_locks_order_without_joining_nullable_relations(self):
        with CaptureQueriesContext(connection) as queries:
            cancel_shipping(
                order_id=self.order.id,
                operator=self.operator,
                reason='物流单号填写错误',
            )

        order_queries = [
            query['sql']
            for query in queries.captured_queries
            if 'FROM "orders_order"' in query['sql']
            and '"orders_order"."id"' in query['sql']
        ]
        self.assertTrue(order_queries)
        self.assertNotIn(' JOIN ', order_queries[0].upper())

    def test_cancel_shipping_validates_reason_status_haier_and_usage(self):
        with self.assertRaisesMessage(ShippingActionError, '取消原因不能为空'):
            cancel_shipping(self.order.id, self.operator, '   ')

        self.order.status = 'paid'
        self.order.save(update_fields=['status'])
        with self.assertRaisesMessage(ShippingActionError, '仅已发货订单可以取消发货'):
            cancel_shipping(self.order.id, self.operator, '测试')

        self.order.status = 'shipped'
        self.order.order_type = 'haier'
        self.order.save(update_fields=['status', 'order_type'])
        with self.assertRaisesMessage(ShippingActionError, '海尔订单不支持取消发货'):
            cancel_shipping(self.order.id, self.operator, '测试')

        self.order.order_type = 'local'
        self.order.save(update_fields=['order_type'])
        cancel_shipping(self.order.id, self.operator, '第一次取消')
        self.order.status = 'shipped'
        self.order.save(update_fields=['status'])
        with self.assertRaisesMessage(ShippingActionError, '该订单已使用取消发货机会'):
            cancel_shipping(self.order.id, self.operator, '第二次取消')


class ShippingActionApiTests(ShippingFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.operator)

    def test_order_serializer_exposes_shipping_capabilities(self):
        data = OrderSerializer(self.order).data

        self.assertTrue(data['can_cancel_shipping'])
        self.assertFalse(data['is_reshipment_pending'])
        self.assertFalse(data['reship_requires_wechat_sync'])
        self.assertEqual(data['shipping_cancel_count'], 0)

    def test_admin_can_cancel_shipping_through_api(self):
        response = self.client.patch(
            reverse('order-cancel-shipping', args=[self.order.id]),
            {'reason': '仓库取消出库'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'paid')
        self.assertFalse(response.json()['can_cancel_shipping'])
        self.assertTrue(response.json()['is_reshipment_pending'])
        self.assertEqual(response.json()['shipping_cancel_count'], 1)

    def test_customer_cannot_cancel_shipping_or_read_history(self):
        self.client.force_authenticate(self.user)

        cancel_response = self.client.patch(
            reverse('order-cancel-shipping', args=[self.order.id]),
            {'reason': '测试'},
            format='json',
        )
        history_response = self.client.get(
            reverse('order-shipping-actions', args=[self.order.id]),
        )

        self.assertEqual(cancel_response.status_code, 403)
        self.assertEqual(history_response.status_code, 403)

    def test_history_endpoint_returns_snapshot_for_admin(self):
        cancel_shipping(self.order.id, self.operator, '物流单号填写错误')

        response = self.client.get(
            reverse('order-shipping-actions', args=[self.order.id]),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()[0]['action'], 'cancel_shipping')
        self.assertEqual(
            response.json()[0]['shipping_snapshot']['logistics_no'],
            'KY4001016483553',
        )
        self.assertEqual(response.json()[0]['operator_username'], 'shipping-admin')

    def test_cancel_shipping_api_returns_business_error(self):
        response = self.client.patch(
            reverse('order-cancel-shipping', args=[self.order.id]),
            {'reason': '   '},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '取消原因不能为空')


class ReshipApiTests(ShippingFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user.openid = 'test-openid'
        self.user.save(update_fields=['openid'])
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        Payment.objects.create(
            order=self.order,
            amount=self.order.actual_amount,
            method='wechat',
            status='succeeded',
            expires_at=timezone.now() + timedelta(days=1),
            logs=[{'transaction_id': '4200000000000000000000000001'}],
        )
        OrderShippingSync.objects.create(
            order=self.order,
            status='succeeded',
            payload={'shipping_list': [{'tracking_no': 'OLD001'}]},
            response={'errcode': 0, 'errmsg': 'ok'},
        )
        cancel_shipping(self.order.id, self.operator, '原物流信息错误')
        self.order.refresh_from_db()

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=True)
    @patch('orders.wechat_shipping_service.upload_shipping_info')
    def test_wechat_reship_success_records_action_and_ships_order(self, upload):
        upload.return_value = (True, {'errcode': 0, 'errmsg': 'ok'}, '')

        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
                'item_desc': '本地测试商品*1',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')
        self.assertFalse(response.json()['is_reshipment_pending'])
        self.assertFalse(response.json()['can_cancel_shipping'])
        action = self.order.shipping_actions.get(action='reship', status='succeeded')
        self.assertTrue(action.wechat_sync_required)
        self.assertTrue(action.wechat_synced)
        self.assertEqual(action.shipping_snapshot['logistics_no'], 'KY4001016483553')

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=True)
    @patch('orders.wechat_shipping_service.upload_shipping_info')
    def test_wechat_reship_10060003_rolls_back_and_records_failed_attempt(self, upload):
        upload.return_value = (
            False,
            {'errcode': 10060003, 'errmsg': 'reship used'},
            'reship used',
        )

        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
                'item_desc': '本地测试商品*1',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '该支付单已使用微信重新发货机会')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertEqual(self.order.logistics_no, '')
        self.assertFalse(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
        ).exists())
        failed = self.order.shipping_actions.get(action='reship', status='failed')
        self.assertEqual(failed.shipping_snapshot['logistics_no'], 'KY4001016483553')
        self.assertEqual(failed.wechat_response['errcode'], 10060003)

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=False)
    def test_required_wechat_reship_is_rejected_when_sync_is_disabled(self):
        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '微信发货同步已关闭，无法重新发货')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=True)
    def test_non_wechat_reship_only_updates_local_state(self):
        self.order.shipping_actions.filter(action='cancel_shipping').update(
            wechat_sync_required=False,
        )

        with patch('orders.wechat_shipping_service.upload_shipping_info') as upload:
            response = self.client.patch(
                reverse('order-ship', args=[self.order.id]),
                {
                    'express_company': 'KYSY',
                    'logistics_no': 'KY4001016483553',
                },
                format='json',
            )

        self.assertEqual(response.status_code, 200, response.content)
        upload.assert_not_called()
        self.assertTrue(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
            wechat_sync_required=False,
            wechat_synced=False,
        ).exists())

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=False)
    def test_first_ship_records_ship_action(self):
        first_order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total_amount=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
            status='paid',
        )

        response = self.client.patch(
            reverse('order-ship', args=[first_order.id]),
            {'express_company': 'KYSY', 'logistics_no': 'FIRST001'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()['can_cancel_shipping'])
        self.assertFalse(response.json()['is_reshipment_pending'])
        self.assertTrue(first_order.shipping_actions.filter(
            action='ship',
            status='succeeded',
        ).exists())


class ShippingActionRegressionTests(ShippingFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.operator)

    def test_legacy_order_without_ship_action_can_be_cancelled(self):
        self.assertFalse(self.order.shipping_actions.exists())

        action = cancel_shipping(self.order.id, self.operator, '旧订单纠错')

        self.assertEqual(action.shipping_snapshot['logistics_no'], 'KY4001016483553')

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=False)
    def test_credit_order_can_cancel_and_reship_locally(self):
        cancel_shipping(self.order.id, self.operator, '信用订单纠错')

        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {'express_company': 'KYSY', 'logistics_no': 'CREDIT001'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
            wechat_sync_required=False,
        ).exists())

    def test_order_item_with_haier_product_blocks_cancel(self):
        haier_product = Product.objects.create(
            name='海尔商品',
            category=self.category,
            brand=self.brand,
            price=Decimal('100.00'),
            stock=10,
            source=Product.SOURCE_HAIER,
        )
        OrderItem.objects.create(
            order=self.order,
            product=haier_product,
            product_name=haier_product.name,
            quantity=1,
            unit_price=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
        )

        with self.assertRaisesMessage(ShippingActionError, '海尔订单不支持取消发货'):
            cancel_shipping(self.order.id, self.operator, '测试')

    def test_generic_status_endpoint_cannot_bypass_cancel_shipping(self):
        response = self.client.patch(
            reverse('order-status', args=[self.order.id]),
            {'status': 'paid'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '请使用取消发货接口恢复待发货状态')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')


class CancelShippingConcurrencyTests(ShippingFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def _cancel(self):
        close_old_connections()
        operator = get_user_model().objects.get(pk=self.operator.id)
        try:
            cancel_shipping(self.order.id, operator, '并发取消')
            return 'ok'
        except ShippingActionError as exc:
            return str(exc)
        finally:
            close_old_connections()

    def test_only_one_concurrent_cancel_succeeds(self):
        if connection.vendor != 'postgresql':
            self.skipTest('select_for_update concurrency semantics require PostgreSQL')

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self._cancel(), range(2)))

        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(results.count('该订单已使用取消发货机会'), 1)
        self.assertEqual(OrderShippingAction.objects.filter(
            order_id=self.order.id,
            action='cancel_shipping',
            status='succeeded',
        ).count(), 1)
