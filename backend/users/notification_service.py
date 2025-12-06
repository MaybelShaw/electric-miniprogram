"""
Notification dispatch helpers: send subscription messages and manage delivery state.
"""
import logging
from django.conf import settings
from django.utils import timezone

from .models import Notification
from integrations.wechat import WeChatMiniProgramClient

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Handle pushing notifications to external channels (e.g., WeChat)."""

    @classmethod
    def dispatch(cls, notification: Notification | None):
        if not notification or not isinstance(notification, Notification):
            return None
        cls._send_wechat_subscription(notification)
        return notification

    @staticmethod
    def _get_template(notification: Notification):
        templates = getattr(settings, 'WECHAT_SUBSCRIBE_TEMPLATES', {}) or {}
        conf = templates.get(notification.type)
        default_page = getattr(settings, 'WECHAT_SUBSCRIBE_DEFAULT_PAGE', '')

        if not conf:
            return None, default_page

        if isinstance(conf, dict):
            return conf.get('template_id') or conf.get('id'), conf.get('page') or default_page
        return str(conf), default_page

    @staticmethod
    def _resolve_page(notification: Notification, configured_page: str | None) -> str:
        meta = notification.metadata or {}
        if isinstance(meta, dict):
            if meta.get('page'):
                return str(meta.get('page'))
            # Order detail page fallback
            order_id = meta.get('order_id')
            if order_id:
                return f'pages/order-detail/index?id={order_id}'
            statement_id = meta.get('statement_id')
            if statement_id:
                return f'pages/statement-detail/index?id={statement_id}'
        return configured_page or getattr(settings, 'WECHAT_SUBSCRIBE_DEFAULT_PAGE', '')

    @staticmethod
    def _build_payload(notification: Notification) -> dict:
        meta = notification.metadata or {}
        if isinstance(meta, dict) and isinstance(meta.get('subscription_data'), dict):
            return meta.get('subscription_data')

        # Fallback payload with generic keys; callers should pass subscription_data to fit templates
        created = notification.created_at
        created_str = ''
        try:
            created_str = timezone.localtime(created).strftime('%Y-%m-%d %H:%M') if created else ''
        except Exception:
            created_str = created.isoformat() if created else ''

        return {
            'thing1': {'value': notification.title[:20]},
            'time2': {'value': created_str},
            'thing3': {'value': (notification.content or '')[:20]},
        }

    @classmethod
    def _send_wechat_subscription(cls, notification: Notification):
        template_id, configured_page = cls._get_template(notification)
        if not template_id:
            return

        user_openid = getattr(notification.user, 'openid', None)
        if not user_openid:
            return

        payload = cls._build_payload(notification)
        page = cls._resolve_page(notification, configured_page)

        try:
            client = WeChatMiniProgramClient()
            ok, err = client.send_subscribe_message(
                touser=user_openid,
                template_id=template_id,
                page=page,
                data=payload,
            )
            if ok:
                notification.mark_sent()
            else:
                notification.status = 'failed'
                notification.save(update_fields=['status'])
                logger.warning('WeChat subscribe message failed: %s', err)
        except Exception as exc:
            logger.error('Dispatch subscription failed: %s', exc)
