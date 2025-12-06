from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_user_last_login_at_user_user_type_alter_user_openid'),
        ('orders', '0018_alter_cart_user_alter_cartitem_cart_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Refund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='退款金额')),
                ('status', models.CharField(choices=[('pending', '待处理'), ('processing', '处理中'), ('succeeded', '退款成功'), ('failed', '退款失败')], default='pending', max_length=20, verbose_name='退款状态')),
                ('reason', models.CharField(blank=True, default='', max_length=255, verbose_name='退款原因')),
                ('transaction_id', models.CharField(blank=True, default='', max_length=100, verbose_name='退款交易号')),
                ('logs', models.JSONField(blank=True, default=list, verbose_name='退款日志')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='handled_refunds', to='users.user', verbose_name='操作人')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='refunds', to='orders.order', verbose_name='订单')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='refunds', to='orders.payment', verbose_name='关联支付')),
            ],
            options={
                'verbose_name': '退款记录',
                'verbose_name_plural': '退款记录',
            },
        ),
        migrations.AddIndex(
            model_name='refund',
            index=models.Index(fields=['status'], name='orders_refu_status_b5d603_idx'),
        ),
        migrations.AddIndex(
            model_name='refund',
            index=models.Index(fields=['order'], name='orders_refu_order_i_268222_idx'),
        ),
        migrations.AddIndex(
            model_name='refund',
            index=models.Index(fields=['payment'], name='orders_refu_payment_08a08a_idx'),
        ),
        migrations.AddIndex(
            model_name='refund',
            index=models.Index(fields=['created_at'], name='orders_refu_created_6d1cd2_idx'),
        ),
    ]

