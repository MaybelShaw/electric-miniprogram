from django.contrib import admin
from .models import User, Address, CompanyInfo


# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "openid", "role", "is_superuser")
    search_fields = ("openid", "username")
    list_filter = ("is_staff", "is_superuser", "is_active", "role")

    fields = ("username", "avatar_url", "openid", "role", "is_staff", "is_superuser", "is_active", "date_joined", "last_login")
    readonly_fields = ("openid", "date_joined", "last_login")


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ("company_name", "user", "business_license", "contact_person", "status", "created_at")
    search_fields = ("company_name", "business_license", "contact_person", "user__username")
    list_filter = ("status", "created_at")
    readonly_fields = ("created_at", "updated_at", "approved_at")
    
    fieldsets = (
        ("基本信息", {
            "fields": ("user", "company_name", "business_license", "legal_representative")
        }),
        ("联系信息", {
            "fields": ("contact_person", "contact_phone", "contact_email")
        }),
        ("地址信息", {
            "fields": ("province", "city", "district", "detail_address")
        }),
        ("业务信息", {
            "fields": ("business_scope", "status")
        }),
        ("时间信息", {
            "fields": ("created_at", "updated_at", "approved_at")
        }),
    )


admin.site.register(Address)