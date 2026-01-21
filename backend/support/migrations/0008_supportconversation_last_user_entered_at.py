from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0007_support_reply_template_fields_and_message_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportconversation',
            name='last_user_entered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
