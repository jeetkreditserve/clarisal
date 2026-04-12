from django.core.management.base import BaseCommand

from apps.reports.services import sync_report_catalog


class Command(BaseCommand):
    help = 'Synchronize report-builder datasets and fields.'

    def handle(self, *args, **options):
        sync_report_catalog()
        self.stdout.write(self.style.SUCCESS('Report catalog synchronized.'))
