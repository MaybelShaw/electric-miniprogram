from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0005_store_show_customer_group_name_storecustomergroup_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storemember",
            name="role",
            field=models.CharField(
                choices=[
                    ("platform_admin", "平台管理员"),
                    ("store_admin", "店铺管理员"),
                    ("store_sub_admin", "店铺管理员"),
                    ("store_staff", "店铺管理员"),
                ],
                default="store_admin",
                max_length=32,
                verbose_name="成员角色",
            ),
        ),
    ]
