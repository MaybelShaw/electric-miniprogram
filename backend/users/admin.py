from django.contrib import admin
from .models import User,Address


# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "openid", "is_superuser")
    search_fields = ("openid", "username")
    list_filter = ("is_staff", "is_superuser", "is_active")

    fields = ("username", "avatar_url", "openid", "is_staff", "is_superuser", "is_active", "date_joined", "last_login")
    readonly_fields = ("openid", "date_joined", "last_login")

admin.site.register(Address)