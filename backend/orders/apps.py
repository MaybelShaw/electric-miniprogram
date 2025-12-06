from django.apps import AppConfig
import os
import threading
import time
import logging
from django.conf import settings
from django.utils import timezone


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        if getattr(self, '_auto_cancel_started', False):
            return
        run_main = os.environ.get('RUN_MAIN') == 'true'
        if settings.DEBUG and not run_main:
            return
        logger = logging.getLogger(__name__)

        def _worker():
            from django.db import close_old_connections
            from datetime import timedelta
            from orders.models import Order
            from orders.state_machine import OrderStateMachine
            from common.audit_logger import AuditLogger
            from django.conf import settings as dj_settings
            while True:
                try:
                    now = timezone.now()
                    cutoff = now - timedelta(minutes=getattr(dj_settings, 'ORDER_PAYMENT_TIMEOUT_MINUTES', 10))
                    qs = Order.objects.filter(status='pending', created_at__lt=cutoff).prefetch_related('payments')
                    for order in qs:
                        if order.payments.filter(status='succeeded').exists():
                            continue
                        order.payments.filter(status__in=['init', 'processing']).update(status='expired', updated_at=now)
                        order.cancel_reason = '超时未支付自动取消'
                        order.cancelled_at = now
                        order.save(update_fields=['cancel_reason', 'cancelled_at'])
                        try:
                            OrderStateMachine.transition(order, 'cancelled', operator=None, note='超时未支付自动取消')
                            AuditLogger.log_order_cancelled(order.id, 'payment_timeout', None)
                        except Exception as e:
                            logger.error(f'auto-cancel failed: {str(e)}')
                except Exception as e:
                    logger.error(f'auto-cancel error: {str(e)}')
                finally:
                    try:
                        close_old_connections()
                    except Exception:
                        pass
                time.sleep(60)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        self._auto_cancel_started = True
