"""
Management command to fix admin user roles.
This command updates all users with is_staff=True to have role='admin'.
"""
from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = 'Fix admin user roles - set role=admin for all is_staff users'

    def handle(self, *args, **options):
        # Find all staff users without admin role
        staff_users = User.objects.filter(is_staff=True).exclude(role='admin')
        count = staff_users.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No users need to be fixed.'))
            return
        
        # Update their roles
        updated = staff_users.update(role='admin')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated} admin user(s) to have role="admin"'
            )
        )
        
        # List updated users
        for user in User.objects.filter(is_staff=True, role='admin'):
            self.stdout.write(f'  - {user.username} (ID: {user.id})')
