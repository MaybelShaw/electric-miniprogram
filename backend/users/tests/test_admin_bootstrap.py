from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User


class ProductionAdminBootstrapTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch.dict("os.environ", {"DJANGO_ENV": "production"})
    def test_password_login_does_not_create_first_admin_in_production(self):
        response = self.client.post(
            "/api/admin/login/",
            {"username": "new-admin", "password": "strong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(User.objects.exists())

    @patch.dict("os.environ", {"DJANGO_ENV": "production"})
    def test_password_login_does_not_promote_existing_user_in_production(self):
        user = User.objects.create_user(username="ordinary", password="password")

        response = self.client.post(
            "/api/admin/login/",
            {"username": "ordinary", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    @patch.dict("os.environ", {"DJANGO_ENV": "production"})
    def test_reset_admin_does_not_create_first_admin_in_production(self):
        with self.assertRaises(CommandError):
            call_command(
                "reset_admin",
                username="admin",
                password="strong-password",
                stdout=StringIO(),
            )

        self.assertFalse(User.objects.exists())

    @patch.dict("os.environ", {"DJANGO_ENV": "production"})
    def test_reset_admin_can_reset_existing_admin_in_production(self):
        admin = User.objects.create_user(
            username="admin",
            password="old-password",
            is_staff=True,
            is_superuser=True,
            role="admin",
        )

        call_command(
            "reset_admin",
            username="admin",
            password="new-password",
            stdout=StringIO(),
        )

        admin.refresh_from_db()
        self.assertTrue(admin.check_password("new-password"))
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
