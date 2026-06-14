from django.core.management.base import BaseCommand

from orders.models import WechatProfitSharingOrder
from orders.profit_sharing import ProfitSharingService


class Command(BaseCommand):
    help = "Sync local profit sharing state and mark due frozen entries available."

    def add_arguments(self, parser):
        parser.add_argument("--mark-local-processing-success", action="store_true")

    def handle(self, *args, **options):
        available_count = ProfitSharingService.mark_available()
        self.stdout.write(self.style.SUCCESS(f"marked available: {available_count}"))

        if options["mark_local_processing_success"]:
            count = 0
            for share_order in WechatProfitSharingOrder.objects.filter(status="processing"):
                response_state = str((share_order.wechat_response or {}).get("state") or "").upper()
                if response_state in {"FINISHED", "SUCCESS"}:
                    ProfitSharingService.mark_share_succeeded(share_order)
                    count += 1
            self.stdout.write(self.style.SUCCESS(f"marked shared: {count}"))
