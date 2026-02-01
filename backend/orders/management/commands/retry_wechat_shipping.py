from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.models import OrderShippingSync
from integrations.wechat import WeChatMiniProgramClient
from orders.wechat_shipping_service import _next_retry_time


class Command(BaseCommand):
    help = 'Retry failed WeChat shipping syncs (when failed records exist).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        limit = options.get('limit') or 50
        now = timezone.now()
        qs = (
            OrderShippingSync.objects
            .filter(status='failed')
            .filter(next_retry_at__lte=now)
            .select_related('order', 'order__user')
            .order_by('next_retry_at')
        )[:limit]

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No failed shipping syncs to retry. 当前策略不保留失败记录，请通过重新发货操作重试。'))
            return

        success = 0
        failed = 0
        for record in qs:
            payload = record.payload or {}
            client = WeChatMiniProgramClient()
            ok, resp, err = client.upload_shipping_info(payload)
            if ok or (isinstance(resp, dict) and resp.get('errcode') == 10060023):
                record.status = 'succeeded'
                record.response = resp or {}
                record.error = ''
                record.save(update_fields=['status', 'response', 'error', 'updated_at'])
                success += 1
            else:
                record.status = 'failed'
                record.response = resp or {}
                record.error = err or (resp.get('errmsg') if isinstance(resp, dict) else 'wechat_error')
                record.retry_count = record.retry_count + 1
                record.next_retry_at = _next_retry_time()
                record.save(update_fields=['status', 'response', 'error', 'retry_count', 'next_retry_at', 'updated_at'])
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'Retry done: success={success} failed={failed} total={total}'))
