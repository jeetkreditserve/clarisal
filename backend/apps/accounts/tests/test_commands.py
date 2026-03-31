import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import AccountType, User, UserRole
from apps.departments.models import Department
from apps.employees.models import Employee, GovernmentIdType
from apps.invitations.models import Invitation
from apps.locations.models import OfficeLocation
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationOnboardingStage,
    OrganisationStatus,
)


@pytest.fixture
def seed_env(monkeypatch):
    monkeypatch.setenv('CONTROL_TOWER_EMAIL', 'control.tower@calrisal.com')
    monkeypatch.setenv('CONTROL_TOWER_PASSWORD', 'ControlTower@123')
    monkeypatch.setenv('SEED_ORGANISATION_NAME', 'Northstar People Pvt Ltd')
    monkeypatch.setenv('SEED_ORGANISATION_LICENCE_COUNT', '10')
    monkeypatch.setenv('SEED_ORGANISATION_PAN', 'AACCN1234F')
    monkeypatch.setenv('SEED_ORGANISATION_EMAIL', 'hello@northstarpeople.com')
    monkeypatch.setenv('SEED_ORGANISATION_PHONE', '+91 9123456789')
    monkeypatch.setenv('SEED_ORGANISATION_ADDRESS', '7 Brigade Road, Bengaluru, Karnataka 560001')
    monkeypatch.setenv('SEED_ORGANISATION_COUNTRY_CODE', 'IN')
    monkeypatch.setenv('SEED_ORGANISATION_CURRENCY', 'INR')
    monkeypatch.setenv('SEED_ORG_ADMIN_EMAIL', 'admin@northstarpeople.com')
    monkeypatch.setenv('SEED_ORG_ADMIN_PASSWORD', 'OrgAdmin@123')
    monkeypatch.setenv('SEED_ORG_ADMIN_FIRST_NAME', 'Aditi')
    monkeypatch.setenv('SEED_ORG_ADMIN_LAST_NAME', 'Rao')
    monkeypatch.setenv('SEED_EMPLOYEE_PASSWORD', 'Employee@123')
    return monkeypatch


