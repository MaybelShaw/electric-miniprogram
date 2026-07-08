from django.test import TestCase
from rest_framework.test import APIClient

from stores.models import Store, StoreMember
from support.models import SupportConversation, SupportMessage, SupportReplyTemplate
from users.models import User


class StoreSupportChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.main_store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.store = Store.objects.create(name="Partner", code="partner-chat", status=Store.STATUS_ACTIVE)
        self.other_store = Store.objects.create(name="Other", code="other-chat", status=Store.STATUS_ACTIVE)
        self.user = User.objects.create_user(username="customer", password="password")
        self.admin = User.objects.create_user(username="store-admin-chat", password="password", role="admin")
        self.support = User.objects.create_user(username="support-chat", password="password", role="support")
        StoreMember.objects.create(user=self.admin, store=self.store, role=StoreMember.ROLE_STORE_ADMIN)

    def test_store_admin_can_reply_only_own_store_conversation(self):
        own = SupportConversation.objects.create(user=self.user, store=self.store)
        other = SupportConversation.objects.create(user=self.user, store=self.other_store)
        SupportMessage.objects.create(conversation=own, sender=self.user, role="user", content="hello")
        SupportMessage.objects.create(conversation=other, sender=self.user, role="user", content="other")

        self.client.force_authenticate(self.admin)
        list_response = self.client.get("/api/support/chat/conversations/")
        reply_response = self.client.post(
            "/api/support/chat/",
            {"conversation_id": own.id, "content": "店铺已收到"},
            format="json",
        )
        forbidden_response = self.client.post(
            "/api/support/chat/",
            {"conversation_id": other.id, "content": "不能回复"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200, list_response.content)
        self.assertEqual([item["id"] for item in list_response.data["results"]], [own.id])
        self.assertEqual(reply_response.status_code, 201, reply_response.content)
        self.assertEqual(reply_response.data["role"], "support")
        self.assertEqual(forbidden_response.status_code, 403)

    def test_store_admin_can_trigger_auto_reply_only_own_store_conversation(self):
        own = SupportConversation.objects.create(user=self.user, store=self.store)
        other = SupportConversation.objects.create(user=self.user, store=self.other_store)
        SupportReplyTemplate.objects.create(
            store=self.store,
            template_type=SupportReplyTemplate.TYPE_AUTO,
            title="store reply",
            content="本店自动回复",
            trigger_event=SupportReplyTemplate.TRIGGER_FIRST,
            enabled=True,
        )

        self.client.force_authenticate(self.admin)
        own_response = self.client.post(f"/api/support/conversations/{own.id}/auto-reply/")
        forbidden_response = self.client.post(f"/api/support/conversations/{other.id}/auto-reply/")

        self.assertEqual(own_response.status_code, 201, own_response.content)
        self.assertTrue(own_response.data["triggered"])
        self.assertEqual(own_response.data["message"]["content"], "本店自动回复")
        self.assertEqual(forbidden_response.status_code, 403)

    def test_user_has_separate_conversation_per_store(self):
        self.client.force_authenticate(self.user)

        store_response = self.client.post(
            "/api/support/chat/",
            {"store_id": self.store.id, "content": "partner hello"},
            format="json",
        )
        main_response = self.client.post(
            "/api/support/chat/",
            {"content": "main hello"},
            format="json",
        )

        self.assertEqual(store_response.status_code, 201, store_response.content)
        self.assertEqual(main_response.status_code, 201, main_response.content)
        self.assertNotEqual(store_response.data["conversation"], main_response.data["conversation"])
        self.assertTrue(SupportConversation.objects.filter(user=self.user, store=self.store).exists())
        self.assertTrue(SupportConversation.objects.filter(user=self.user, store=self.main_store).exists())

    def test_non_main_store_does_not_trigger_platform_auto_reply(self):
        SupportReplyTemplate.objects.create(
            store=self.main_store,
            template_type=SupportReplyTemplate.TYPE_AUTO,
            title="main reply",
            content="丁当客服主店回复",
            trigger_event=SupportReplyTemplate.TRIGGER_FIRST,
            enabled=True,
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/support/chat/auto-reply/",
            {"store_id": self.store.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.data["triggered"])
        conversation = SupportConversation.objects.get(user=self.user, store=self.store)
        self.assertFalse(SupportMessage.objects.filter(conversation=conversation).exists())

    def test_non_main_store_triggers_own_auto_reply(self):
        SupportReplyTemplate.objects.create(
            store=self.store,
            template_type=SupportReplyTemplate.TYPE_AUTO,
            title="store reply",
            content="本店自动回复",
            trigger_event=SupportReplyTemplate.TRIGGER_FIRST,
            enabled=True,
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/support/chat/auto-reply/",
            {"store_id": self.store.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.data["triggered"])
        self.assertEqual(response.data["message"]["content"], "本店自动回复")

    def test_non_main_store_hides_legacy_auto_reply_messages(self):
        template = SupportReplyTemplate.objects.create(
            store=self.main_store,
            template_type=SupportReplyTemplate.TYPE_AUTO,
            title="main reply",
            content="丁当客服主店回复",
            trigger_event=SupportReplyTemplate.TRIGGER_FIRST,
            enabled=True,
        )
        conversation = SupportConversation.objects.create(user=self.user, store=self.store)
        SupportMessage.objects.create(conversation=conversation, sender=self.support, role="support", content="丁当客服主店回复", template=template)
        user_message = SupportMessage.objects.create(conversation=conversation, sender=self.user, role="user", content="用户消息")

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/support/chat/", {"store_id": self.store.id})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([item["id"] for item in response.data], [user_message.id])

    def test_store_admin_manages_only_own_reply_templates(self):
        own = SupportReplyTemplate.objects.create(
            store=self.store,
            template_type=SupportReplyTemplate.TYPE_AUTO,
            title="own",
            content="own reply",
            trigger_event=SupportReplyTemplate.TRIGGER_FIRST,
            enabled=True,
        )
        other = SupportReplyTemplate.objects.create(
            store=self.other_store,
            template_type=SupportReplyTemplate.TYPE_AUTO,
            title="other",
            content="other reply",
            trigger_event=SupportReplyTemplate.TRIGGER_FIRST,
            enabled=True,
        )

        self.client.force_authenticate(self.admin)
        list_response = self.client.get("/api/support/reply-templates/")
        create_response = self.client.post(
            "/api/support/reply-templates/",
            {
                "template_type": SupportReplyTemplate.TYPE_AUTO,
                "title": "new own",
                "content": "new reply",
                "trigger_event": SupportReplyTemplate.TRIGGER_FIRST,
                "enabled": True,
            },
            format="json",
        )
        forbidden_response = self.client.post(
            "/api/support/reply-templates/",
            {
                "store_id": self.other_store.id,
                "template_type": SupportReplyTemplate.TYPE_AUTO,
                "title": "bad",
                "content": "bad reply",
                "trigger_event": SupportReplyTemplate.TRIGGER_FIRST,
                "enabled": True,
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, 200, list_response.content)
        self.assertEqual([item["id"] for item in list_response.data["results"]], [own.id])
        self.assertNotIn(other.id, [item["id"] for item in list_response.data["results"]])
        self.assertEqual(create_response.status_code, 201, create_response.content)
        self.assertEqual(create_response.data["store"], self.store.id)
        self.assertEqual(forbidden_response.status_code, 403)
