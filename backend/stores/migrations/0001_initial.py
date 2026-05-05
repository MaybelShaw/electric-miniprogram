from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def create_main_store(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    Store.objects.get_or_create(
        code="main_store",
        defaults={
            "name": "main_store",
            "status": "active",
            "is_main": True,
            "allow_haier": True,
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Store",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, verbose_name="Store name")),
                ("code", models.SlugField(max_length=64, unique=True, verbose_name="Store code")),
                ("status", models.CharField(choices=[("active", "Active"), ("disabled", "Disabled")], default="active", max_length=20)),
                ("is_main", models.BooleanField(default=False)),
                ("allow_haier", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-is_main", "id"],
            },
        ),
        migrations.CreateModel(
            name="StoreMember",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("platform_admin", "Platform admin"), ("store_admin", "Store admin"), ("store_staff", "Store staff")], default="store_staff", max_length=32)),
                ("status", models.CharField(choices=[("active", "Active"), ("disabled", "Disabled")], default="active", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="members", to="stores.store")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="store_memberships", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="StorePaymentConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("wechat_mch_id", models.CharField(blank=True, default="", max_length=64)),
                ("wechat_sub_mch_id", models.CharField(blank=True, default="", max_length=64)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("store", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="payment_config", to="stores.store")),
            ],
        ),
        migrations.CreateModel(
            name="StoreSettlementRule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("commission_rate", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5)),
                ("settlement_cycle_days", models.PositiveIntegerField(default=7)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("store", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="settlement_rule", to="stores.store")),
            ],
        ),
        migrations.AddConstraint(
            model_name="store",
            constraint=models.UniqueConstraint(condition=Q(("is_main", True)), fields=("is_main",), name="stores_unique_main_store"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["code"], name="stores_stor_code_1c926b_idx"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["status"], name="stores_stor_status_d56e36_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="storemember",
            unique_together={("user", "store")},
        ),
        migrations.AddIndex(
            model_name="storemember",
            index=models.Index(fields=["user", "status"], name="stores_stor_user_id_65e6dc_idx"),
        ),
        migrations.AddIndex(
            model_name="storemember",
            index=models.Index(fields=["store", "role"], name="stores_stor_store_i_b24f1d_idx"),
        ),
        migrations.RunPython(create_main_store, migrations.RunPython.noop),
    ]
