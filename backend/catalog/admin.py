from django.contrib import admin
from .models import Category, Brand, Product, MediaImage, SearchLog, InventoryLog, Case, CaseDetailBlock

# Register your models here.
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product)

@admin.register(MediaImage)
class MediaImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_name', 'content_type', 'size', 'created_at')
    readonly_fields = ('created_at',)
    search_fields = ('original_name',)

@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'keyword', 'user', 'created_at')
    readonly_fields = ('created_at',)
    search_fields = ('keyword',)
    list_filter = ('created_at',)

@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'change_type', 'quantity', 'reason', 'created_by', 'created_at')
    readonly_fields = ('created_at',)
    search_fields = ('product__name', 'reason')
    list_filter = ('change_type', 'created_at')


class CaseDetailBlockInline(admin.TabularInline):
    model = CaseDetailBlock
    extra = 0
    fields = ('order', 'block_type', 'text', 'image', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('order', 'id')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'order', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title',)
    ordering = ('order', '-id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CaseDetailBlockInline]
