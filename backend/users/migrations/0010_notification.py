from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_user_last_login_at_user_user_type_alter_user_openid'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='标题')),
                ('content', models.TextField(verbose_name='内容')),
                ('type', models.CharField(choices=[('payment', '支付'), ('order', '订单'), ('refund', '退款'), ('system', '系统')], default='system', max_length=20, verbose_name='类型')),
                ('status', models.CharField(choices=[('pending', '待发送'), ('sent', '已发送'), ('failed', '发送失败')], default='pending', max_length=20, verbose_name='状态')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='元数据')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='发送时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='users.user', verbose_name='用户')),
            ],
            options={
                'verbose_name': '通知',
                'verbose_name_plural': '通知',
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'status'], name='users_notif_user_id__25c28a_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['type'], name='users_notif_type_1d15b6_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['created_at'], name='users_notif_created_6e8225_idx'),
        ),
    ]

