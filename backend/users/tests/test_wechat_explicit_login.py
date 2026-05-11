from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User


class MockWechatResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


@override_settings(WECHAT_APPID="appid", WECHAT_SECRET="secret", DEBUG=False)
class WeChatExplicitLoginTests(TestCase):
    url = "/api/wechat/explicit-login/"

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @patch("users.views.requests.get")
    def test_first_login_without_phone_authorization_does_not_create_user(self, mock_get):
        mock_get.return_value = MockWechatResponse(
            {"openid": "openid-new", "session_key": "session-key"}
        )

        response = self.client.post(self.url, {"code": "js-code"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("phone", response.data["error"].lower())

    @patch("users.views.requests.post")
    @patch("users.views.requests.get")
    def test_phone_authorization_creates_or_reuses_user_and_returns_tokens(
        self, mock_get, mock_post
    ):
        mock_get.side_effect = [
            MockWechatResponse({"openid": "openid-1", "session_key": "session-key"}),
            MockWechatResponse({"access_token": "access-token", "expires_in": 7200}),
            MockWechatResponse({"openid": "openid-1", "session_key": "session-key"}),
            MockWechatResponse({"access_token": "access-token", "expires_in": 7200}),
        ]
        mock_post.return_value = MockWechatResponse(
            {"errcode": 0, "phone_info": {"phoneNumber": "13800138000"}}
        )

        first = self.client.post(
            self.url,
            {"code": "js-code", "phone_code": "phone-code"},
            format="json",
        )
        second = self.client.post(
            self.url,
            {"code": "js-code-2", "phone_code": "phone-code-2"},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertIn("access", first.data)
        self.assertIn("refresh", first.data)
        self.assertEqual(first.data["user"]["phone"], "13800138000")
        self.assertEqual(User.objects.count(), 1)

        user = User.objects.get(openid="openid-1")
        self.assertEqual(user.phone, "13800138000")
        self.assertIsNotNone(user.last_login_at)

    @patch("users.views.requests.post")
    @patch("users.views.requests.get")
    def test_default_username_is_generated_without_profile_authorization(
        self, mock_get, mock_post
    ):
        mock_get.side_effect = [
            MockWechatResponse({"openid": "openid-default-name", "session_key": "session-key"}),
            MockWechatResponse({"access_token": "access-token", "expires_in": 7200}),
        ]
        mock_post.return_value = MockWechatResponse(
            {"errcode": 0, "phone_info": {"phoneNumber": "13900139000"}}
        )

        response = self.client.post(
            self.url,
            {"code": "js-code", "phone_code": "phone-code"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["user"]["username"].startswith("用户_"))
        self.assertTrue(response.data["user"]["avatar_url"])


@override_settings(WECHAT_APPID="", WECHAT_SECRET="", DEBUG=True)
class WeChatExplicitLoginDevelopmentTests(TestCase):
    url = "/api/wechat/explicit-login/"

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_debug_mode_without_wechat_credentials_simulates_phone_login(self):
        response = self.client.post(
            self.url,
            {"code": "dev-openid", "phone_code": "dev-phone-code"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["phone"], "13800000000")
        self.assertTrue(User.objects.filter(openid="dev-openid").exists())
