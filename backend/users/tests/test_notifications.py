from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User, Notification
from users.services import create_notification


class NotificationServiceTests(TestCase):
    @override_settings(
        WECHAT_APPID='appid',
        WECHAT_SECRET='secret',
        WECHAT_SUBSCRIBE_TEMPLATES={'payment': {'template_id': 'tmpl123', 'page': 'pages/order-detail/index'}}
    )
    @patch('users.notification_service.WeChatMiniProgramClient.send_subscribe_message', return_value=(True, ''))
    def test_create_notification_marks_sent_and_uses_templates(self, mock_send):
        user = User.objects.create_user(username='u1', password='pass', openid='openid-1')

        notif = create_notification(
            user,
            title='支付成功',
            content='订单 123 支付成功',
            ntype='payment',
            metadata={
                'order_id': 123,
                'order_number': '123',
                'subscription_data': {'thing1': {'value': '订单 123'}}
            }
        )

        self.assertIsNotNone(notif)
        notif.refresh_from_db()
        self.assertEqual(notif.status, 'sent')
        self.assertIsNotNone(notif.sent_at)

        self.assertTrue(mock_send.called)
        _, kwargs = mock_send.call_args
        self.assertEqual(kwargs.get('touser'), 'openid-1')
        self.assertEqual(kwargs.get('template_id'), 'tmpl123')
        self.assertIn('data', kwargs)


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass', openid='openid-api')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_mark_read_and_stats(self):
        n1 = Notification.objects.create(user=self.user, title='待读', content='hello', type='order')
        n2 = Notification.objects.create(
            user=self.user,
            title='已读',
            content='world',
            type='payment',
            read_at=timezone.now()
        )

        resp = self.client.get('/api/notifications/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data.get('results', [])), 2)

        resp_stats = self.client.get('/api/notifications/stats/')
        self.assertEqual(resp_stats.status_code, 200)
        self.assertEqual(resp_stats.data.get('unread_count'), 1)

        resp_mark = self.client.post(f'/api/notifications/{n1.id}/mark_read/')
        self.assertEqual(resp_mark.status_code, 200)
        n1.refresh_from_db()
        self.assertIsNotNone(n1.read_at)

        resp_all = self.client.post('/api/notifications/mark_all_read/')
        self.assertEqual(resp_all.status_code, 200)
        n2.refresh_from_db()
        self.assertIsNotNone(n2.read_at)

        resp_stats2 = self.client.get('/api/notifications/stats/')
        self.assertEqual(resp_stats2.data.get('unread_count'), 0)

    def test_filter_by_type_and_read_flag(self):
        Notification.objects.create(user=self.user, title='支付', content='c1', type='payment')
        Notification.objects.create(user=self.user, title='订单', content='c2', type='order', read_at=timezone.now())

        resp_payment = self.client.get('/api/notifications/', {'type': 'payment'})
        self.assertEqual(resp_payment.status_code, 200)
        self.assertEqual(len(resp_payment.data.get('results', [])), 1)

        resp_unread = self.client.get('/api/notifications/', {'read': 'false'})
        self.assertEqual(resp_unread.status_code, 200)
        self.assertEqual(len(resp_unread.data.get('results', [])), 1)

        resp_read = self.client.get('/api/notifications/', {'read': 'true'})
        self.assertEqual(resp_read.status_code, 200)
        self.assertEqual(len(resp_read.data.get('results', [])), 1)
