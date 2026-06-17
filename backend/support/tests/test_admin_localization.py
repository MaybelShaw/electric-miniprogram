from django.test import TestCase

from support.models import SupportConversation, SupportMessage, SupportReplyTemplate


class SupportAdminLocalizationTests(TestCase):
    def test_support_models_use_chinese_admin_metadata(self):
        self.assertEqual(SupportConversation._meta.verbose_name, "客服会话")
        self.assertEqual(SupportReplyTemplate._meta.verbose_name, "客服回复模板")
        self.assertEqual(SupportReplyTemplate._meta.get_field("title").verbose_name, "模板标题")
        self.assertEqual(SupportMessage._meta.verbose_name, "客服消息")
        self.assertEqual(SupportMessage._meta.get_field("content").verbose_name, "消息内容")
