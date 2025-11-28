from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager


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
        extra_fields.setdefault("user_type", "admin")
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
    
    # New fields for dual authentication
    USER_TYPE_CHOICES = [
        ('wechat', '微信用户'),
        ('admin', '管理员'),
    ]
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='wechat',
        verbose_name='用户类型'
    )
    
    # User role: individual or dealer
    ROLE_CHOICES = [
        ('individual', '个人用户'),
        ('dealer', '经销商'),
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


class CompanyInfo(models.Model):
    """公司信息模型 - 用于经销商"""
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
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
