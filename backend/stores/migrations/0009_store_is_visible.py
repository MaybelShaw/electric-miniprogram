from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0008_remove_store_platform_store"),
    ]

    operations = [
        migrations.AddField(
            model_name="store",
            name="is_visible",
            field=models.BooleanField(default=True, verbose_name="展示"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["is_visible"], name="stores_stor_is_visi_d6c5d4_idx"),
        ),
    ]
