from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0005_alter_supportconversation_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportconversation',
            name='first_contacted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supportconversation',
            name='last_user_message_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supportconversation',
            name='last_support_message_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supportconversation',
            name='last_auto_reply_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='SupportReplyTemplate',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('template_type', models.CharField(choices=[('auto', '自动回复'), ('quick', '快捷回复')], default='quick', max_length=20)),
                ('title', models.CharField(max_length=120)),
                ('content', models.TextField()),
                ('enabled', models.BooleanField(default=True)),
                ('trigger_event', models.CharField(blank=True, choices=[('first_contact', '首次联系'), ('idle_contact', '长时间未联系')], max_length=20, null=True)),
                ('idle_minutes', models.PositiveIntegerField(blank=True, null=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='supportreplytemplate',
            index=models.Index(fields=['template_type', 'enabled'], name='support_tpl_type_idx'),
        ),
        migrations.AddIndex(
            model_name='supportreplytemplate',
            index=models.Index(fields=['trigger_event'], name='support_tpl_trigger_idx'),
        ),
    ]
