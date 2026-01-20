from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0030_remove_homebanner_link_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='dealer_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='经销价'),
        ),
        migrations.AddField(
            model_name='productsku',
            name='dealer_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='经销价'),
        ),
    ]