@pytest.mark.django_db
class TestSeedControlTowerCommand:
    def test_command_fails_without_password_env_var(self, monkeypatch):
        monkeypatch.delenv('CONTROL_TOWER_PASSWORD', raising=False)

        with pytest.raises(CommandError) as exc_info:
            call_command('seed_control_tower')

        assert 'CONTROL_TOWER_PASSWORD environment variable is not set' in str(exc_info.value)

    def test_command_creates_groups_control_tower_and_demo_organisation(self, seed_env):
        call_command('seed_control_tower')

        assert Group.objects.filter(name='control_tower').exists()
        assert Group.objects.filter(name='org_admin').exists()
        assert Group.objects.filter(name='employee').exists()

        control_tower = User.objects.get(
            email='control.tower@calrisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        assert control_tower.account_type == AccountType.CONTROL_TOWER
        assert control_tower.role == UserRole.CONTROL_TOWER
        assert control_tower.is_superuser is True
        assert control_tower.is_staff is True
        assert control_tower.check_password('ControlTower@123')
        assert control_tower.groups.filter(name='control_tower').exists()

        organisation = Organisation.objects.get(name='Northstar People Pvt Ltd')
        assert organisation.licence_count == 10
        assert organisation.pan_number == 'AACCN1234F'
        assert organisation.status == OrganisationStatus.ACTIVE
        assert organisation.billing_status == OrganisationBillingStatus.PAID
        assert organisation.access_state == OrganisationAccessState.ACTIVE
        assert organisation.onboarding_stage == OrganisationOnboardingStage.EMPLOYEES_INVITED

        org_admin = User.objects.get(
            email='admin@northstarpeople.com',
            account_type=AccountType.WORKFORCE,
        )
        assert organisation.primary_admin_user_id == org_admin.id
        assert org_admin.account_type == AccountType.WORKFORCE
        assert org_admin.role == UserRole.ORG_ADMIN
        assert org_admin.organisation_id is None
        assert org_admin.is_active is True
        assert org_admin.check_password('OrgAdmin@123')
        assert org_admin.groups.filter(name='org_admin').exists()
        membership = OrganisationMembership.objects.get(user=org_admin, organisation=organisation)
        assert membership.is_org_admin is True
        assert membership.status == OrganisationMembershipStatus.ACTIVE

        assert OfficeLocation.objects.filter(organisation=organisation).count() == 2
        assert Department.objects.filter(organisation=organisation).count() == 3
        assert Employee.objects.filter(organisation=organisation).count() == 3
        assert Employee.objects.filter(organisation=organisation, status='ACTIVE').count() == 3
        assert OrganisationMembership.objects.filter(organisation=organisation).count() == 1
        assert Invitation.objects.count() == 0

        seeded_employee = Employee.objects.select_related('user', 'profile').get(employee_code='EMP001')
        assert seeded_employee.user.account_type == AccountType.WORKFORCE
        assert seeded_employee.user.check_password('Employee@123')
        assert seeded_employee.profile.phone_personal == '+91 9988776655'
        assert seeded_employee.education_records.count() == 1
        assert seeded_employee.bank_accounts.filter(is_primary=True).count() == 1
        assert seeded_employee.government_ids.count() == 2

        pan = seeded_employee.government_ids.get(id_type=GovernmentIdType.PAN)
        aadhaar = seeded_employee.government_ids.get(id_type=GovernmentIdType.AADHAAR)
        bank_account = seeded_employee.bank_accounts.get(is_primary=True)
        assert pan.masked_identifier
        assert aadhaar.masked_identifier
        assert bank_account.masked_account_number
        assert bank_account.account_number_encrypted != '123456789012'

    def test_command_is_idempotent_for_demo_seed(self, seed_env, capsys):
        call_command('seed_control_tower')
        first_org = Organisation.objects.get(name='Northstar People Pvt Ltd')
        first_control_tower = User.objects.get(
            email='control.tower@calrisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        first_org_admin = User.objects.get(
            email='admin@northstarpeople.com',
            account_type=AccountType.WORKFORCE,
        )

        call_command('seed_control_tower')

        second_org = Organisation.objects.get(name='Northstar People Pvt Ltd')
        second_control_tower = User.objects.get(
            email='control.tower@calrisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        second_org_admin = User.objects.get(
            email='admin@northstarpeople.com',
            account_type=AccountType.WORKFORCE,
        )

        assert second_org.id == first_org.id
        assert second_control_tower.id == first_control_tower.id
        assert second_org_admin.id == first_org_admin.id
        assert Organisation.objects.count() == 1
        assert OfficeLocation.objects.count() == 2
        assert Department.objects.count() == 3
        assert OrganisationMembership.objects.count() == 1
        assert Employee.objects.count() == 3
        assert Invitation.objects.count() == 0

        output = capsys.readouterr().out
        assert 'already exists' in output

    def test_command_fails_when_seed_licences_are_below_demo_employee_count(self, seed_env):
        seed_env.setenv('SEED_ORGANISATION_LICENCE_COUNT', '2')

        with pytest.raises(CommandError) as exc_info:
            call_command('seed_control_tower')

        assert 'must be at least 3' in str(exc_info.value)
        assert Group.objects.filter(name__in=['control_tower', 'org_admin', 'employee']).count() == 0
        assert User.objects.count() == 0
        assert Organisation.objects.count() == 0

    def test_command_uses_custom_control_tower_email_from_env(self, seed_env):
        seed_env.setenv('CONTROL_TOWER_EMAIL', 'platform-admin@calrisal.com')

        call_command('seed_control_tower')

        user = User.objects.get(
            email='platform-admin@calrisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        assert user.account_type == AccountType.CONTROL_TOWER
        assert user.role == UserRole.CONTROL_TOWER
