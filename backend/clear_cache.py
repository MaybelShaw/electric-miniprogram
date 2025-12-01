import os
import django
import sys

sys.path.append('/Users/bobo/developer/electric-miniprogram/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.development')
django.setup()

from orders.analytics import OrderAnalytics

print("Invalidating analytics cache...")
OrderAnalytics.invalidate_cache()
print("Cache invalidated.")
