"""
Management command to reconcile pending/processing payments by querying provider status.

Since we are currently using a mock payment provider, this command simulates a
simple reconciliation strategy:
1. For payments still in init/processing and not expired, mark them as succeeded
   if a mock "auto_success" flag is set on the order metadata (used for demos).
2. Expire payments that have passed expires_at.
3. Leave space to integrate real provider (e.g., WeChat Pay) query APIs.

Usage:
    python manage.py reconcile_payments
    python manage.py reconcile_payments --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from orders.models import Payment
from orders.payment_service import PaymentService
from orders.state_machine import OrderStateMachine


class Command(BaseCommand):
    help = 'Reconcile pending/processing payments and fix missed callbacks.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show actions without applying changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        qs = Payment.objects.filter(status__in=['init', 'processing']).select_related('order')
        total = qs.count()
        succeeded = 0
        expired = 0
        self.stdout.write(self.style.SUCCESS(f'Found {total} payments to reconcile'))

        for pay in qs:
            # Expire overdue payments
            if pay.expires_at and pay.expires_at < now:
                if dry_run:
                    self.stdout.write(f'[DRY RUN] Would expire payment #{pay.id}')
                else:
                    with transaction.atomic():
                        pay.status = 'expired'
                        pay.logs.append({'t': now.isoformat(), 'event': 'expired_by_reconcile'})
                        pay.save(update_fields=['status', 'logs', 'updated_at'])
                        try:
                            if pay.order.status == 'pending':
                                OrderStateMachine.transition(pay.order, 'cancelled', operator=None, note='Reconcile expired')
                        except Exception:
                            pass
                    expired += 1
                continue

            # Simulated auto success hook for demos; replace with real provider query
            auto_success = getattr(pay.order, 'auto_success', False) or pay.order.metadata.get('auto_success') if hasattr(pay.order, 'metadata') else False
            if auto_success:
                if dry_run:
                    self.stdout.write(f'[DRY RUN] Would mark payment #{pay.id} as succeeded')
                else:
                    with transaction.atomic():
                        PaymentService.process_payment_success(pay.id, transaction_id='reconcile-mock')
                    succeeded += 1

        self.stdout.write(self.style.SUCCESS(f'Succeeded: {succeeded}, Expired: {expired}'))

