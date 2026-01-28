"""
Reconcile orders that were locally cancelled but YLH cancel callback failed.

This command attempts to rollback order.status from "cancelled" to the previous
status recorded in OrderStatusHistory, when haier_status is "cancel_failed".

Usage:
    python manage.py reconcile_ylh_cancel_status
    python manage.py reconcile_ylh_cancel_status --dry-run
    python manage.py reconcile_ylh_cancel_status --order-id 123
    python manage.py reconcile_ylh_cancel_status --order-number SO.20250101.000001
    python manage.py reconcile_ylh_cancel_status --limit 50
    python manage.py reconcile_ylh_cancel_status --include-refunds
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from orders.models import Order, OrderStatusHistory


class Command(BaseCommand):
    help = 'Reconcile YLH cancel-failed orders that were locally cancelled'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be changed',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of orders to process',
        )
        parser.add_argument(
            '--order-id',
            type=int,
            default=None,
            help='Only process a specific order id',
        )
        parser.add_argument(
            '--order-number',
            type=str,
            default=None,
            help='Only process a specific order number',
        )
        parser.add_argument(
            '--include-refunds',
            action='store_true',
            help='Allow rollback even if refunds exist (NOT recommended)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        order_id = options['order_id']
        order_number = options['order_number']
        include_refunds = options['include_refunds']

        qs = Order.objects.filter(
            haier_status='cancel_failed',
            status='cancelled',
        ).exclude(haier_so_id='')

        if order_id:
            qs = qs.filter(id=order_id)
        if order_number:
            qs = qs.filter(order_number=order_number)
        if not include_refunds:
            qs = qs.filter(refunds__isnull=True)

        if limit:
            qs = qs.order_by('id')[:limit]

        total = qs.count()
        self.stdout.write(self.style.SUCCESS(
            f'Start reconcile_ylh_cancel_status (total={total}, dry_run={dry_run})'
        ))

        fixed = 0
        skipped = 0
        errors = 0

        for order in qs:
            try:
                previous_status = order.status_history.filter(
                    to_status='cancelled'
                ).order_by('-created_at').values_list('from_status', flat=True).first()

                if not previous_status or previous_status == order.status:
                    skipped += 1
                    self.stdout.write(
                        f'[SKIP] order#{order.order_number} no previous status to rollback'
                    )
                    continue

                msg = (
                    f'order#{order.order_number} {order.status} -> {previous_status} '
                    f'(haier_status={order.haier_status})'
                )
                if dry_run:
                    fixed += 1
                    self.stdout.write(f'[DRY RUN] {msg}')
                    continue

                self._rollback_order(order, previous_status)
                fixed += 1
                self.stdout.write(self.style.SUCCESS(f'[OK] {msg}'))
            except Exception as exc:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f'[ERROR] order#{order.order_number} {str(exc)}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Summary ===\n'
            f'Total matched: {total}\n'
            f'Rolled back: {fixed}\n'
            f'Skipped: {skipped}\n'
            f'Errors: {errors}'
        ))

    @transaction.atomic
    def _rollback_order(self, order: Order, previous_status: str):
        old_status = order.status
        order.status = previous_status
        order.updated_at = timezone.now()
        note = f'易理货取消失败回退: {old_status} -> {previous_status}'
        if note not in (order.note or ''):
            order.note = f"{order.note}\n{note}".strip()
        order.save(update_fields=['status', 'note', 'updated_at'])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=previous_status,
            operator=None,
            note='易理货取消失败回退'
        )

        try:
            from orders.analytics import OrderAnalytics
            OrderAnalytics.on_order_status_changed(order.id)
        except Exception:
            pass
