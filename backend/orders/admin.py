from django.contrib import admin
from .models import (
    Order,
    Cart,
    CartItem,
    Discount,
    DiscountTarget,
    Invoice,
    ReturnRequest,
    Payment,
    Refund,
    OrderStatusHistory,
)

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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "amount", "method", "status", "created_at", "expires_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("id", "order__order_number", "order__user__username")
    list_select_related = ("order", "order__user")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "payment", "amount", "status", "reason", "operator", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "order__order_number", "payment__id", "transaction_id", "order__user__username")
    list_select_related = ("order", "payment", "operator", "order__user")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "from_status", "to_status", "operator", "created_at")
    list_filter = ("from_status", "to_status", "created_at")
    search_fields = ("order__order_number", "operator__username", "note")
    list_select_related = ("order", "operator", "order__user")


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "user", "status", "reason", "tracking_number", "created_at")
    list_filter = ("status",)
    search_fields = ("order__order_number", "user__username", "tracking_number")
