from django.test import TestCase

from stores.models import Store, StoreMember, StorePaymentConfig, StoreSettlementRule


class StoreAdminLocalizationTests(TestCase):
    def test_store_models_use_chinese_admin_metadata(self):
        self.assertEqual(Store._meta.verbose_name, "店铺")
        self.assertEqual(Store._meta.verbose_name_plural, "店铺")
        self.assertEqual(Store._meta.get_field("name").verbose_name, "店铺名称")
        self.assertEqual(Store._meta.get_field("code").verbose_name, "店铺编码")
        self.assertEqual(Store._meta.get_field("store_type").verbose_name, "店铺类型")
        self.assertEqual(dict(Store.TYPE_CHOICES)[Store.TYPE_SELF_OPERATED], "自营店铺")
        self.assertEqual(dict(Store.STATUS_CHOICES)[Store.STATUS_ACTIVE], "启用")

    def test_store_member_and_config_models_use_chinese_admin_metadata(self):
        self.assertEqual(StoreMember._meta.verbose_name, "店铺成员")
        self.assertEqual(StoreMember._meta.get_field("role").verbose_name, "成员角色")
        self.assertEqual(dict(StoreMember.ROLE_CHOICES)[StoreMember.ROLE_STORE_ADMIN], "店铺管理员")
        self.assertEqual(dict(StoreMember.STATUS_CHOICES)[StoreMember.STATUS_DISABLED], "停用")

        self.assertEqual(StorePaymentConfig._meta.verbose_name, "店铺支付配置")
        self.assertEqual(StorePaymentConfig._meta.get_field("wechat_mch_id").verbose_name, "微信商户号")
        self.assertEqual(StoreSettlementRule._meta.verbose_name, "店铺结算规则")
        self.assertEqual(StoreSettlementRule._meta.get_field("commission_rate").verbose_name, "佣金比例")
