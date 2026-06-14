import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, connections


class Command(BaseCommand):
    help = "Wait until the configured database accepts connections."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60)
        parser.add_argument("--interval", type=float, default=2.0)

    def handle(self, *args, **options):
        timeout = max(options["timeout"], 1)
        interval = max(options["interval"], 0.1)
        deadline = time.monotonic() + timeout
        last_error = None

        while time.monotonic() < deadline:
            try:
                connections["default"].ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database is available"))
                return
            except OperationalError as exc:
                last_error = exc
                self.stdout.write(f"Waiting for database: {exc}")
                time.sleep(interval)

        raise OperationalError(f"Database unavailable after {timeout}s: {last_error}")
