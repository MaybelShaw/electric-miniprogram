from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


def get_main_store_pk():
    store, _ = Store.objects.get_or_create(
        code=Store.MAIN_STORE_CODE,
        defaults={
            "name": Store.MAIN_STORE_CODE,
            "status": Store.STATUS_ACTIVE,
            "is_main": True,
            "allow_haier": True,
        },
    )
    return store.pk


class Store(models.Model):
    MAIN_STORE_CODE = "main_store"

    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISABLED, "Disabled"),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name="Store name")
    code = models.SlugField(max_length=64, unique=True, verbose_name="Store code")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_main = models.BooleanField(default=False)
    allow_haier = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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
        ]

    def clean(self):
        if self.allow_haier and not self.is_main:
            raise ValidationError({"allow_haier": "Only the main store can enable Haier capability."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StoreMember(models.Model):
    ROLE_PLATFORM_ADMIN = "platform_admin"
    ROLE_STORE_ADMIN = "store_admin"
    ROLE_STORE_STAFF = "store_staff"
    ROLE_CHOICES = [
        (ROLE_PLATFORM_ADMIN, "Platform admin"),
        (ROLE_STORE_ADMIN, "Store admin"),
        (ROLE_STORE_STAFF, "Store staff"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISABLED, "Disabled"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="store_memberships")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="members")
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_STORE_STAFF)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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
    store = models.OneToOneField(Store, on_delete=models.PROTECT, related_name="payment_config")
    wechat_mch_id = models.CharField(max_length=64, blank=True, default="")
    wechat_sub_mch_id = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PaymentConfig#{self.store_id}"


class StoreSettlementRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    store = models.OneToOneField(Store, on_delete=models.PROTECT, related_name="settlement_rule")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    settlement_cycle_days = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SettlementRule#{self.store_id}"
