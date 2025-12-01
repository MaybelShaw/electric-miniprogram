from django.core.management.base import BaseCommand
from orders.models import Order
from common.address_parser import address_parser
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix missing region fields in Order snapshots by parsing snapshot_address'

    def handle(self, *args, **options):
        self.stdout.write('Starting to fix order regions...')
        
        # Find orders with empty snapshot_province OR empty snapshot_city OR empty snapshot_district
        # but primarily we want to fix missing province/city as that's the main grouping
        orders = Order.objects.filter(snapshot_province='')
        # Also check for cases where we might have missed district
        # orders = orders | Order.objects.filter(snapshot_district='') 
        # For now let's just focus on empty province to avoid overwriting valid empty districts (if any)
        # But since I want to re-process the one I just "fixed" partially, I need to expand the filter
        # or just iterate all orders and check if they need fixing.
        
        # Better: filter for empty province OR (empty district AND snapshot_address is not empty)
        from django.db.models import Q
        orders = Order.objects.filter(Q(snapshot_province='') | Q(snapshot_district=''))
        
        count = orders.count()
        
        self.stdout.write(f'Found {count} orders with missing region info.')
        
        fixed_count = 0
        failed_count = 0
        
        for order in orders:
            address_text = order.snapshot_address
            if not address_text:
                # If address is empty, we can't do anything
                continue
            
            # Current values
            curr_p = order.snapshot_province
            curr_c = order.snapshot_city
            curr_d = order.snapshot_district
            
            # Strategy 1: Use AddressParser (JioNLP)
            parsed = address_parser.parse_address(address_text)
            
            province = parsed.get('province')
            city = parsed.get('city')
            district = parsed.get('district')
            town = parsed.get('town')
            
            # Strategy 2: Fallback to space splitting
            # If Jionlp missed something, try to fill it from parts
            parts = address_text.split()
            if len(parts) >= 3:
                p_cand = parts[0]
                c_cand = parts[1]
                d_cand = parts[2]
                
                if not province and p_cand: province = p_cand
                if not city and c_cand: city = c_cand
                # If jionlp didn't find district, and we have a candidate that looks reasonable (not just "北京")
                # Actually, if the user entered "北京", maybe we should just store it so they see it
                if not district and d_cand: district = d_cand
            
            # Clean up
            province = province or ''
            city = city or ''
            district = district or ''
            town = town or ''
            
            # Check if we have better data than current
            changed = False
            if province and province != curr_p:
                order.snapshot_province = province
                changed = True
            if city and city != curr_c:
                order.snapshot_city = city
                changed = True
            if district and district != curr_d:
                order.snapshot_district = district
                changed = True
            if town and town != order.snapshot_town:
                order.snapshot_town = town
                changed = True
                
            if changed:
                order.save(update_fields=['snapshot_province', 'snapshot_city', 'snapshot_district', 'snapshot_town'])
                self.stdout.write(self.style.SUCCESS(f'Order {order.order_number}: Updated -> {province} {city} {district}'))
                fixed_count += 1
            else:
                 # debug info
                 # self.stdout.write(f'Order {order.order_number}: No change needed or failed to parse better.')
                 pass
                
        self.stdout.write(self.style.SUCCESS(f'Finished. Fixed: {fixed_count}, Failed: {failed_count}'))
