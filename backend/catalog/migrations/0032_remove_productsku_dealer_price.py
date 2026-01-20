from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0031_product_dealer_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productsku',
            name='dealer_price',
        ),
    ]
