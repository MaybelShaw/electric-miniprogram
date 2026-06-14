import decimal

import django.db.models.deletion
import orders.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orders", "0029_checkout_suborders"),
        ("stores", "0007_storepaymentconfig_profit_sharing"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="profit_sharing_required",
            field=models.BooleanField(default=False, verbose_name="是否微信分账订单"),
        ),
        migrations.AddField(
            model_name="payment",
            name="profit_sharing_status",
            field=models.CharField(
                choices=[
                    ("not_required", "无需分账"),
                    ("pending", "待支付"),
                    ("pending_receiver_config", "待配置接收方"),
                    ("frozen", "冻结中"),
                    ("available", "可分账"),
                    ("processing", "分账处理中"),
                    ("shared", "分账完成"),
                    ("failed", "分账失败"),
                    ("manual_settlement_required", "需人工结算"),
                ],
                default="not_required",
                max_length=40,
                verbose_name="分账状态",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="profit_sharing_unfrozen",
            field=models.BooleanField(default=False, verbose_name="分账剩余资金已解冻"),
        ),
        migrations.CreateModel(
            name="StoreProfitSharingEntry",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("store_type_snapshot", models.CharField(max_length=32, verbose_name="店铺类型快照")),
                ("gross_amount", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="子单实付金额")),
                ("commission_rate_snapshot", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=5, verbose_name="抽佣比例快照")),
                ("commission_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10, verbose_name="抽佣金额")),
                ("sharing_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10, verbose_name="分账金额")),
                ("retained_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10, verbose_name="平台留存金额")),
                ("receiver_type", models.CharField(blank=True, default="", max_length=32, verbose_name="接收方类型")),
                ("receiver_account", models.CharField(blank=True, default="", max_length=64, verbose_name="接收方账号")),
                ("receiver_name_snapshot", models.CharField(blank=True, default="", max_length=128, verbose_name="接收方名称快照")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("platform_retained", "平台留存"),
                            ("pending_receiver_config", "待配置接收方"),
                            ("frozen", "冻结中"),
                            ("available", "可分账"),
                            ("available_for_manual_share", "可手动分账"),
                            ("processing", "处理中"),
                            ("shared", "分账成功"),
                            ("failed", "分账失败"),
                            ("manual_settled", "人工结算"),
                            ("manual_settlement_required", "需人工结算"),
                            ("cancelled", "已取消"),
                        ],
                        default="frozen",
                        max_length=40,
                        verbose_name="分账流水状态",
                    ),
                ),
                ("available_at", models.DateTimeField(blank=True, null=True, verbose_name="可分账时间")),
                ("shared_at", models.DateTimeField(blank=True, null=True, verbose_name="分账成功时间")),
                ("failure_reason", models.TextField(blank=True, default="", verbose_name="失败原因")),
                ("logs", models.JSONField(blank=True, default=list, verbose_name="日志")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("checkout_order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="profit_sharing_entries", to="orders.checkoutorder", verbose_name="结算单")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="profit_sharing_entries", to="orders.order", verbose_name="兼容订单")),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="profit_sharing_entries", to="orders.payment", verbose_name="支付记录")),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="profit_sharing_entries", to="stores.store", verbose_name="店铺")),
                ("suborder", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="profit_sharing_entry", to="orders.suborder", verbose_name="子单")),
            ],
            options={
                "verbose_name": "店铺分账流水",
                "verbose_name_plural": "店铺分账流水",
            },
        ),
        migrations.CreateModel(
            name="WechatProfitSharingOrder",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("out_order_no", models.CharField(default=orders.models.generate_order_number, max_length=100, unique=True, verbose_name="商户分账单号")),
                ("transaction_id", models.CharField(blank=True, default="", max_length=100, verbose_name="微信支付交易号")),
                ("receivers", models.JSONField(blank=True, default=list, verbose_name="接收方列表")),
                ("amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10, verbose_name="分账总金额")),
                ("unfreeze_unsplit", models.BooleanField(default=False, verbose_name="解冻剩余资金")),
                ("status", models.CharField(choices=[("processing", "处理中"), ("shared", "分账成功"), ("failed", "分账失败"), ("closed", "已关闭")], default="processing", max_length=20, verbose_name="状态")),
                ("wechat_response", models.JSONField(blank=True, default=dict, verbose_name="微信响应")),
                ("error_message", models.TextField(blank=True, default="", verbose_name="错误信息")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("checkout_order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="wechat_profit_sharing_orders", to="orders.checkoutorder", verbose_name="结算单")),
                ("operator", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="wechat_profit_sharing_orders", to=settings.AUTH_USER_MODEL, verbose_name="操作人")),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="wechat_profit_sharing_orders", to="orders.payment", verbose_name="支付记录")),
                ("entries", models.ManyToManyField(blank=True, related_name="wechat_profit_sharing_orders", to="orders.storeprofitsharingentry", verbose_name="分账流水")),
            ],
            options={
                "verbose_name": "微信分账请求",
                "verbose_name_plural": "微信分账请求",
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["profit_sharing_status"], name="orders_paym_profit_1fae24_idx"),
        ),
        migrations.AddIndex(
            model_name="storeprofitsharingentry",
            index=models.Index(fields=["checkout_order", "status"], name="orders_stor_checkou_37be54_idx"),
        ),
        migrations.AddIndex(
            model_name="storeprofitsharingentry",
            index=models.Index(fields=["payment", "status"], name="orders_stor_payment_3e5fb7_idx"),
        ),
        migrations.AddIndex(
            model_name="storeprofitsharingentry",
            index=models.Index(fields=["store", "status"], name="orders_stor_store_i_85c69f_idx"),
        ),
        migrations.AddIndex(
            model_name="storeprofitsharingentry",
            index=models.Index(fields=["available_at"], name="orders_stor_availab_8ee3af_idx"),
        ),
        migrations.AddIndex(
            model_name="wechatprofitsharingorder",
            index=models.Index(fields=["payment", "status"], name="orders_wech_payment_4607af_idx"),
        ),
        migrations.AddIndex(
            model_name="wechatprofitsharingorder",
            index=models.Index(fields=["checkout_order", "status"], name="orders_wech_checkou_c3e46f_idx"),
        ),
        migrations.AddIndex(
            model_name="wechatprofitsharingorder",
            index=models.Index(fields=["created_at"], name="orders_wech_created_922b54_idx"),
        ),
    ]
