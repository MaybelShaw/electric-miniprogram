from django.contrib import admin

from .models import (
    Store,
    StoreCustomerGroup,
    StoreCustomerGroupMember,
    StoreCustomerGroupPrice,
    StoreMember,
    StorePaymentConfig,
    StoreSettlementRule,
)


class StoreMemberInline(admin.TabularInline):
    model = StoreMember
    extra = 0
    fields = ("user", "role", "status", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "store_type", "status", "is_main", "show_on_home", "allow_haier")
    search_fields = ("name", "code", "contact_phone", "address")
    list_filter = ("status", "store_type", "is_main", "show_on_home", "allow_haier")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StoreMemberInline]


@admin.register(StoreMember)
class StoreMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "store", "role", "status", "created_at")
    search_fields = ("user__username", "user__phone", "store__name", "store__code")
    list_filter = ("role", "status", "store")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StoreCustomerGroup)
class StoreCustomerGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "name", "status", "created_at")
    search_fields = ("store__name", "store__code", "name")
    list_filter = ("status", "store")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StoreCustomerGroupMember)
class StoreCustomerGroupMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "group", "user", "phone", "status", "created_at")
    search_fields = ("store__name", "group__name", "user__username", "user__phone", "phone")
    list_filter = ("status", "store", "group")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StoreCustomerGroupPrice)
class StoreCustomerGroupPriceAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "product", "sku", "price", "updated_at")
    search_fields = ("group__name", "product__name", "sku__name", "sku__sku_code")
    list_filter = ("group__store", "group")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StorePaymentConfig)
class StorePaymentConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "wechat_mch_id", "wechat_sub_mch_id", "is_active", "updated_at")
    search_fields = ("store__name", "wechat_mch_id", "wechat_sub_mch_id")
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(StoreSettlementRule)
class StoreSettlementRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "commission_rate", "settlement_cycle_days", "is_active", "updated_at")
    search_fields = ("store__name", "store__code")
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "updated_at")
