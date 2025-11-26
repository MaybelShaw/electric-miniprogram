from django.db import models


class HaierConfig(models.Model):
    """
    海尔API配置模型
    
    存储海尔API的认证信息和配置参数。
    """
    
    name = models.CharField(
        max_length=50,
        unique=True,
        default='haier',
        verbose_name='配置名称',
        help_text='配置标识，默认为haier'
    )
    
    # 使用JSONField存储配置，支持灵活的字段结构
    config = models.JSONField(
        verbose_name='配置信息',
        help_text='海尔API配置，包含client_id、client_secret等'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
        help_text='禁用后将不会使用此配置'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '海尔API配置'
        verbose_name_plural = '海尔API配置'
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"{self.name} ({'启用' if self.is_active else '禁用'})"


class HaierSyncLog(models.Model):
    """
    海尔API同步日志模型
    
    记录所有海尔API数据同步操作的详细信息，用于审计和故障排查。
    """
    
    SYNC_TYPE_CHOICES = [
        ('products', '商品同步'),
        ('prices', '价格同步'),
        ('stock', '库存同步'),
        ('order', '订单推送'),
        ('logistics', '物流查询'),
        ('manual', '手动操作'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('partial', '部分成功'),
    ]
    
    sync_type = models.CharField(
        max_length=20,
        choices=SYNC_TYPE_CHOICES,
        verbose_name='同步类型',
        db_index=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='同步状态',
        db_index=True
    )
    
    message = models.TextField(
        blank=True,
        verbose_name='同步消息',
        help_text='同步过程中的详细信息或错误信息'
    )
    
    # 同步统计信息
    total_count = models.IntegerField(
        default=0,
        verbose_name='总数',
        help_text='处理的总记录数'
    )
    
    success_count = models.IntegerField(
        default=0,
        verbose_name='成功数',
        help_text='成功处理的记录数'
    )
    
    failed_count = models.IntegerField(
        default=0,
        verbose_name='失败数',
        help_text='失败的记录数'
    )
    
    # 时间戳
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='开始时间'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_index=True
    )
    
    class Meta:
        verbose_name = '海尔同步日志'
        verbose_name_plural = '海尔同步日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['sync_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"海尔 - {self.get_sync_type_display()} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """获取同步耗时（秒）"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
