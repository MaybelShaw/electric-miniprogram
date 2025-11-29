from django.contrib import admin
from .models import Order, Cart, CartItem, Discount, DiscountTarget, Invoice

# Register your models here.

class DiscountTargetInline(admin.TabularInline):
    model = DiscountTarget
    extra = 0


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "amount", "priority", "effective_time", "expiration_time")
    list_filter = ("priority",)
    search_fields = ("name",)
    inlines = [DiscountTargetInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "product", "quantity", "total_amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("order_number", "user__username")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
    search_fields = ("user__username",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity")
    search_fields = ("cart__user__username", "product__name")


@admin.register(DiscountTarget)
class DiscountTargetAdmin(admin.ModelAdmin):
    list_display = ("id", "discount", "user", "product")
    # 默认使用下拉选择（移除 raw_id_fields）


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "user", "title", "amount", "status", "invoice_number", "requested_at", "issued_at")
    list_filter = ("status", "invoice_type")
    search_fields = ("order__order_number", "user__username", "invoice_number", "title")
