from django.contrib import admin

from .models import (
    Brand,
    Case,
    CaseDetailBlock,
    Category,
    HomeBanner,
    HomeStoreCard,
    HomeStoreCardCategory,
    HomeStoreCardProduct,
    InventoryLog,
    MediaImage,
    Product,
    ProductSKU,
    SearchLog,
    SpecialZone,
    SpecialZoneCover,
    SpecialZoneProduct,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "name", "level", "parent", "order", "created_at")
    list_filter = ("store", "level", "created_at")
    search_fields = ("name", "store__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "name", "is_active", "order", "created_at")
    list_filter = ("store", "is_active", "created_at")
    search_fields = ("name", "store__name")
    readonly_fields = ("created_at", "updated_at")


class ProductSKUInline(admin.TabularInline):
    model = ProductSKU
    extra = 0
    fields = ("name", "sku_code", "specs", "price", "stock", "image", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "name", "brand", "category", "price", "stock", "is_active", "source", "updated_at")
    list_filter = ("store", "brand", "category", "source", "is_active", "created_at")
    search_fields = ("name", "product_code", "product_model", "brand__name", "category__name", "store__name")
    readonly_fields = ("created_at", "updated_at", "last_sync_at", "view_count", "sales_count")
    inlines = [ProductSKUInline]


@admin.register(ProductSKU)
class ProductSKUAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "name", "sku_code", "price", "stock", "is_active", "updated_at")
    list_filter = ("product__store", "is_active", "created_at")
    search_fields = ("name", "sku_code", "product__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MediaImage)
class MediaImageAdmin(admin.ModelAdmin):
    list_display = ("id", "original_name", "content_type", "size", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("original_name",)


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("id", "keyword", "user", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("keyword", "user__username")
    list_filter = ("created_at",)


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "sku", "change_type", "quantity", "reason", "created_by", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("product__name", "sku__name", "sku__sku_code", "reason")
    list_filter = ("product__store", "change_type", "created_at")


class SpecialZoneProductInline(admin.TabularInline):
    model = SpecialZoneProduct
    extra = 0
    fields = ("product", "is_active", "order", "created_at")
    readonly_fields = ("created_at",)


@admin.register(SpecialZone)
class SpecialZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "title", "kind", "is_active", "show_on_home", "home_order", "updated_at")
    list_filter = ("store", "kind", "is_active", "show_on_home")
    search_fields = ("title", "slug", "store__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SpecialZoneProductInline]


@admin.register(SpecialZoneProduct)
class SpecialZoneProductAdmin(admin.ModelAdmin):
    list_display = ("id", "zone", "product", "is_active", "order", "created_at")
    list_filter = ("zone__store", "zone", "is_active")
    search_fields = ("zone__title", "product__name")
    readonly_fields = ("created_at",)


class HomeStoreCardProductInline(admin.TabularInline):
    model = HomeStoreCardProduct
    extra = 0
    fields = ("product", "role", "order")


class HomeStoreCardCategoryInline(admin.TabularInline):
    model = HomeStoreCardCategory
    extra = 0
    fields = ("category", "order")


@admin.register(HomeStoreCard)
class HomeStoreCardAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "title", "subtitle", "order", "is_active", "updated_at")
    list_filter = ("store", "is_active")
    search_fields = ("title", "subtitle", "store__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [HomeStoreCardProductInline, HomeStoreCardCategoryInline]


@admin.register(HomeStoreCardProduct)
class HomeStoreCardProductAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "product", "role", "order")
    list_filter = ("role", "card__store")
    search_fields = ("card__title", "product__name")


@admin.register(HomeStoreCardCategory)
class HomeStoreCardCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "category", "order")
    list_filter = ("card__store",)
    search_fields = ("card__title", "category__name")


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "title", "position", "special_zone", "product", "is_active", "order", "updated_at")
    list_filter = ("store", "position", "is_active", "special_zone")
    search_fields = ("title", "store__name", "product__name", "special_zone__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SpecialZoneCover)
class SpecialZoneCoverAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "type", "is_active", "updated_at")
    list_filter = ("store", "type", "is_active")
    ordering = ("type", "-id")
    readonly_fields = ("created_at", "updated_at")


class CaseDetailBlockInline(admin.TabularInline):
    model = CaseDetailBlock
    extra = 0
    fields = ("order", "block_type", "text", "image", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("order", "id")


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "order", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("order", "-id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CaseDetailBlockInline]
