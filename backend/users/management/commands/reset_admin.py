from django.core.management.base import BaseCommand, CommandError
from users.models import User


class Command(BaseCommand):
    help = (
        "Reset or initialize the admin account. "
        "Sets username and password; if no admin exists, creates one. "
        "Use --target-openid to select a specific admin when multiple exist."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Target admin username to set")
        parser.add_argument("--password", required=True, help="New password to set for admin")
        parser.add_argument(
            "--target-openid",
            required=False,
            help="Specify exact admin by openid when multiple admins exist",
        )

    def handle(self, *args, **options):
        username: str = options["username"]
        password: str = options["password"]
        target_openid: str | None = options.get("target_openid")

        staff_qs = User.objects.filter(is_staff=True).order_by("-date_joined")

        user: User | None = None
        if target_openid:
            user = User.objects.filter(openid=target_openid, is_staff=True).first()
            if not user:
                raise CommandError(f"No admin found with openid={target_openid}")
        elif staff_qs.count() == 0:
            # Create first admin if none exists
            user = User.objects.create_user(
                openid=f"bootstrap:{username}", username=username, password=password
            )
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created first admin: username={username}"))
            return
        elif staff_qs.count() == 1:
            user = staff_qs.first()
        else:
            # Multiple admins exist; try match by username, otherwise require explicit target
            user = (
                User.objects.filter(username=username, is_staff=True)
                .order_by("-date_joined")
                .first()
            )
            if not user:
                raise CommandError(
                    "Multiple admins exist. Provide --target-openid to select which admin to reset."
                )

        # Set username and password for the selected/created admin
        user.username = username
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Admin reset: id={user.id}, username={user.username}, openid={user.openid}"
            )
        )