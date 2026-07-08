from django.test import TestCase
from rest_framework.test import APIClient

from stores.models import Store, StoreMember
from support.models import SupportConversation, SupportMessage
from users.models import User


class StoreSupportChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.main_store = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.store = Store.objects.create(name="Partner", code="partner-chat", status=Store.STATUS_ACTIVE)
        self.other_store = Store.objects.create(name="Other", code="other-chat", status=Store.STATUS_ACTIVE)
        self.user = User.objects.create_user(username="customer", password="password")
        self.admin = User.objects.create_user(username="store-admin-chat", password="password", role="admin")
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
