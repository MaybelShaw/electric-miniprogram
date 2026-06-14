from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0006_storemember_role_business_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="storepaymentconfig",
            name="profit_sharing_enabled",
            field=models.BooleanField(default=False, verbose_name="启用微信分账"),
        ),
        migrations.AddField(
            model_name="storepaymentconfig",
            name="profit_sharing_receiver_type",
            field=models.CharField(
                choices=[("MERCHANT_ID", "商户号")],
                default="MERCHANT_ID",
                max_length=32,
                verbose_name="分账接收方类型",
            ),
        ),
        migrations.AddField(
            model_name="storepaymentconfig",
            name="profit_sharing_receiver_name",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="分账接收方名称"),
        ),
        migrations.AddField(
            model_name="storepaymentconfig",
            name="profit_sharing_receiver_added",
            field=models.BooleanField(default=False, verbose_name="已添加微信分账接收方"),
        ),
        migrations.AddField(
            model_name="storepaymentconfig",
            name="profit_sharing_receiver_verified",
            field=models.BooleanField(default=False, verbose_name="分账接收方已校验"),
        ),
    ]
