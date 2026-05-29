from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


def get_main_store_pk():
    from django.db import connection

    table_name = Store._meta.db_table
    column_names = {
        column.name
        for column in connection.introspection.get_table_description(connection.cursor(), table_name)
    }
    defaults = {
        "name": Store.MAIN_STORE_CODE,
        "status": Store.STATUS_ACTIVE,
        "is_main": True,
        "allow_haier": True,
    }
    if "store_type" in column_names:
        defaults["store_type"] = Store.TYPE_SELF_OPERATED
    if "show_on_home" in column_names:
        defaults["show_on_home"] = True

    store, _ = Store.objects.only("id").get_or_create(code=Store.MAIN_STORE_CODE, defaults=defaults)
    return store.pk


class Store(models.Model):
    MAIN_STORE_CODE = "main_store"

    TYPE_SELF_OPERATED = "self_operated"
    TYPE_PARTNER = "partner"
    TYPE_SUPPLIER = "supplier"
    TYPE_CHOICES = [
        (TYPE_SELF_OPERATED, "自营店铺"),
        (TYPE_PARTNER, "合作方店铺"),
        (TYPE_SUPPLIER, "供应商"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "启用"),
        (STATUS_DISABLED, "停用"),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="店铺名称")
    code = models.SlugField(max_length=64, unique=True, verbose_name="店铺编码")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name="状态")
    is_main = models.BooleanField(default=False, verbose_name="是否主店")
    store_type = models.CharField(max_length=32, choices=TYPE_CHOICES, default=TYPE_SELF_OPERATED, verbose_name="店铺类型")
    platform_store = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="partner_stores",
        verbose_name="所属平台店铺",
    )
    logo = models.CharField(max_length=512, blank=True, default="", verbose_name="店铺Logo")
    cover_image = models.CharField(max_length=512, blank=True, default="", verbose_name="封面图")
    description = models.TextField(blank=True, default="", verbose_name="店铺简介")
    show_on_home = models.BooleanField(default=False, verbose_name="首页展示")
    home_order = models.IntegerField(default=0, verbose_name="首页排序")
    contact_phone = models.CharField(max_length=32, blank=True, default="", verbose_name="联系电话")
    address = models.CharField(max_length=255, blank=True, default="", verbose_name="地址")
    allow_haier = models.BooleanField(default=False, verbose_name="启用海尔能力")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "店铺"
        verbose_name_plural = "店铺"
        ordering = ["-is_main", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_main"],
                condition=Q(is_main=True),
                name="stores_unique_main_store",
            ),
        ]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["store_type", "platform_store"]),
            models.Index(fields=["show_on_home", "home_order"]),
        ]

    def clean(self):
        errors = {}
        if self.is_main and self.store_type != self.TYPE_SELF_OPERATED:
            errors["store_type"] = "主店必须是自营店铺。"
        if self.platform_store_id and self.platform_store_id == self.id:
            errors["platform_store"] = "店铺不能归属于自身。"
        if self.store_type == self.TYPE_PARTNER and not self.platform_store_id:
            errors["platform_store"] = "合作方店铺必须归属于一个平台店铺。"
        if self.allow_haier and not self.is_main:
            errors["allow_haier"] = "只有主店可以启用海尔能力。"
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StoreMember(models.Model):
    ROLE_PLATFORM_ADMIN = "platform_admin"
    ROLE_STORE_ADMIN = "store_admin"
    ROLE_STORE_SUB_ADMIN = "store_sub_admin"
    ROLE_STORE_STAFF = "store_staff"
    ROLE_CHOICES = [
        (ROLE_PLATFORM_ADMIN, "平台管理员"),
        (ROLE_STORE_ADMIN, "店铺管理员"),
        (ROLE_STORE_SUB_ADMIN, "店铺子管理员"),
        (ROLE_STORE_STAFF, "店铺运营"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "启用"),
        (STATUS_DISABLED, "停用"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="store_memberships", verbose_name="用户")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="members", verbose_name="店铺")
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_STORE_STAFF, verbose_name="成员角色")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "店铺成员"
        verbose_name_plural = "店铺成员"
        unique_together = [("user", "store")]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["store", "role"]),
        ]

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE and self.store.status == Store.STATUS_ACTIVE

    def __str__(self):
        return f"{self.user_id}@{self.store_id}:{self.role}"


class StorePaymentConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    store = models.OneToOneField(Store, on_delete=models.PROTECT, related_name="payment_config", verbose_name="店铺")
    wechat_mch_id = models.CharField(max_length=64, blank=True, default="", verbose_name="微信商户号")
    wechat_sub_mch_id = models.CharField(max_length=64, blank=True, default="", verbose_name="微信子商户号")
    is_active = models.BooleanField(default=False, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "店铺支付配置"
        verbose_name_plural = "店铺支付配置"

    def __str__(self):
        return f"PaymentConfig#{self.store_id}"


class StoreSettlementRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    store = models.OneToOneField(Store, on_delete=models.PROTECT, related_name="settlement_rule", verbose_name="店铺")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="佣金比例")
    settlement_cycle_days = models.PositiveIntegerField(default=7, verbose_name="结算周期天数")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "店铺结算规则"
        verbose_name_plural = "店铺结算规则"

    def __str__(self):
        return f"SettlementRule#{self.store_id}"
