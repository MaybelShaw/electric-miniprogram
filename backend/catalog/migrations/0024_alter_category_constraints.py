from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0023_case_casedetailblock_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='category',
            name='unique_category_level_name',
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.UniqueConstraint(
                fields=('level', 'name'),
                condition=Q(parent__isnull=True),
                name='unique_category_root_level_name',
            ),
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.UniqueConstraint(
                fields=('level', 'parent', 'name'),
                condition=Q(parent__isnull=False),
                name='unique_category_level_parent_name',
            ),
        ),
    ]
