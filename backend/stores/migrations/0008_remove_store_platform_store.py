from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0007_storepaymentconfig_profit_sharing"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="store",
            name="stores_stor_store_t_b105df_idx",
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["store_type"], name="stores_stor_store_t_93515a_idx"),
        ),
        migrations.RemoveField(
            model_name="store",
            name="platform_store",
        ),
    ]
