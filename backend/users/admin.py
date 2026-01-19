from django.contrib import admin
from .models import User, Address, CompanyInfo, CreditAccount, AccountStatement, AccountTransaction


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
            "fields": ("business_scope", "reject_reason", "status")
        }),
        ("时间信息", {
            "fields": ("created_at", "updated_at", "approved_at")
        }),
    )


@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "credit_limit", "outstanding_debt", "available_credit_display", "payment_term_days", "is_active", "created_at")
    search_fields = ("user__username", "user__company_info__company_name")
    list_filter = ("is_active", "created_at")
    readonly_fields = ("outstanding_debt", "created_at", "updated_at", "available_credit_display")
    
    fieldsets = (
        ("账户信息", {
            "fields": ("user", "is_active")
        }),
        ("信用设置", {
            "fields": ("credit_limit", "payment_term_days")
        }),
        ("当前状态", {
            "fields": ("outstanding_debt", "available_credit_display")
        }),
        ("时间信息", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    def available_credit_display(self, obj):
        return obj.available_credit
    available_credit_display.short_description = "可用额度"


@admin.register(AccountStatement)
class AccountStatementAdmin(admin.ModelAdmin):
    list_display = ("id", "credit_account", "period_start", "period_end", "period_end_balance", "overdue_amount", "status", "created_at")
    search_fields = ("credit_account__user__username", "credit_account__user__company_info__company_name")
    list_filter = ("status", "period_start", "period_end")
    readonly_fields = ("created_at", "updated_at", "confirmed_at", "settled_at")
    
    fieldsets = (
        ("基本信息", {
            "fields": ("credit_account", "period_start", "period_end", "status")
        }),
        ("财务汇总", {
            "fields": ("previous_balance", "current_purchases", "current_payments", "current_refunds", "period_end_balance")
        }),
        ("应付跟踪", {
            "fields": ("due_within_term", "paid_within_term", "overdue_amount")
        }),
        ("时间信息", {
            "fields": ("created_at", "updated_at", "confirmed_at", "settled_at")
        }),
    )


@admin.register(AccountTransaction)
class AccountTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "credit_account", "transaction_type", "amount", "balance_after", "payment_status", "due_date", "created_at")
    search_fields = ("credit_account__user__username", "description", "order_id")
    list_filter = ("transaction_type", "payment_status", "created_at")
    readonly_fields = ("balance_after", "created_at")
    
    fieldsets = (
        ("基本信息", {
            "fields": ("credit_account", "statement", "transaction_type", "amount", "balance_after")
        }),
        ("关联信息", {
            "fields": ("order_id", "description")
        }),
        ("付款信息", {
            "fields": ("due_date", "paid_date", "payment_status")
        }),
        ("时间信息", {
            "fields": ("created_at",)
        }),
    )


admin.site.register(Address)
