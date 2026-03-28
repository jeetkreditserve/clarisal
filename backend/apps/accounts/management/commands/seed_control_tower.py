from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
import os


class Command(BaseCommand):
    help = 'Creates the initial Control Tower superuser and permission groups'

    def handle(self, *args, **options):
        from apps.accounts.models import User, UserRole

        # Create permission groups
        for group_name in ['control_tower', 'org_admin', 'employee']:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  Created group: {group_name}')

        # Create Control Tower user
        email = os.environ.get('CONTROL_TOWER_EMAIL', 'admin@calrisal.com')
        password = os.environ.get('CONTROL_TOWER_PASSWORD', 'CalrisalAdmin@2024!')

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Control Tower user {email} already exists, skipping.'))
            return

        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Control',
            last_name='Tower',
            role=UserRole.CONTROL_TOWER,
        )
        ct_group = Group.objects.get(name='control_tower')
        user.groups.add(ct_group)

        self.stdout.write(self.style.SUCCESS(f'Control Tower user created: {email}'))
        self.stdout.write(self.style.WARNING('IMPORTANT: Change the default password in production!'))
