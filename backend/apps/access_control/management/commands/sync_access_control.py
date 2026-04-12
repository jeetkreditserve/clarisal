from django.core.management.base import BaseCommand

from apps.access_control.services import sync_access_control


class Command(BaseCommand):
    help = "Seed access-control permissions, roles, and compatibility assignments."

    def handle(self, *args, **options):
        summary = sync_access_control()
        self.stdout.write(
            self.style.SUCCESS(
                "Access-control catalog synchronized. "
                f"permissions={summary['permissions']} roles={summary['roles']} "
                f"ct_assignments={summary['ct_assignments']} org_assignments={summary['org_assignments']}"
            )
        )
