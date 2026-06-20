from django.core.management.base import BaseCommand

from orders.profit_sharing import ProfitSharingService


class Command(BaseCommand):
    help = "Sync local profit sharing state and mark due frozen entries available."

    def handle(self, *args, **options):
        available_count = ProfitSharingService.mark_available()
        self.stdout.write(self.style.SUCCESS(f"marked available: {available_count}"))
