from django.contrib import admin
from .models import (
    CheckoutOrder,
    Order,
    OrderItem,
    SubOrder,
    SubOrderItem,
    Cart,
    CartItem,
    Discount,
    DiscountTarget,
    Invoice,
    ReturnRequest,
    Payment,
    Refund,
    OrderShippingAction,
    OrderStatusHistory,
    OrderShippingSync,
)

# Register your models here.

class DiscountTargetInline(admin.TabularInline):
    model = DiscountTarget
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "sku", "product_name", "quantity", "unit_price", "actual_amount", "created_at")
    readonly_fields = ("created_at",)


@admin.register(CheckoutOrder)
class CheckoutOrderAdmin(admin.ModelAdmin):
    list_display = ("checkout_number", "user", "status", "payment_status", "total_amount", "actual_amount", "created_at")
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("checkout_number", "payment_number", "user__username", "snapshot_phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "amount", "priority", "effective_time", "expiration_time")
    list_filter = ("priority",)
    search_fields = ("name",)
    inlines = [DiscountTargetInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "product", "quantity", "total_amount", "status", "created_at")
    list_filter = ("store", "status", "order_type", "created_at")
    search_fields = ("order_number", "user__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product_name", "sku", "quantity", "unit_price", "actual_amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("order__order_number", "product_name", "sku_code")


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = ("suborder_number", "checkout_order", "legacy_order", "store", "product", "status", "actual_amount", "created_at")
    list_filter = ("store", "status", "created_at")
    search_fields = ("suborder_number", "checkout_order__checkout_number", "legacy_order__order_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubOrderItem)
class SubOrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "suborder", "product_name", "sku", "quantity", "unit_price", "actual_amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("suborder__suborder_number", "product_name", "sku_code")


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


@admin.register(OrderShippingSync)
class OrderShippingSyncAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "status", "retry_count", "next_retry_at", "created_at", "updated_at")
    list_filter = ("status", "created_at", "next_retry_at")
    search_fields = ("order__order_number", "error")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OrderShippingAction)
class OrderShippingActionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "action",
        "status",
        "operator",
        "wechat_sync_required",
        "wechat_synced",
        "created_at",
    )
    list_filter = ("action", "status", "wechat_sync_required", "wechat_synced", "created_at")
    search_fields = ("order__order_number", "operator__username", "reason")
    list_select_related = ("order", "operator")
    readonly_fields = (
        "order",
        "action",
        "status",
        "shipping_snapshot",
        "operator",
        "reason",
        "wechat_sync_required",
        "wechat_synced",
        "wechat_response",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "user", "status", "reason", "tracking_number", "created_at")
    list_filter = ("status",)
    search_fields = ("order__order_number", "user__username", "tracking_number")
