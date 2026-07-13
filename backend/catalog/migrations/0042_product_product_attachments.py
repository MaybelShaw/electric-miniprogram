from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0041_activity_home_store_cards'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='product_attachments',
            field=models.JSONField(blank=True, default=list, verbose_name='PDF附件'),
        ),
    ]
