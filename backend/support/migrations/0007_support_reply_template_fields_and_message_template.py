from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0006_support_reply_templates_and_conversation_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportreplytemplate',
            name='content_type',
            field=models.CharField(choices=[('text', '纯文本'), ('card', '图文卡片'), ('quick_buttons', '快捷问题按钮')], default='text', max_length=20),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='content_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='group_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='is_pinned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='daily_limit',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='user_cooldown_days',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='apply_channels',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='apply_user_tags',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='usage_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='supportreplytemplate',
            name='last_used_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supportmessage',
            name='content_type',
            field=models.CharField(default='text', max_length=20),
        ),
        migrations.AddField(
            model_name='supportmessage',
            name='content_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='supportmessage',
            name='template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='support.supportreplytemplate'),
        ),
    ]
