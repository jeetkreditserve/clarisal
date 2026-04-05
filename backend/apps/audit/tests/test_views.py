import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.audit.models import AuditLog
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


@pytest.fixture
def audit_setup(db):
    ct_user = User.objects.create_superuser(
        email='ct-audit@test.com',
        password='pass123!',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )
    organisation = Organisation.objects.create(
        name='Audit Safe Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
        created_by=ct_user,
    )
    org_admin = User.objects.create_user(
        email='org-admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        organisation=organisation,
        user=org_admin,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    employee_user = User.objects.create_user(
        email='employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP-AUD-001',
        designation='Analyst',
        status=EmployeeStatus.ACTIVE,
    )

    ct_client = APIClient()
    ct_client.force_authenticate(user=ct_user)

    org_admin_client = APIClient()
    org_admin_client.force_authenticate(user=org_admin)
    session = org_admin_client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()

    return {
        'ct_user': ct_user,
        'organisation': organisation,
        'org_admin': org_admin,
        'ct_client': ct_client,
        'org_admin_client': org_admin_client,
    }


@pytest.mark.django_db
class TestAuditLogViews:
    def test_control_tower_view_redacts_historical_sensitive_payloads(self, audit_setup):
        AuditLog.objects.create(
            actor=audit_setup['org_admin'],
            organisation=audit_setup['organisation'],
            action='employee.profile.updated',
            payload={
                'status': 'ACTIVE',
                'pan_number': 'ABCDE1234F',
                'aadhaar_identifier': '123412341234',
                'address_line1': '123 Secret Street',
                'gross_pay': '98000.00',
                'monthly_amount': '45000.00',
                'nested': {
                    'ifsc': 'HDFC0001234',
                },
            },
        )

        response = audit_setup['ct_client'].get(f"/api/ct/audit/?organisation_id={audit_setup['organisation'].id}")

        assert response.status_code == 200
        payload = response.data['results'][0]['payload']
        assert payload['status'] == 'ACTIVE'
        assert payload['pan_number'] == '[REDACTED]'
        assert payload['aadhaar_identifier'] == '[REDACTED]'
        assert payload['address_line1'] == '[REDACTED]'
        assert payload['gross_pay'] == '[REDACTED]'
        assert payload['monthly_amount'] == '[REDACTED]'
        assert payload['nested']['ifsc'] == '[REDACTED]'
        assert 'ABCDE1234F' not in response.data['results'][0]['payload_summary']
        assert '123 Secret Street' not in response.data['results'][0]['payload_summary']

    def test_org_admin_view_redacts_historical_sensitive_payloads(self, audit_setup):
        AuditLog.objects.create(
            actor=audit_setup['org_admin'],
            organisation=audit_setup['organisation'],
            action='organisation.updated',
            payload={
                'country_code': 'IN',
                'pan_number': 'ABCDE1234F',
                'phone_personal': '+919999999999',
                'net_pay': '82000.00',
            },
        )

        response = audit_setup['org_admin_client'].get('/api/org/audit/')

        assert response.status_code == 200
        payload = response.data['results'][0]['payload']
        assert payload['country_code'] == 'IN'
        assert payload['pan_number'] == '[REDACTED]'
        assert payload['phone_personal'] == '[REDACTED]'
        assert payload['net_pay'] == '[REDACTED]'

    def test_control_tower_view_masks_employee_actor_identity_and_device_metadata(self, audit_setup):
        employee_actor = User.objects.create_user(
            email='employee-actor@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=audit_setup['organisation'],
            is_active=True,
            first_name='Hidden',
            last_name='Employee',
        )
        AuditLog.objects.create(
            actor=employee_actor,
            organisation=audit_setup['organisation'],
            action='attendance.punch.recorded',
            payload={'action_type': 'CHECK_IN'},
            ip_address='10.0.0.14',
            user_agent='Mozilla/5.0 Test Agent',
        )

        response = audit_setup['ct_client'].get(f"/api/ct/audit/?organisation_id={audit_setup['organisation'].id}")

        assert response.status_code == 200
        entry = response.data['results'][0]
        assert entry['actor_name'] == 'Employee user'
        assert entry['actor_email'] is None
        assert entry['ip_address'] is None
        assert entry['user_agent'] is None

    def test_org_admin_view_keeps_actor_identity_visible_for_org_troubleshooting(self, audit_setup):
        AuditLog.objects.create(
            actor=audit_setup['org_admin'],
            organisation=audit_setup['organisation'],
            action='organisation.updated',
            payload={'country_code': 'IN'},
            ip_address='10.0.0.16',
            user_agent='Mozilla/5.0 Admin Agent',
        )

        response = audit_setup['org_admin_client'].get('/api/org/audit/')

        assert response.status_code == 200
        entry = response.data['results'][0]
        assert entry['actor_name'] == audit_setup['org_admin'].full_name
        assert entry['actor_email'] == audit_setup['org_admin'].email
        assert entry['ip_address'] == '10.0.0.16'
        assert entry['user_agent'] == 'Mozilla/5.0 Admin Agent'
