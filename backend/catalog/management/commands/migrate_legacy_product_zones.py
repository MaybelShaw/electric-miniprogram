from django.core.management.base import BaseCommand

from catalog.models import Product, SpecialZone, SpecialZoneProduct
from stores.models import Store


class Command(BaseCommand):
    help = "Migrate legacy fixed product zone flags into platform activities."

    LEGACY_ZONES = [
        ("show_in_gift_zone", "礼遇精选", "legacy-gift-zone"),
        ("show_in_designer_zone", "设计师严选", "legacy-designer-zone"),
        ("show_in_best_seller_zone", "爆品推荐", "legacy-best-seller-zone"),
    ]

    def handle(self, *args, **options):
        main_store = Store.objects.filter(is_main=True).first()
        if not main_store:
            self.stderr.write("Main store does not exist.")
            return

        for flag, title, slug in self.LEGACY_ZONES:
            zone, _ = SpecialZone.objects.get_or_create(
                store=main_store,
                slug=slug,
                defaults={
                    "title": title,
                    "kind": SpecialZone.KIND_PLATFORM_ACTIVITY,
                    "is_active": True,
                    "show_on_home": False,
                },
            )
            products = Product.objects.filter(**{flag: True})
            count = 0
            for product in products:
                SpecialZoneProduct.objects.update_or_create(
                    zone=zone,
                    product=product,
                    defaults={"is_active": True, "order": 0},
                )
                count += 1
            self.stdout.write(f"{title}: migrated {count} products.")
