from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0023_refund_evidence_images'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='haier_fail_msg',
            field=models.TextField(blank=True, default='', verbose_name='海尔失败信息'),
        ),
    ]
