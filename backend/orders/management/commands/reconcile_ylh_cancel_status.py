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
    python manage.py reconcile_ylh_cancel_status --no-fallback
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
        parser.add_argument(
            '--no-fallback',
            action='store_true',
            help='Do not infer previous status when history is missing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        order_id = options['order_id']
        order_number = options['order_number']
        include_refunds = options['include_refunds']
        no_fallback = options['no_fallback']

        qs = Order.objects.filter(
            haier_status='cancel_failed',
            status='cancelled',
        ).exclude(haier_so_id__isnull=True).exclude(haier_so_id='')

        if order_id:
            qs = qs.filter(id=order_id)
        if order_number:
            qs = qs.filter(order_number=order_number)
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
                refund_statuses = list(order.refunds.values_list('status', flat=True))
                if refund_statuses and not include_refunds:
                    if any(status in {'pending', 'processing', 'succeeded'} for status in refund_statuses):
                        skipped += 1
                        self.stdout.write(
                            f'[SKIP] order#{order.order_number} refunds exist: {",".join(refund_statuses)}'
                        )
                        continue
                    # All refunds failed - allow rollback but log
                    self.stdout.write(
                        f'[INFO] order#{order.order_number} only failed refunds found, proceeding'
                    )
                previous_status = self._resolve_previous_status(order, allow_fallback=not no_fallback)

                if not previous_status or previous_status == order.status:
                    skipped += 1
                    reason = 'no previous status to rollback'
                    if no_fallback:
                        reason = 'no previous status (fallback disabled)'
                    self.stdout.write(f'[SKIP] order#{order.order_number} {reason}')
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
        order.save(update_fields=['status', 'updated_at'])

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

    @staticmethod
    def _resolve_previous_status(order: Order, allow_fallback: bool = True):
        """Try to resolve the status before the local cancelled change."""
        history = order.status_history.all().order_by('-created_at')
        prev = history.filter(to_status='cancelled').values_list('from_status', flat=True).first()
        if prev:
            return prev
        # If no cancelled history exists, fallback to last known status in history
        if history.exists():
            last_status = history.values_list('to_status', flat=True).first()
            if last_status and last_status != 'cancelled':
                return last_status
        if not allow_fallback:
            return None
        # Heuristic fallback based on evidence
        has_shipping = bool(order.logistics_no or order.delivery_record_code or order.sn_code)
        if has_shipping:
            return 'shipped'
        if order.payments.filter(status='succeeded').exists():
            return 'paid'
        return 'pending'
