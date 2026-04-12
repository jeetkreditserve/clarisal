from django.core.management.base import BaseCommand, CommandError

from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.reports.services import seed_system_report_templates, sync_report_catalog


class Command(BaseCommand):
    help = 'Seed system report templates for one organisation or all active organisations.'

    def add_arguments(self, parser):
        parser.add_argument('--organisation', type=str, help='Seed system report templates for one organisation id.')
        parser.add_argument(
            '--all-active-organisations',
            action='store_true',
            help='Seed system report templates for all active, paid, accessible organisations.',
        )

    def handle(self, *args, **options):
        organisation_id = options.get('organisation')
        seed_all = options.get('all_active_organisations')
        if bool(organisation_id) == bool(seed_all):
            raise CommandError('Provide exactly one of --organisation or --all-active-organisations.')

        sync_report_catalog()

        if organisation_id:
            organisations = Organisation.objects.filter(id=organisation_id)
            if not organisations.exists():
                raise CommandError('Organisation not found.')
        else:
            organisations = Organisation.objects.filter(
                status=OrganisationStatus.ACTIVE,
                billing_status=OrganisationBillingStatus.PAID,
                access_state=OrganisationAccessState.ACTIVE,
            )

        seeded = 0
        for organisation in organisations:
            seed_system_report_templates(organisation)
            seeded += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded system report templates for {seeded} organisation(s).'))
