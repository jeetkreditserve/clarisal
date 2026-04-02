import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import ApprovalWorkflow
from apps.communications.models import Notice
from apps.departments.models import Department
from apps.documents.models import EmployeeDocumentRequest, OnboardingDocumentType
from apps.employees.models import Employee, EmployeeStatus, GovernmentIdType
from apps.invitations.models import Invitation, InvitationStatus
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
from apps.organisations.services import get_org_licence_summary
from apps.timeoff.models import HolidayCalendar, LeaveRequest, OnDutyRequest


@pytest.fixture
def seed_env(monkeypatch):
    monkeypatch.setenv('CONTROL_TOWER_EMAIL', 'control.tower@clarisal.com')
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

    def test_command_fails_without_org_admin_password_env_var(self, seed_env):
        seed_env.delenv('SEED_ORG_ADMIN_PASSWORD', raising=False)

        with pytest.raises(CommandError) as exc_info:
            call_command('seed_control_tower')

        assert 'SEED_ORG_ADMIN_PASSWORD environment variable is not set' in str(exc_info.value)

    def test_command_fails_without_employee_password_env_var(self, seed_env):
        seed_env.delenv('SEED_EMPLOYEE_PASSWORD', raising=False)

        with pytest.raises(CommandError) as exc_info:
            call_command('seed_control_tower')

        assert 'SEED_EMPLOYEE_PASSWORD environment variable is not set' in str(exc_info.value)

    def test_command_creates_exhaustive_seed_data(self, seed_env):
        call_command('seed_control_tower')

        assert Group.objects.filter(name='control_tower').exists()
        assert Group.objects.filter(name='org_admin').exists()
        assert Group.objects.filter(name='employee').exists()

        control_tower = User.objects.get(
            email='control.tower@clarisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        assert control_tower.account_type == AccountType.CONTROL_TOWER
        assert control_tower.role == UserRole.CONTROL_TOWER
        assert control_tower.is_superuser is True
        assert control_tower.is_staff is True
        assert control_tower.check_password('ControlTower@123')
        assert control_tower.groups.filter(name='control_tower').exists()

        primary_org = Organisation.objects.get(name='Northstar People Pvt Ltd')
        assert primary_org.licence_count == 10
        assert primary_org.pan_number == 'AACCN1234F'
        assert primary_org.status == OrganisationStatus.ACTIVE
        assert primary_org.billing_status == OrganisationBillingStatus.PAID
        assert primary_org.access_state == OrganisationAccessState.ACTIVE
        assert primary_org.onboarding_stage == OrganisationOnboardingStage.EMPLOYEES_INVITED

        primary_admin = User.objects.get(
            email='admin@northstarpeople.com',
            account_type=AccountType.WORKFORCE,
        )
        assert primary_org.primary_admin_user_id == primary_admin.id
        assert primary_admin.check_password('OrgAdmin@123')
        assert primary_admin.groups.filter(name='org_admin').exists()
        assert OrganisationMembership.objects.get(user=primary_admin, organisation=primary_org).status == OrganisationMembershipStatus.ACTIVE

        shared_admin = User.objects.get(
            email='control.tower@clarisal.com',
            account_type=AccountType.WORKFORCE,
        )
        assert shared_admin.check_password('ControlTower@123')
        assert shared_admin.groups.filter(name='org_admin').exists()
        assert shared_admin.employee_records.filter(organisation=primary_org, status=EmployeeStatus.ACTIVE).exists()
        assert shared_admin.organisation_memberships.filter(is_org_admin=True).count() == 3

        unpaid_org = Organisation.objects.get(name='Orbit Freight Pvt Ltd')
        suspended_org = Organisation.objects.get(name='Redwood Retail Pvt Ltd')
        expired_org = Organisation.objects.get(name='Zenith Field Services Pvt Ltd')
        assert unpaid_org.status == OrganisationStatus.PENDING
        assert suspended_org.status == OrganisationStatus.SUSPENDED
        assert expired_org.status == OrganisationStatus.ACTIVE
        assert get_org_licence_summary(expired_org)['active_paid_quantity'] == 0

        assert Organisation.objects.count() == 4
        assert OfficeLocation.objects.count() == 12
        assert Department.objects.count() == 7
        assert OrganisationMembership.objects.count() == 4
        assert Employee.objects.count() == 11
        assert Invitation.objects.count() == 6
        assert OnboardingDocumentType.objects.count() >= 30
        assert ApprovalWorkflow.objects.filter(organisation=primary_org).count() == 7
        assert LeaveRequest.objects.filter(employee__organisation=primary_org).count() == 5
        assert OnDutyRequest.objects.filter(employee__organisation=primary_org).count() == 4
        assert Notice.objects.filter(organisation=primary_org).count() == 3
        assert HolidayCalendar.objects.filter(organisation=primary_org).count() == 2

        seeded_employee = Employee.objects.select_related('user', 'profile').get(employee_code='EMP002')
        assert seeded_employee.user.account_type == AccountType.WORKFORCE
        assert seeded_employee.user.check_password('Employee@123')
        assert seeded_employee.profile.phone_personal == '+91 9988776655'
        assert seeded_employee.education_records.count() == 1
        assert seeded_employee.bank_accounts.filter(is_primary=True).count() == 1
        assert seeded_employee.government_ids.count() == 2
        assert seeded_employee.document_requests.filter(status='REJECTED').exists()
        assert seeded_employee.document_requests.filter(status='SUBMITTED').exists()

        onboarding_employee = Employee.objects.get(user__email='meera.singh@northstarpeople.com', organisation=primary_org)
        pending_employee = Employee.objects.get(user__email='karthik.verma@northstarpeople.com', organisation=primary_org)
        pending_invite_employee = Employee.objects.get(user__email='isha.kapoor@northstarpeople.com', organisation=primary_org)
        assert onboarding_employee.status == EmployeeStatus.INVITED
        assert pending_employee.status == EmployeeStatus.PENDING
        assert pending_invite_employee.status == EmployeeStatus.INVITED
        assert Invitation.objects.get(email='meera.singh@northstarpeople.com', organisation=primary_org).status == InvitationStatus.ACCEPTED
        assert Invitation.objects.get(email='isha.kapoor@northstarpeople.com', organisation=primary_org).status == InvitationStatus.PENDING
        assert Invitation.objects.get(email='admin@northstarpeople.com', organisation=primary_org).status in {
            InvitationStatus.PENDING,
            InvitationStatus.ACCEPTED,
        }
        assert Invitation.objects.get(email='former.candidate@northstarpeople.com', organisation=primary_org).status == InvitationStatus.REVOKED
        assert Invitation.objects.get(email='expired.candidate@northstarpeople.com', organisation=primary_org).status == InvitationStatus.EXPIRED

        assert Employee.objects.filter(organisation=primary_org, status=EmployeeStatus.ACTIVE).count() == 4
        assert Employee.objects.filter(organisation=primary_org, status=EmployeeStatus.PENDING).count() == 1
        assert Employee.objects.filter(organisation=primary_org, status=EmployeeStatus.RESIGNED).count() == 1
        assert Employee.objects.filter(organisation=primary_org, status=EmployeeStatus.RETIRED).count() == 1
        assert Employee.objects.filter(organisation=primary_org, status=EmployeeStatus.TERMINATED).count() == 1

        pan = seeded_employee.government_ids.get(id_type=GovernmentIdType.PAN)
        aadhaar = seeded_employee.government_ids.get(id_type=GovernmentIdType.AADHAAR)
        bank_account = seeded_employee.bank_accounts.get(is_primary=True)
        assert pan.masked_identifier
        assert aadhaar.masked_identifier
        assert bank_account.masked_account_number
        assert bank_account.account_number_encrypted != '123456789012'

        request_statuses = set(EmployeeDocumentRequest.objects.values_list('status', flat=True))
        assert {
            'REQUESTED',
            'SUBMITTED',
            'VERIFIED',
            'REJECTED',
            'WAIVED',
        }.issubset(request_statuses)

    def test_command_is_idempotent_for_exhaustive_seed(self, seed_env, capsys):
        call_command('seed_control_tower')
        first_primary_org = Organisation.objects.get(name='Northstar People Pvt Ltd')
        first_control_tower = User.objects.get(
            email='control.tower@clarisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        first_org_admin = User.objects.get(
            email='admin@northstarpeople.com',
            account_type=AccountType.WORKFORCE,
        )

        call_command('seed_control_tower')

        second_primary_org = Organisation.objects.get(name='Northstar People Pvt Ltd')
        second_control_tower = User.objects.get(
            email='control.tower@clarisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        second_org_admin = User.objects.get(
            email='admin@northstarpeople.com',
            account_type=AccountType.WORKFORCE,
        )

        assert second_primary_org.id == first_primary_org.id
        assert second_control_tower.id == first_control_tower.id
        assert second_org_admin.id == first_org_admin.id
        assert Organisation.objects.count() == 4
        assert OfficeLocation.objects.count() == 12
        assert Department.objects.count() == 7
        assert OrganisationMembership.objects.count() == 4
        assert Employee.objects.count() == 11
        assert Invitation.objects.count() == 6
        assert LeaveRequest.objects.count() == 5
        assert OnDutyRequest.objects.count() == 4
        assert ApprovalWorkflow.objects.count() == 7
        assert Notice.objects.count() == 3
        assert HolidayCalendar.objects.count() == 2

        output = capsys.readouterr().out
        assert 'Seed Credentials' in output
        assert 'password not shown' in output
        assert 'ControlTower@123' not in output
        assert 'OrgAdmin@123' not in output
        assert 'Employee@123' not in output
        assert 'already exists' in output

    def test_command_fails_when_seed_licences_are_below_exhaustive_employee_count(self, seed_env):
        seed_env.setenv('SEED_ORGANISATION_LICENCE_COUNT', '6')

        with pytest.raises(CommandError) as exc_info:
            call_command('seed_control_tower')

        assert 'must be at least 7' in str(exc_info.value)
        assert Group.objects.filter(name__in=['control_tower', 'org_admin', 'employee']).count() == 0
        assert User.objects.count() == 0
        assert Organisation.objects.count() == 0

    def test_command_uses_custom_control_tower_email_from_env(self, seed_env):
        seed_env.setenv('CONTROL_TOWER_EMAIL', 'platform-admin@clarisal.com')

        call_command('seed_control_tower')

        control_tower_user = User.objects.get(
            email='platform-admin@clarisal.com',
            account_type=AccountType.CONTROL_TOWER,
        )
        workforce_twin = User.objects.get(
            email='platform-admin@clarisal.com',
            account_type=AccountType.WORKFORCE,
        )
        assert control_tower_user.account_type == AccountType.CONTROL_TOWER
        assert control_tower_user.role == UserRole.CONTROL_TOWER
        assert workforce_twin.account_type == AccountType.WORKFORCE
        assert workforce_twin.organisation_memberships.filter(is_org_admin=True).count() == 3
