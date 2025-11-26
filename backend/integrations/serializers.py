"""
海尔API序列化器
"""
from rest_framework import serializers
from .models import HaierConfig, HaierSyncLog


class HaierConfigSerializer(serializers.ModelSerializer):
    """海尔API配置序列化器"""
    
    class Meta:
        model = HaierConfig
        fields = ['id', 'name', 'config', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_config(self, value):
        """验证配置信息"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("配置必须是字典格式")
        
        # 检查必需的字段
        required_fields = ['client_id', 'client_secret', 'token_url', 'base_url']
        missing_fields = [f for f in required_fields if f not in value]
        
        if missing_fields:
            raise serializers.ValidationError(
                f"缺少必需字段: {', '.join(missing_fields)}"
            )
        
        return value


class HaierSyncLogSerializer(serializers.ModelSerializer):
    """海尔同步日志序列化器"""
    
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = HaierSyncLog
        fields = [
            'id',
            'sync_type',
            'sync_type_display',
            'status',
            'status_display',
            'message',
            'total_count',
            'success_count',
            'failed_count',
            'started_at',
            'completed_at',
            'created_at',
            'duration',
        ]
        read_only_fields = [
            'id',
            'started_at',
            'completed_at',
            'created_at',
        ]
    
    def get_duration(self, obj):
        """获取同步耗时"""
        return obj.duration
