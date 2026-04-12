import pytest
from django.core.management import call_command

from apps.accounts.models import User, UserRole
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.reports.models import ReportFolder, ReportTemplate


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='reports-ct@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.CONTROL_TOWER,
    )


@pytest.mark.django_db
def test_seed_system_report_templates_for_one_organisation(ct_user):
    organisation = Organisation.objects.create(
        name='Report Seed Org',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
        country_code='IN',
        currency='INR',
    )

    call_command('seed_system_report_templates', '--organisation', str(organisation.id))

    assert ReportFolder.objects.filter(organisation=organisation, name='System Reports').exists()
    assert ReportTemplate.objects.filter(organisation=organisation, name='Payroll Register', is_system=True).exists()
    assert ReportTemplate.objects.filter(organisation=organisation, name='Headcount', is_system=True).exists()


@pytest.mark.django_db
def test_seed_system_report_templates_for_all_active_organisations_only(ct_user):
    active_org = Organisation.objects.create(
        name='Active Seed Org',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
        country_code='IN',
        currency='INR',
    )
    inactive_org = Organisation.objects.create(
        name='Inactive Seed Org',
        created_by=ct_user,
        status=OrganisationStatus.PENDING,
        billing_status=OrganisationBillingStatus.PENDING_PAYMENT,
        access_state=OrganisationAccessState.PROVISIONING,
        country_code='IN',
        currency='INR',
    )

    call_command('seed_system_report_templates', '--all-active-organisations')

    assert ReportTemplate.objects.filter(organisation=active_org, is_system=True).count() >= 2
    assert not ReportTemplate.objects.filter(organisation=inactive_org, is_system=True).exists()
