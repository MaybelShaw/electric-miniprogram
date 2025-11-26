from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_product_images_json'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='category',
            name='level',
        ),
    ]