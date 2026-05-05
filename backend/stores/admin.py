from django.contrib import admin

from .models import Store, StoreMember, StorePaymentConfig, StoreSettlementRule


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "status", "is_main", "allow_haier")
    search_fields = ("name", "code")
    list_filter = ("status", "is_main", "allow_haier")


@admin.register(StoreMember)
class StoreMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "store", "role", "status")
    search_fields = ("user__username", "store__name", "store__code")
    list_filter = ("role", "status")


admin.site.register(StorePaymentConfig)
admin.site.register(StoreSettlementRule)
