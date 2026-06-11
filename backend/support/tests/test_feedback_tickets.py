from django.test import TestCase
from rest_framework.test import APIClient

from stores.models import Store, StoreMember
from support.models import FeedbackTicket, FeedbackTicketReply
from users.models import User


class FeedbackTicketTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.platform = Store.objects.get(code=Store.MAIN_STORE_CODE)
        self.store = Store.objects.create(
            name="Zhibang",
            code="zhibang-feedback",
            status=Store.STATUS_ACTIVE,
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.other_store = Store.objects.create(
            name="Other",
            code="other-feedback",
            status=Store.STATUS_ACTIVE,
            store_type=Store.TYPE_PARTNER,
            platform_store=self.platform,
        )
        self.user = User.objects.create_user(username="customer", password="password", phone="13800000000")
        self.other_user = User.objects.create_user(username="other-customer", password="password")
        self.store_admin = User.objects.create_user(username="store-admin", password="password", role="admin")
        self.store_staff = User.objects.create_user(username="store-staff", password="password", role="admin")
        self.platform_admin = User.objects.create_user(
            username="platform-admin",
            password="password",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )
        self.support = User.objects.create_user(username="support", password="password", role="support")
        StoreMember.objects.create(user=self.store_admin, store=self.store, role=StoreMember.ROLE_STORE_ADMIN)
        StoreMember.objects.create(user=self.store_staff, store=self.store, role=StoreMember.ROLE_STORE_STAFF)

    def create_ticket(self, store=None, user=None, title="反馈标题测试", content="这里是一段至少十个字的问题描述"):
        return FeedbackTicket.objects.create(
            store=store or self.store,
            user=user or self.user,
            ticket_type=FeedbackTicket.TYPE_QUESTION,
            title=title,
            content=content,
            contact_phone="13900000000",
        )

    def test_user_can_create_and_list_own_ticket(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/support/feedback-tickets/",
            {
                "store_id": self.store.id,
                "ticket_type": "question",
                "title": "安装问题反馈",
                "content": "安装过程中遇到了一些问题需要协助处理",
                "contact_phone": "13800000000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertRegex(response.data["ticket_number"], r"^FB\d{8}0001$")
        self.assertEqual(response.data["status"], FeedbackTicket.STATUS_PENDING)

        other_ticket = self.create_ticket(store=self.other_store, user=self.other_user, title="其他用户反馈")
        list_response = self.client.get("/api/support/feedback-tickets/")

        self.assertEqual(list_response.status_code, 200, list_response.content)
        ids = [item["id"] for item in list_response.data["results"]]
        self.assertIn(response.data["id"], ids)
        self.assertNotIn(other_ticket.id, ids)

    def test_user_supplement_reopens_replied_ticket(self):
        ticket = self.create_ticket()
        ticket.status = FeedbackTicket.STATUS_REPLIED
        ticket.save(update_fields=["status"])

        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/supplement/",
            {"content": "这里补充一些新的现场情况"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, FeedbackTicket.STATUS_PENDING)
        self.assertTrue(ticket.replies.filter(record_type=FeedbackTicketReply.TYPE_USER_SUPPLEMENT).exists())

    def test_store_members_only_see_own_store_tickets(self):
        own = self.create_ticket(store=self.store, title="本店工单测试")
        other = self.create_ticket(store=self.other_store, title="其他店工单测试")

        self.client.force_authenticate(self.store_staff)
        response = self.client.get("/api/support/feedback-tickets/")

        self.assertEqual(response.status_code, 200, response.content)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [own.id])
        self.assertNotIn(other.id, ids)

    def test_legacy_store_staff_can_reply_and_close_as_store_admin(self):
        ticket = self.create_ticket()

        self.client.force_authenticate(self.store_staff)
        reply_response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/reply/",
            {"content": "我们已经收到，会尽快处理"},
            format="json",
        )
        close_response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/close/",
            {"content": "关闭"},
            format="json",
        )

        self.assertEqual(reply_response.status_code, 200, reply_response.content)
        self.assertEqual(close_response.status_code, 200, close_response.content)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, FeedbackTicket.STATUS_CLOSED)

    def test_store_admin_can_close_own_ticket(self):
        ticket = self.create_ticket()

        self.client.force_authenticate(self.store_admin)
        response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/close/",
            {"content": "已处理完成"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, FeedbackTicket.STATUS_CLOSED)
        self.assertTrue(ticket.replies.filter(record_type=FeedbackTicketReply.TYPE_CLOSE).exists())

    def test_platform_admin_can_manage_all_tickets(self):
        ticket = self.create_ticket(store=self.other_store)

        self.client.force_authenticate(self.platform_admin)
        list_response = self.client.get("/api/support/feedback-tickets/")
        close_response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/close/",
            {"content": "平台关闭"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200, list_response.content)
        self.assertIn(ticket.id, [item["id"] for item in list_response.data["results"]])
        self.assertEqual(close_response.status_code, 200, close_response.content)

    def test_support_can_reply_but_cannot_close(self):
        ticket = self.create_ticket(store=self.other_store)

        self.client.force_authenticate(self.support)
        reply_response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/reply/",
            {"content": "客服已记录并同步店铺"},
            format="json",
        )
        close_response = self.client.post(f"/api/support/feedback-tickets/{ticket.id}/close/", {}, format="json")

        self.assertEqual(reply_response.status_code, 200, reply_response.content)
        self.assertEqual(close_response.status_code, 403)

    def test_closed_ticket_is_read_only(self):
        ticket = self.create_ticket()
        ticket.status = FeedbackTicket.STATUS_CLOSED
        ticket.save(update_fields=["status"])

        self.client.force_authenticate(self.user)
        supplement_response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/supplement/",
            {"content": "还能补充吗"},
            format="json",
        )
        self.client.force_authenticate(self.store_admin)
        reply_response = self.client.post(
            f"/api/support/feedback-tickets/{ticket.id}/reply/",
            {"content": "还能回复吗"},
            format="json",
        )

        self.assertEqual(supplement_response.status_code, 400)
        self.assertEqual(reply_response.status_code, 400)

    def test_keyword_search_matches_user_phone_and_title(self):
        own = self.create_ticket(title="瓷砖需求反馈")
        self.user.phone = "18612345678"
        self.user.save(update_fields=["phone"])
        other = self.create_ticket(user=self.other_user, title="普通反馈")

        self.client.force_authenticate(self.store_admin)
        phone_response = self.client.get("/api/support/feedback-tickets/", {"search": "1861234"})
        title_response = self.client.get("/api/support/feedback-tickets/", {"search": "瓷砖"})

        self.assertEqual([item["id"] for item in phone_response.data["results"]], [own.id])
        self.assertEqual([item["id"] for item in title_response.data["results"]], [own.id])
        self.assertNotIn(other.id, [item["id"] for item in title_response.data["results"]])
