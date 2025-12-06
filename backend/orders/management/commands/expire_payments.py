"""
Management command to expire overdue payments and cancel their orders if still pending.

Usage:
    python manage.py expire_payments
    python manage.py expire_payments --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from orders.models import Payment
from orders.state_machine import OrderStateMachine


class Command(BaseCommand):
    help = 'Mark overdue payments as expired and cancel pending orders to release stock'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be expired without modifying data',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        qs = Payment.objects.filter(status__in=['init', 'processing'], expires_at__lt=now).select_related('order')

        total = qs.count()
        expired = 0
        self.stdout.write(self.style.SUCCESS(f'Found {total} overdue payments'))

        for pay in qs:
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would expire payment #{pay.id} (order {pay.order_id})')
                continue
            with transaction.atomic():
                pay.status = 'expired'
                pay.logs.append({
                    't': now.isoformat(),
                    'event': 'expired_by_task',
                    'detail': 'Auto expired by management command'
                })
                pay.save(update_fields=['status', 'logs', 'updated_at'])
                try:
                    if pay.order.status == 'pending':
                        OrderStateMachine.transition(
                            pay.order,
                            'cancelled',
                            operator=None,
                            note='Payment expired auto cancel'
                        )
                except Exception:
                    # Fail silently to avoid breaking the loop; logs already contain expiry
                    pass
                expired += 1

        self.stdout.write(self.style.SUCCESS(f'Expired {expired} payments'))

