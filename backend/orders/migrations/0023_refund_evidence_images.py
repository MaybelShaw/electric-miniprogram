from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0022_discount_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='refund',
            name='evidence_images',
            field=models.JSONField(blank=True, default=list, verbose_name='退款凭证'),
        ),
    ]
