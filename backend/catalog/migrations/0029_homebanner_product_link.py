from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0028_product_zone_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='homebanner',
            name='product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='home_banners',
                to='catalog.product',
                verbose_name='跳转商品',
            ),
        ),
    ]
