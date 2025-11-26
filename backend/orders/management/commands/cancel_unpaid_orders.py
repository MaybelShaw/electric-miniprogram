"""
Management command to automatically cancel unpaid orders that have exceeded the payment timeout.

This command:
1. Finds all pending orders that have exceeded the payment timeout
2. Cancels them using the OrderStateMachine
3. Releases the locked inventory
4. Logs the operation

Usage:
    python manage.py cancel_unpaid_orders
    python manage.py cancel_unpaid_orders --timeout-minutes 30
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from orders.models import Order, Payment
from orders.state_machine import OrderStateMachine
from orders.services import InventoryService


class Command(BaseCommand):
    help = 'Automatically cancel unpaid orders that have exceeded the payment timeout'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout-minutes',
            type=int,
            default=30,
            help='Payment timeout in minutes (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cancelled without actually cancelling',
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout_minutes']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting automatic order cancellation (timeout: {timeout_minutes} minutes, dry_run: {dry_run})'
            )
        )

        # Calculate the cutoff time
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)

        # Find all pending orders created before the cutoff time
        # These orders have not been paid within the timeout period
        unpaid_orders = Order.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        ).select_related('user', 'product')

        cancelled_count = 0
        error_count = 0

        for order in unpaid_orders:
            try:
                if dry_run:
                    self.stdout.write(
                        f'[DRY RUN] Would cancel order #{order.order_number} '
                        f'(created: {order.created_at}, user: {order.user.username})'
                    )
                else:
                    self._cancel_order(order)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Cancelled order #{order.order_number} '
                            f'(created: {order.created_at}, user: {order.user.username})'
                        )
                    )
                cancelled_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to cancel order #{order.order_number}: {str(e)}'
                    )
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Summary ===\n'
                f'Total orders processed: {unpaid_orders.count()}\n'
                f'Successfully cancelled: {cancelled_count}\n'
                f'Errors: {error_count}'
            )
        )

    @transaction.atomic
    def _cancel_order(self, order):
        """Cancel a single order and release its inventory
        
        Args:
            order: Order object to cancel
            
        Raises:
            ValueError: If order cannot be cancelled
        """
        # Use the state machine to transition the order to cancelled status
        # This will automatically trigger inventory release via the post-transition handler
        OrderStateMachine.transition(
            order=order,
            new_status='cancelled',
            operator=None,
            note='Automatically cancelled due to payment timeout'
        )
