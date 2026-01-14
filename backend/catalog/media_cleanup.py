from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from django.conf import settings
from django.db.models.deletion import ProtectedError

from .models import MediaImage, Product


def normalize_media_path(url: str) -> str:
    if not url:
        return ''
    if url.startswith(settings.MEDIA_URL):
        return url
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return parsed.path or ''
    if url.startswith('/'):
        return url
    media_prefix = settings.MEDIA_URL.rstrip('/')
    return f"{media_prefix}/{url.lstrip('/')}"


def is_local_media_url(url: str) -> bool:
    if not url:
        return False
    normalized = normalize_media_path(url)
    media_prefix = settings.MEDIA_URL.rstrip('/') + '/'
    return normalized.startswith(media_prefix)


def media_file_name_from_url(url: str) -> str:
    path = normalize_media_path(url)
    if not path:
        return ''
    media_prefix = settings.MEDIA_URL.rstrip('/')
    if path.startswith(media_prefix):
        path = path[len(media_prefix):]
    return path.lstrip('/')


def collect_media_paths(media: MediaImage) -> set[str]:
    paths = set()
    file_url = getattr(media.file, 'url', '')
    file_name = getattr(media.file, 'name', '')
    for value in (file_url, file_name):
        normalized = normalize_media_path(value)
        if normalized:
            paths.add(normalized)
    return paths


def iter_product_image_urls(product: Product) -> Iterable[str]:
    for url in (product.main_images or []):
        if url:
            yield str(url)
    for url in (product.detail_images or []):
        if url:
            yield str(url)
    if product.product_image_url:
        yield str(product.product_image_url)
    for url in (product.product_page_urls or []):
        if url:
            yield str(url)


def is_media_referenced(media: MediaImage) -> bool:
    from .models import HomeBanner, SpecialZoneCover, Case, CaseDetailBlock, Category, Brand, ProductSKU
    from orders.models import OrderItem

    media_id = media.id
    if HomeBanner.objects.filter(image_id=media_id).exists():
        return True
    if SpecialZoneCover.objects.filter(image_id=media_id).exists():
        return True
    if Case.objects.filter(cover_image_id=media_id).exists():
        return True
    if CaseDetailBlock.objects.filter(image_id=media_id).exists():
        return True

    media_paths = collect_media_paths(media)
    if not media_paths:
        return False

    for logo in Category.objects.exclude(logo='').values_list('logo', flat=True):
        if normalize_media_path(logo) in media_paths:
            return True
    for logo in Brand.objects.exclude(logo='').values_list('logo', flat=True):
        if normalize_media_path(logo) in media_paths:
            return True
    for sku_image in ProductSKU.objects.exclude(image='').values_list('image', flat=True):
        if normalize_media_path(sku_image) in media_paths:
            return True
    for snapshot in OrderItem.objects.exclude(snapshot_image='').values_list('snapshot_image', flat=True):
        if normalize_media_path(snapshot) in media_paths:
            return True

    for product in Product.objects.only('main_images', 'detail_images', 'product_image_url', 'product_page_urls'):
        for url in iter_product_image_urls(product):
            if normalize_media_path(url) in media_paths:
                return True
    return False


def cleanup_media_image(media: MediaImage | None) -> None:
    if not media:
        return
    if is_media_referenced(media):
        return
    try:
        media.delete()
    except ProtectedError:
        return


def cleanup_media_by_url(url: str) -> None:
    if not is_local_media_url(url):
        return
    file_name = media_file_name_from_url(url)
    if not file_name:
        return
    media = MediaImage.objects.filter(file=file_name).first()
    if not media:
        return
    cleanup_media_image(media)


def cleanup_product_images(product: Product) -> None:
    if product.source == Product.SOURCE_HAIER:
        return
    for url in iter_product_image_urls(product):
        cleanup_media_by_url(url)
