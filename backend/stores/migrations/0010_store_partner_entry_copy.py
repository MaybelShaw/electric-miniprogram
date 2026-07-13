from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0009_store_is_visible"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartnerEntryConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entry_title", models.CharField(blank=True, default="", max_length=40, verbose_name="首页入口标题")),
                ("entry_subtitle", models.CharField(blank=True, default="", max_length=80, verbose_name="首页入口副标题")),
                ("section_title", models.CharField(blank=True, default="", max_length=40, verbose_name="首页板块标题")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "合作方入口配置",
                "verbose_name_plural": "合作方入口配置",
            },
        ),
    ]
