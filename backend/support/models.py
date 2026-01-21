from django.db import models
from django.conf import settings
from orders.models import Order
from catalog.models import Product


class SupportConversation(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_contacted_at = models.DateTimeField(null=True, blank=True)
    last_user_message_at = models.DateTimeField(null=True, blank=True)
    last_support_message_at = models.DateTimeField(null=True, blank=True)
    last_auto_reply_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        indexes = [
            models.Index(fields=['user'], name='support_conv_user_idx'),
            models.Index(fields=['updated_at'], name='support_conv_updated_idx'),
        ]


class SupportReplyTemplate(models.Model):
    TYPE_AUTO = 'auto'
    TYPE_QUICK = 'quick'
    TYPE_CHOICES = [
        (TYPE_AUTO, '自动回复'),
        (TYPE_QUICK, '快捷回复'),
    ]

    CONTENT_TEXT = 'text'
    CONTENT_CARD = 'card'
    CONTENT_QUICK = 'quick_buttons'
    CONTENT_CHOICES = [
        (CONTENT_TEXT, '纯文本'),
        (CONTENT_CARD, '图文卡片'),
        (CONTENT_QUICK, '快捷问题按钮'),
    ]

    TRIGGER_FIRST = 'first_contact'
    TRIGGER_IDLE = 'idle_contact'
    TRIGGER_CHOICES = [
        (TRIGGER_FIRST, '首次联系'),
        (TRIGGER_IDLE, '长时间未联系'),
    ]

    id = models.BigAutoField(primary_key=True)
    template_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_QUICK)
    title = models.CharField(max_length=120)
    content = models.TextField()
    content_type = models.CharField(max_length=20, choices=CONTENT_CHOICES, default=CONTENT_TEXT)
    content_payload = models.JSONField(default=dict, blank=True)
    group_name = models.CharField(max_length=120, blank=True, default='')
    is_pinned = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    trigger_event = models.CharField(max_length=20, choices=TRIGGER_CHOICES, null=True, blank=True)
    idle_minutes = models.PositiveIntegerField(null=True, blank=True)
    daily_limit = models.PositiveIntegerField(default=1)
    user_cooldown_days = models.PositiveIntegerField(default=1)
    apply_channels = models.JSONField(default=list, blank=True)
    apply_user_tags = models.JSONField(default=list, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['template_type', 'enabled'], name='support_tpl_type_idx'),
            models.Index(fields=['trigger_event'], name='support_tpl_trigger_idx'),
        ]


class SupportMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(SupportConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_messages')
    role = models.CharField(max_length=20, default='', db_index=True)
    content = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, default=SupportReplyTemplate.CONTENT_TEXT)
    content_payload = models.JSONField(default=dict, blank=True)
    attachment = models.FileField(upload_to='support/attachments/%Y/%m/%d/', null=True, blank=True)
    attachment_type = models.CharField(max_length=10, choices=[('image', 'image'), ('video', 'video')], null=True, blank=True, db_index=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_messages')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_messages')
    template = models.ForeignKey(SupportReplyTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='support_msg_conv_created_idx'),
            models.Index(fields=['attachment_type'], name='support_sup_attachm_54bc2a_idx'),
            models.Index(fields=['order'], name='support_sup_order_i_c35c9c_idx'),
            models.Index(fields=['product'], name='support_sup_product_cd2223_idx'),
        ]
