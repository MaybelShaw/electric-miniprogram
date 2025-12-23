from django.db import migrations, models


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
                fields=('level', 'parent', 'name'),
                name='unique_category_level_parent_name',
            ),
        ),
    ]
