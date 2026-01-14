from __future__ import annotations

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .media_cleanup import cleanup_media_image, cleanup_product_images, cleanup_media_by_url
from .models import MediaImage, HomeBanner, SpecialZoneCover, Case, CaseDetailBlock, Product, Category, Brand, ProductSKU


@receiver(post_delete, sender=MediaImage)
def delete_media_file(sender, instance: MediaImage, **kwargs):
    file_field = getattr(instance, 'file', None)
    if file_field:
        try:
            file_field.delete(save=False)
        except Exception:
            pass


@receiver(post_delete, sender=HomeBanner)
def cleanup_banner_image(sender, instance: HomeBanner, **kwargs):
    cleanup_media_image(instance.image if instance else None)


@receiver(post_delete, sender=SpecialZoneCover)
def cleanup_zone_cover_image(sender, instance: SpecialZoneCover, **kwargs):
    cleanup_media_image(instance.image if instance else None)


@receiver(post_delete, sender=Case)
def cleanup_case_cover_image(sender, instance: Case, **kwargs):
    cleanup_media_image(instance.cover_image if instance else None)


@receiver(post_delete, sender=CaseDetailBlock)
def cleanup_case_detail_image(sender, instance: CaseDetailBlock, **kwargs):
    cleanup_media_image(instance.image if instance else None)


@receiver(post_delete, sender=Product)
def cleanup_product_media(sender, instance: Product, **kwargs):
    if instance:
        cleanup_product_images(instance)


@receiver(post_delete, sender=Category)
def cleanup_category_logo(sender, instance: Category, **kwargs):
    if instance and instance.logo:
        cleanup_media_by_url(instance.logo)


@receiver(post_delete, sender=Brand)
def cleanup_brand_logo(sender, instance: Brand, **kwargs):
    if instance and instance.logo:
        cleanup_media_by_url(instance.logo)


@receiver(post_delete, sender=ProductSKU)
def cleanup_sku_image(sender, instance: ProductSKU, **kwargs):
    if instance and instance.image:
        cleanup_media_by_url(instance.image)
