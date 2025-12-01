import os
import django
import sys

# Set up Django environment
sys.path.append('/Users/bobo/developer/electric-miniprogram/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.development')
django.setup()

from orders.models import Order

print("Checking orders for snapshot address fields...")
orders = Order.objects.all()[:10]
for order in orders:
    print(f"Order {order.order_number}: Province='{order.snapshot_province}', City='{order.snapshot_city}', District='{order.snapshot_district}', Town='{order.snapshot_town}'")
    print(f"Snapshot Address: {order.snapshot_address}")
    print("-" * 20)
