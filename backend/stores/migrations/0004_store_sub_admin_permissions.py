from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0003_alter_store_options_alter_storemember_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storemember",
            name="role",
            field=models.CharField(
                choices=[
                    ("platform_admin", "平台管理员"),
                    ("store_admin", "店铺管理员"),
                    ("store_sub_admin", "店铺子管理员"),
                    ("store_staff", "店铺运营"),
                ],
                default="store_staff",
                max_length=32,
                verbose_name="成员角色",
            ),
        ),
    ]
