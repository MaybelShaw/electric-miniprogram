from django.db import migrations, models


def forwards(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    for p in Product.objects.all():
        main_images = []
        try:
            # 若旧字段存在且有值，则作为第一张主图
            if hasattr(p, 'main_image') and p.main_image:
                main_images = [p.main_image]
        except Exception:
            main_images = []
        try:
            p.main_images = main_images
            p.save(update_fields=['main_images'])
        except Exception:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0005_mediaimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='main_images',
            field=models.JSONField(blank=True, default=list, verbose_name='主图URL列表'),
        ),
        migrations.RemoveField(
            model_name='product',
            name='main_image',
        ),
        migrations.RunPython(forwards),
    ]