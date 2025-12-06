from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, openid=None, username=None, password=None, **extra_fields):
        # For WeChat users, openid is required
        # For admin users, openid can be None
        if not username and not openid:
            raise ValueError("Either username or openid must be set")
        
        user = self.model(openid=openid, username=username or openid, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, openid=None, username=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(openid, username, password, **extra_fields)


def generate_unique_username():
    import uuid

    return "用户_" + str(uuid.uuid4())[:16]


class User(AbstractUser, PermissionsMixin):
    id = models.BigAutoField(primary_key=True)
    openid = models.CharField(max_length=64, unique=True, null=True, blank=True)
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        default=generate_unique_username,
        verbose_name="用户名",
    )

    avatar_url = models.URLField(
        max_length=200,
        blank=True,
        default="https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y",
        verbose_name="头像链接",
    )
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="手机号"
    )
    email = models.EmailField(blank=True, null=True, verbose_name="电子邮箱")
    
    # Unified role field: individual, dealer, or admin
    ROLE_CHOICES = [
        ('individual', '个人用户'),
        ('dealer', '经销商'),
        ('support', '客服'),
        ('admin', '管理员'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='individual',
        verbose_name='用户角色'
    )
    
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name='最后登录时间')

    objects = UserManager()

    # Use username as the primary authentication field for Django admin
    # openid is used for WeChat mini program authentication
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username or self.openid


class Notification(models.Model):
    STATUS_CHOICES = [
        ('pending', '待发送'),
        ('sent', '已发送'),
        ('failed', '发送失败'),
    ]

    TYPE_CHOICES = [
        ('payment', '支付'),
        ('order', '订单'),
        ('refund', '退款'),
        ('return', '退货'),
        ('statement', '对账单'),
        ('system', '系统'),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications', verbose_name='用户')
    title = models.CharField(max_length=100, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system', verbose_name='类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='阅读时间')

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['read_at']),
        ]

    def mark_sent(self):
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_read(self):
        if self.read_at:
            return
        self.read_at = timezone.now()
        self.save(update_fields=['read_at'])

    @property
    def is_read(self) -> bool:
        return bool(self.read_at)


class CompanyInfo(models.Model):
    """公司信息模型 - 用于经销商"""
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        User, 
        on_delete=models.PROTECT, 
        related_name="company_info",
        verbose_name="关联用户"
    )
    company_name = models.CharField(max_length=200, verbose_name="公司名称")
    business_license = models.CharField(max_length=100, unique=True, verbose_name="营业执照号")
    legal_representative = models.CharField(max_length=50, verbose_name="法人代表")
    contact_person = models.CharField(max_length=50, verbose_name="联系人")
    contact_phone = models.CharField(max_length=20, verbose_name="联系电话")
    contact_email = models.EmailField(blank=True, null=True, verbose_name="联系邮箱")
    
    # Company address
    province = models.CharField(max_length=20, blank=True, default='', verbose_name="省份")
    city = models.CharField(max_length=20, blank=True, default='', verbose_name="城市")
    district = models.CharField(max_length=20, blank=True, default='', verbose_name="区县")
    detail_address = models.CharField(max_length=200, blank=True, default='', verbose_name="详细地址")
    
    # Business scope and status
    business_scope = models.TextField(blank=True, verbose_name="经营范围")
    
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已审核'),
        ('rejected', '已拒绝'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='审核状态'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    
    class Meta:
        verbose_name = "公司信息"
        verbose_name_plural = "公司信息"
        indexes = [
            models.Index(fields=['business_license']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.company_name} - {self.get_status_display()}"


class Address(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="addresses")
    contact_name = models.CharField(max_length=50, verbose_name="联系人")
    phone = models.CharField(max_length=20, verbose_name="手机号")
    province = models.CharField(max_length=20, verbose_name="省份")
    city = models.CharField(max_length=20, verbose_name="城市")
    district = models.CharField(max_length=20, verbose_name="区县")
    detail = models.CharField(max_length=200, verbose_name="详细地址")
    is_default = models.BooleanField(default=False, verbose_name="默认地址")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "收货地址"
        verbose_name_plural = "收货地址"

    def __str__(self):
        return f"{self.contact_name},{self.phone},{self.province}, {self.city}, {self.district},{self.detail}"


class CreditAccount(models.Model):
    """经销商信用账户"""
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="credit_account",
        limit_choices_to={'role': 'dealer'},
        verbose_name="经销商用户"
    )
    
    # Credit settings
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="信用额度"
    )
    payment_term_days = models.IntegerField(
        default=30,
        verbose_name="账期（天）"
    )
    
    # Current balance
    outstanding_debt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="未结清欠款"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="账户状态")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "信用账户"
        verbose_name_plural = "信用账户"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - 信用额度: {self.credit_limit}"
    
    @property
    def available_credit(self):
        """可用额度 = 信用额度 - 未结清欠款"""
        return self.credit_limit - self.outstanding_debt
    
    def can_place_order(self, amount):
        """检查是否可以赊账下单"""
        return self.is_active and self.available_credit >= amount


class AccountStatement(models.Model):
    """账务对账单"""
    id = models.BigAutoField(primary_key=True)
    credit_account = models.ForeignKey(
        CreditAccount,
        on_delete=models.PROTECT,
        related_name="statements",
        verbose_name="信用账户"
    )
    
    # Statement period
    period_start = models.DateField(verbose_name="账期开始日期")
    period_end = models.DateField(verbose_name="账期结束日期")
    
    # Financial summary
    previous_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="上期结余"
    )
    current_purchases = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="本期采购"
    )
    current_payments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="本期付款"
    )
    current_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="本期退款"
    )
    period_end_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="期末未付"
    )
    
    # Due tracking
    due_within_term = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="账期内应付"
    )
    paid_within_term = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="账期内已付"
    )
    overdue_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="往来余额（逾期）"
    )
    
    # Statement status
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('confirmed', '已确认'),
        ('settled', '已结清'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='对账单状态'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="确认时间")
    settled_at = models.DateTimeField(null=True, blank=True, verbose_name="结清时间")
    
    class Meta:
        verbose_name = "账务对账单"
        verbose_name_plural = "账务对账单"
        ordering = ['-period_end', '-created_at']
        indexes = [
            models.Index(fields=['credit_account', 'period_start', 'period_end']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.credit_account.user.username} - {self.period_start} 至 {self.period_end}"


class AccountTransaction(models.Model):
    """账务交易记录"""
    id = models.BigAutoField(primary_key=True)
    credit_account = models.ForeignKey(
        CreditAccount,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="信用账户"
    )
    statement = models.ForeignKey(
        AccountStatement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="关联对账单"
    )
    
    # Transaction details
    TRANSACTION_TYPE_CHOICES = [
        ('purchase', '采购'),
        ('payment', '付款'),
        ('refund', '退款'),
        ('adjustment', '调整'),
    ]
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='交易类型'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="交易金额"
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="交易后余额"
    )
    
    # Related order (if applicable)
    order_id = models.BigIntegerField(null=True, blank=True, verbose_name="关联订单ID")
    
    # Due date for purchases
    due_date = models.DateField(null=True, blank=True, verbose_name="应付日期")
    paid_date = models.DateField(null=True, blank=True, verbose_name="实付日期")
    
    # Payment status
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', '未付款'),
        ('paid', '已付款'),
        ('overdue', '已逾期'),
    ]
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        verbose_name='付款状态'
    )
    
    # Description
    description = models.CharField(max_length=200, blank=True, verbose_name="备注")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "账务交易记录"
        verbose_name_plural = "账务交易记录"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['credit_account', 'created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} - {self.created_at.date()}"
