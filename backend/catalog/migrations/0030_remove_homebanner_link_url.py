from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0029_homebanner_product_link'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='homebanner',
            name='link_url',
        ),
    ]
