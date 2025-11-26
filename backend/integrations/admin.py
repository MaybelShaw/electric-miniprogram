from django.contrib import admin
from .models import HaierConfig, HaierSyncLog


@admin.register(HaierConfig)
class HaierConfigAdmin(admin.ModelAdmin):
    """海尔API配置管理"""
    list_display = ['name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(HaierSyncLog)
class HaierSyncLogAdmin(admin.ModelAdmin):
    """海尔同步日志管理"""
    list_display = ['sync_type', 'status', 'total_count', 'success_count', 'failed_count', 'created_at']
    list_filter = ['sync_type', 'status', 'created_at']
    search_fields = ['message']
    readonly_fields = ['sync_type', 'status', 'message', 'total_count', 'success_count', 
                      'failed_count', 'started_at', 'completed_at', 'created_at']
    
    def has_add_permission(self, request):
        """禁止手动添加日志"""
        return False
