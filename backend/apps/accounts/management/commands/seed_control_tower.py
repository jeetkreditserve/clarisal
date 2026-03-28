from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
from django.db import transaction
import os


class Command(BaseCommand):
    help = 'Creates the initial Control Tower superuser and permission groups'

    def handle(self, *args, **options):
        from apps.accounts.models import User, UserRole

        # Validate required environment variable
        password = os.environ.get('CONTROL_TOWER_PASSWORD')
        if not password:
            raise CommandError(
                'CONTROL_TOWER_PASSWORD environment variable is not set. '
                'Set it before running this command.'
            )

        with transaction.atomic():
            # Create permission groups
            for group_name in ['control_tower', 'org_admin', 'employee']:
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    self.stdout.write(f'  Created group: {group_name}')

            # Create Control Tower user
            email = os.environ.get('CONTROL_TOWER_EMAIL', 'admin@calrisal.com')

            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'Control Tower user {email} already exists, skipping creation.'))
                # Verify groups exist but don't return early
                ct_group = Group.objects.get(name='control_tower')
                user = User.objects.get(email=email)
                if ct_group not in user.groups.all():
                    user.groups.add(ct_group)
                    self.stdout.write(self.style.SUCCESS(f'Added control_tower group to existing user {email}'))
            else:
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
