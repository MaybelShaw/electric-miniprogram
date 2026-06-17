from django.db import migrations, models
import django.db.models.deletion


def migrate_store_marketplace_fields(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    platform = Store.objects.filter(is_main=True).order_by("id").first()
    if platform is None:
        platform, _ = Store.objects.get_or_create(
            code="main_store",
            defaults={
                "name": "main_store",
                "status": "active",
                "is_main": True,
                "allow_haier": True,
            },
        )

    Store.objects.filter(id=platform.id).update(
        store_type="self_operated",
        platform_store=None,
        show_on_home=True,
    )
    Store.objects.exclude(id=platform.id).update(
        store_type="partner",
        platform_store=platform,
        allow_haier=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="store",
            name="address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="store",
            name="contact_phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="store",
            name="cover_image",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="store",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="store",
            name="home_order",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="store",
            name="logo",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="store",
            name="platform_store",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="partner_stores",
                to="stores.store",
            ),
        ),
        migrations.AddField(
            model_name="store",
            name="show_on_home",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="store",
            name="store_type",
            field=models.CharField(
                choices=[
                    ("self_operated", "Self operated"),
                    ("partner", "Partner"),
                    ("supplier", "Supplier"),
                ],
                default="self_operated",
                max_length=32,
            ),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["store_type", "platform_store"], name="stores_stor_store_t_b105df_idx"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["show_on_home", "home_order"], name="stores_stor_show_on_3c41e4_idx"),
        ),
        migrations.RunPython(migrate_store_marketplace_fields, migrations.RunPython.noop),
    ]
