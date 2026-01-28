from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, F


class Command(BaseCommand):
    help = "Recalculate Product.sales_count from orders/items (paid/shipped/completed only)."

    def handle(self, *args, **options):
        from catalog.models import Product
        from orders.models import Order, OrderItem

        sales_statuses = ['paid', 'shipped', 'completed']

        self.stdout.write("Recalculating sales_count (full rebuild)...")

        with transaction.atomic():
            # 1) Reset all counts
            Product.objects.update(sales_count=0)

            # 2) Aggregate from order items
            item_totals = (
                OrderItem.objects.filter(order__status__in=sales_statuses)
                .values('product_id')
                .annotate(total=Sum('quantity'))
            )
            for row in item_totals:
                if not row.get('product_id') or row.get('total') is None:
                    continue
                Product.objects.filter(id=row['product_id']).update(sales_count=row['total'])

            # 3) Legacy orders without items (fallback)
            legacy_totals = (
                Order.objects.filter(status__in=sales_statuses, items__isnull=True, product_id__isnull=False)
                .values('product_id')
                .annotate(total=Sum('quantity'))
            )
            for row in legacy_totals:
                if not row.get('product_id') or row.get('total') is None:
                    continue
                Product.objects.filter(id=row['product_id']).update(sales_count=F('sales_count') + row['total'])

        self.stdout.write(self.style.SUCCESS("Recalculate sales_count completed."))
