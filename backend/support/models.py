from django.db import models
from django.conf import settings
from orders.models import Order
from catalog.models import Product
from stores.models import Store
from django.utils import timezone


class SupportConversation(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_conversations', verbose_name='用户')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    first_contacted_at = models.DateTimeField(null=True, blank=True, verbose_name='首次联系时间')
    last_user_message_at = models.DateTimeField(null=True, blank=True, verbose_name='用户最后消息时间')
    last_user_entered_at = models.DateTimeField(null=True, blank=True, verbose_name='用户最后进入时间')
    last_support_message_at = models.DateTimeField(null=True, blank=True, verbose_name='客服最后消息时间')
    last_auto_reply_at = models.DateTimeField(null=True, blank=True, verbose_name='最后自动回复时间')

    class Meta:
        verbose_name = '客服会话'
        verbose_name_plural = '客服会话'
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
    TRIGGER_BOTH = 'both'
    TRIGGER_CHOICES = [
        (TRIGGER_FIRST, '首次联系'),
        (TRIGGER_IDLE, '长时间未联系'),
        (TRIGGER_BOTH, '首次联系 + 长时间未联系'),
    ]

    id = models.BigAutoField(primary_key=True)
    template_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_QUICK, verbose_name='模板类型')
    title = models.CharField(max_length=120, verbose_name='模板标题')
    content = models.TextField(verbose_name='回复内容')
    content_type = models.CharField(max_length=20, choices=CONTENT_CHOICES, default=CONTENT_TEXT, verbose_name='内容类型')
    content_payload = models.JSONField(default=dict, blank=True, verbose_name='内容配置')
    group_name = models.CharField(max_length=120, blank=True, default='', verbose_name='分组名称')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    enabled = models.BooleanField(default=True, verbose_name='是否启用')
    trigger_event = models.CharField(max_length=20, choices=TRIGGER_CHOICES, null=True, blank=True, verbose_name='触发事件')
    idle_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name='闲置分钟数')
    daily_limit = models.PositiveIntegerField(default=1, verbose_name='每日发送上限')
    user_cooldown_days = models.PositiveIntegerField(default=1, verbose_name='用户冷却天数')
    apply_channels = models.JSONField(default=list, blank=True, verbose_name='适用渠道')
    apply_user_tags = models.JSONField(default=list, blank=True, verbose_name='适用用户标签')
    usage_count = models.PositiveIntegerField(default=0, verbose_name='使用次数')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '客服回复模板'
        verbose_name_plural = '客服回复模板'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['template_type', 'enabled'], name='support_tpl_type_idx'),
            models.Index(fields=['trigger_event'], name='support_tpl_trigger_idx'),
        ]


class SupportMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(SupportConversation, on_delete=models.CASCADE, related_name='messages', verbose_name='会话')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_messages', verbose_name='发送人')
    role = models.CharField(max_length=20, default='', db_index=True, verbose_name='发送角色')
    content = models.TextField(blank=True, verbose_name='消息内容')
    content_type = models.CharField(max_length=20, default=SupportReplyTemplate.CONTENT_TEXT, verbose_name='内容类型')
    content_payload = models.JSONField(default=dict, blank=True, verbose_name='内容配置')
    attachment = models.FileField(upload_to='support/attachments/%Y/%m/%d/', null=True, blank=True, verbose_name='附件')
    attachment_type = models.CharField(max_length=10, choices=[('image', '图片'), ('video', '视频')], null=True, blank=True, db_index=True, verbose_name='附件类型')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_messages', verbose_name='关联订单')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_messages', verbose_name='关联商品')
    template = models.ForeignKey(SupportReplyTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages', verbose_name='关联模板')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '客服消息'
        verbose_name_plural = '客服消息'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='support_msg_conv_created_idx'),
            models.Index(fields=['attachment_type'], name='support_sup_attachm_54bc2a_idx'),
            models.Index(fields=['order'], name='support_sup_order_i_c35c9c_idx'),
            models.Index(fields=['product'], name='support_sup_product_cd2223_idx'),
        ]


class FeedbackTicket(models.Model):
    TYPE_QUESTION = 'question'
    TYPE_REQUIREMENT = 'requirement'
    TYPE_CHOICES = [
        (TYPE_QUESTION, '问题'),
        (TYPE_REQUIREMENT, '需求'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_REPLIED = 'replied'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_PENDING, '待处理'),
        (STATUS_REPLIED, '已回复'),
        (STATUS_CLOSED, '已关闭'),
    ]

    id = models.BigAutoField(primary_key=True)
    ticket_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name='工单编号')
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name='feedback_tickets', verbose_name='店铺')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='feedback_tickets', verbose_name='用户')
    ticket_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_QUESTION, verbose_name='工单类型')
    title = models.CharField(max_length=60, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    contact_phone = models.CharField(max_length=32, blank=True, default='', verbose_name='联系电话')
    attachments = models.JSONField(default=list, blank=True, verbose_name='图片附件')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='状态')
    last_replied_at = models.DateTimeField(null=True, blank=True, verbose_name='最后回复时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '问题建议工单'
        verbose_name_plural = '问题建议工单'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['ticket_number'], name='fb_ticket_no_idx'),
            models.Index(fields=['store', 'status'], name='fb_ticket_store_status_idx'),
            models.Index(fields=['user', 'created_at'], name='fb_ticket_user_created_idx'),
            models.Index(fields=['status', 'created_at'], name='fb_ticket_status_created_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_ticket_number(cls):
        prefix = f"FB{timezone.localdate().strftime('%Y%m%d')}"
        latest = (
            cls.objects.filter(ticket_number__startswith=prefix)
            .order_by('-ticket_number')
            .values_list('ticket_number', flat=True)
            .first()
        )
        next_seq = 1
        if latest:
            try:
                next_seq = int(latest[-4:]) + 1
            except (TypeError, ValueError):
                next_seq = 1
        return f"{prefix}{next_seq:04d}"

    def __str__(self):
        return self.ticket_number or f"FeedbackTicket#{self.pk}"


class FeedbackTicketReply(models.Model):
    TYPE_USER_SUPPLEMENT = 'user_supplement'
    TYPE_MERCHANT_REPLY = 'merchant_reply'
    TYPE_CLOSE = 'close'
    TYPE_CHOICES = [
        (TYPE_USER_SUPPLEMENT, '用户补充'),
        (TYPE_MERCHANT_REPLY, '商家回复'),
        (TYPE_CLOSE, '工单关闭'),
    ]

    id = models.BigAutoField(primary_key=True)
    ticket = models.ForeignKey(FeedbackTicket, on_delete=models.CASCADE, related_name='replies', verbose_name='工单')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='feedback_ticket_replies', verbose_name='发送人')
    record_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='记录类型')
    content = models.TextField(blank=True, default='', verbose_name='内容')
    attachments = models.JSONField(default=list, blank=True, verbose_name='图片附件')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '问题建议处理记录'
        verbose_name_plural = '问题建议处理记录'
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['ticket', 'created_at'], name='fb_reply_ticket_created_idx'),
            models.Index(fields=['record_type'], name='fb_reply_type_idx'),
        ]
