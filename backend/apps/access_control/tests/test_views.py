from datetime import date

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import (
    Employee,
    EmployeeBankAccount,
    EmployeeGovernmentId,
    EmployeeProfile,
    EmployeeStatus,
    GovernmentIdType,
)
from apps.locations.models import OfficeLocation
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)

from ..models import (
    AccessPermission,
    AccessRole,
    AccessRoleAssignment,
    AccessRolePermission,
    AccessScope,
    DataScopeKind,
)
from ..services import has_permission, summarize_effective_scopes


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct-view@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(
        name='Access View Org',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
        country_code='IN',
        currency='INR',
        admin_setup_completed_at=date(2026, 4, 1),
    )


@pytest.fixture
def org_owner_user(organisation, ct_user):
    user = User.objects.create_user(
        email='owner-view@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    return user


@pytest.fixture
def location_hq(organisation):
    return OfficeLocation.objects.create(organisation=organisation, name='HQ')


@pytest.fixture
def location_remote(organisation):
    return OfficeLocation.objects.create(organisation=organisation, name='Remote')


@pytest.mark.django_db
def test_auth_me_includes_effective_permissions_and_scopes(api_client, organisation, org_owner_user):
    call_command('sync_access_control')
    api_client.force_authenticate(user=org_owner_user)

    response = api_client.get('/api/v1/auth/me/')

    assert response.status_code == 200
    assert 'org.access_control.manage' in response.data['effective_permissions']
    assert {'kind': 'ALL_EMPLOYEES', 'label': 'All employees'} in response.data['effective_scopes']


@pytest.mark.django_db
def test_org_report_view_denies_explicit_org_admin_without_report_permission(api_client, organisation, ct_user):
    call_command('sync_access_control')
    restricted_admin = User.objects.create_user(
        email='restricted-view@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=restricted_admin,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    people_only_role = AccessRole.objects.create(
        code='ORG_PEOPLE_ONLY',
        scope='ORGANISATION',
        name='People Only',
        is_system=False,
    )
    AccessRolePermission.objects.create(
        role=people_only_role,
        permission=AccessPermission.objects.get(code='org.employees.read'),
    )
    AccessRoleAssignment.objects.create(
        user=restricted_admin,
        organisation=organisation,
        role=people_only_role,
    )
    api_client.force_authenticate(user=restricted_admin)

    response = api_client.get('/api/v1/org/reports/headcount/')

    assert response.status_code == 403


@pytest.mark.django_db
def test_org_report_view_allows_seeded_org_owner(api_client, organisation, org_owner_user):
    call_command('sync_access_control')
    api_client.force_authenticate(user=org_owner_user)

    response = api_client.get('/api/v1/org/reports/headcount/')

    assert response.status_code == 200


@pytest.mark.django_db
def test_org_payroll_summary_denies_admin_without_payroll_permission(api_client, organisation, ct_user):
    call_command('sync_access_control')
    restricted_admin = User.objects.create_user(
        email='restricted-payroll@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=restricted_admin,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    people_only_role = AccessRole.objects.create(
        code='ORG_PEOPLE_READER',
        scope='ORGANISATION',
        name='People Reader',
        is_system=False,
    )
    AccessRolePermission.objects.create(
        role=people_only_role,
        permission=AccessPermission.objects.get(code='org.employees.read'),
    )
    AccessRoleAssignment.objects.create(
        user=restricted_admin,
        organisation=organisation,
        role=people_only_role,
    )
    api_client.force_authenticate(user=restricted_admin)

    response = api_client.get('/api/v1/org/payroll/summary/')

    assert response.status_code == 403


@pytest.mark.django_db
def test_org_employee_endpoints_scope_results_and_mask_sensitive_fields(
    api_client,
    organisation,
    ct_user,
    location_hq,
    location_remote,
):
    call_command('sync_access_control')
    restricted_admin = User.objects.create_user(
        email='restricted-employees@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=restricted_admin,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    assignment = AccessRoleAssignment.objects.create(
        user=restricted_admin,
        organisation=organisation,
        role=AccessRole.objects.get(code='ORG_MANAGER'),
    )
    AccessScope.objects.create(
        assignment=assignment,
        scope_kind=DataScopeKind.SELECTED_OFFICE_LOCATIONS,
        office_location=location_hq,
    )

    hq_user = User.objects.create_user(
        email='hq-view@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
    )
    remote_user = User.objects.create_user(
        email='remote-view@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
    )
    hq_employee = Employee.objects.create(
        organisation=organisation,
        user=hq_user,
        employee_code='E200',
        office_location=location_hq,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
    )
    remote_employee = Employee.objects.create(
        organisation=organisation,
        user=remote_user,
        employee_code='E201',
        office_location=location_remote,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
    )
    EmployeeProfile.objects.create(employee=hq_employee, date_of_birth=date(1991, 2, 3))
    EmployeeGovernmentId.objects.create(
        employee=hq_employee,
        id_type=GovernmentIdType.PAN,
        masked_identifier='ABCDE1234F',  # pragma: allowlist secret
    )
    EmployeeBankAccount.objects.create(
        employee=hq_employee,
        account_holder_name='HQ View',
        masked_account_number='XXXX4321',
        masked_ifsc='HDFC0001234',
        is_primary=True,
    )
    api_client.force_authenticate(user=restricted_admin)

    list_response = api_client.get('/api/v1/org/employees/')
    detail_response = api_client.get(f'/api/v1/org/employees/{hq_employee.id}/')
    out_of_scope_response = api_client.get(f'/api/v1/org/employees/{remote_employee.id}/')

    assert list_response.status_code == 200
    assert list_response.data['count'] == 1
    assert [result['employee_code'] for result in list_response.data['results']] == ['E200']
    assert detail_response.status_code == 200
    assert detail_response.data['profile'] is None
    assert detail_response.data['government_ids'] == []
    assert detail_response.data['bank_accounts'] == []
    assert out_of_scope_response.status_code == 404


@pytest.mark.django_db
def test_org_access_control_overview_and_create_scoped_assignment(
    api_client,
    organisation,
    org_owner_user,
    ct_user,
    location_hq,
):
    call_command('sync_access_control')
    scoped_admin = User.objects.create_user(
        email='payroll-admin@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=scoped_admin,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    api_client.force_authenticate(user=org_owner_user)

    overview_response = api_client.get('/api/v1/org/access-control/')
    create_response = api_client.post(
        '/api/v1/org/access-control/assignments/',
        {
            'user_id': str(scoped_admin.id),
            'role_code': 'ORG_PAYROLL_ADMIN',
            'is_active': True,
            'scopes': [
                {
                    'scope_kind': 'SELECTED_OFFICE_LOCATIONS',
                    'office_location_id': str(location_hq.id),
                }
            ],
        },
        format='json',
    )

    assert overview_response.status_code == 200
    assert any(role['code'] == 'ORG_PAYROLL_ADMIN' for role in overview_response.data['roles'])
    assert create_response.status_code == 201
    assert create_response.data['role_code'] == 'ORG_PAYROLL_ADMIN'
    assert len(create_response.data['scopes']) == 1
    assert create_response.data['scopes'][0]['scope_kind'] == 'SELECTED_OFFICE_LOCATIONS'
    assert create_response.data['scopes'][0]['label'] == 'HQ'
    assert str(create_response.data['scopes'][0]['office_location_id']) == str(location_hq.id)
    assert has_permission(scoped_admin, 'org.payroll.read', organisation=organisation) is True
    assert {'kind': 'SELECTED_OFFICE_LOCATIONS', 'label': 'HQ'} in summarize_effective_scopes(
        scoped_admin,
        organisation=organisation,
    )


@pytest.mark.django_db
def test_org_owner_can_create_custom_role_and_assign_it(
    api_client,
    organisation,
    org_owner_user,
    ct_user,
    location_hq,
):
    call_command('sync_access_control')
    scoped_admin = User.objects.create_user(
        email='custom-payroll-reader@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=scoped_admin,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    api_client.force_authenticate(user=org_owner_user)

    role_response = api_client.post(
        '/api/v1/org/access-control/roles/',
        {
            'name': 'Custom Payroll Reader',
            'description': 'Can read payroll for a selected office.',
            'permission_codes': ['org.employees.read', 'org.payroll.read'],
        },
        format='json',
    )
    assignment_response = api_client.post(
        '/api/v1/org/access-control/assignments/',
        {
            'user_id': str(scoped_admin.id),
            'role_code': role_response.data.get('code'),
            'is_active': True,
            'scopes': [
                {
                    'scope_kind': 'SELECTED_OFFICE_LOCATIONS',
                    'office_location_id': str(location_hq.id),
                }
            ],
        },
        format='json',
    )

    assert role_response.status_code == 201
    assert role_response.data['scope'] == 'ORGANISATION'
    assert role_response.data['is_system'] is False
    assert role_response.data['permissions'] == ['org.employees.read', 'org.payroll.read']
    assert assignment_response.status_code == 201
    assert assignment_response.data['role_code'] == role_response.data['code']
    assert has_permission(scoped_admin, 'org.payroll.read', organisation=organisation) is True


@pytest.mark.django_db
def test_ct_access_control_overview_uses_ct_permission(
    api_client,
    ct_user,
):
    call_command('sync_access_control')
    api_client.force_authenticate(user=ct_user)

    response = api_client.get('/api/v1/ct/access-control/')

    assert response.status_code == 200
    assert any(role['code'] == 'CT_SUPER_ADMIN' for role in response.data['roles'])
    assert any(permission['code'] == 'ct.organisations.read' for permission in response.data['permissions'])


@pytest.mark.django_db
def test_ct_user_can_create_custom_role_and_assign_it(api_client, ct_user):
    call_command('sync_access_control')
    support_user = User.objects.create_user(
        email='ct-support@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.CONTROL_TOWER,
        account_type=AccountType.CONTROL_TOWER,
        is_active=True,
    )
    api_client.force_authenticate(user=ct_user)

    role_response = api_client.post(
        '/api/v1/ct/access-control/roles/',
        {
            'name': 'CT Billing Operations',
            'description': 'Billing-focused Control Tower access.',
            'permission_codes': ['ct.billing.read', 'ct.billing.write'],
        },
        format='json',
    )
    assignment_response = api_client.post(
        '/api/v1/ct/access-control/assignments/',
        {
            'user_id': str(support_user.id),
            'role_code': role_response.data.get('code'),
            'is_active': True,
            'scopes': [],
        },
        format='json',
    )
    overview_response = api_client.get('/api/v1/ct/access-control/')

    assert role_response.status_code == 201
    assert role_response.data['scope'] == 'CONTROL_TOWER'
    assert role_response.data['permissions'] == ['ct.billing.read', 'ct.billing.write']
    assert assignment_response.status_code == 201
    assert assignment_response.data['role_code'] == role_response.data['code']
    assert has_permission(support_user, 'ct.billing.write') is True
    assert any(assignment['user_email'] == 'ct-support@test.com' for assignment in overview_response.data['assignments'])


@pytest.mark.django_db
def test_org_access_control_simulation_returns_effective_permissions_scopes_and_employee_access(
    api_client,
    organisation,
    org_owner_user,
    ct_user,
    location_hq,
    location_remote,
):
    call_command('sync_access_control')
    manager_user = User.objects.create_user(
        email='manager-sim@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        account_type=AccountType.WORKFORCE,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=manager_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
        invited_by=ct_user,
    )
    assignment = AccessRoleAssignment.objects.create(
        user=manager_user,
        organisation=organisation,
        role=AccessRole.objects.get(code='ORG_MANAGER'),
    )
    AccessScope.objects.create(
        assignment=assignment,
        scope_kind=DataScopeKind.SELECTED_OFFICE_LOCATIONS,
        office_location=location_hq,
    )
    hq_user = User.objects.create_user(
        email='hq-sim@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
    )
    remote_user = User.objects.create_user(
        email='remote-sim@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
    )
    hq_employee = Employee.objects.create(
        organisation=organisation,
        user=hq_user,
        employee_code='E210',
        office_location=location_hq,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
    )
    remote_employee = Employee.objects.create(
        organisation=organisation,
        user=remote_user,
        employee_code='E211',
        office_location=location_remote,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
    )
    api_client.force_authenticate(user=org_owner_user)

    allowed_response = api_client.post(
        '/api/v1/org/access-control/simulate/',
        {
            'user_id': str(manager_user.id),
            'employee_id': str(hq_employee.id),
        },
        format='json',
    )
    denied_response = api_client.post(
        '/api/v1/org/access-control/simulate/',
        {
            'user_id': str(manager_user.id),
            'employee_id': str(remote_employee.id),
        },
        format='json',
    )

    assert allowed_response.status_code == 200
    assert 'org.employees.read' in allowed_response.data['effective_permissions']
    assert {'kind': 'SELECTED_OFFICE_LOCATIONS', 'label': 'HQ'} in allowed_response.data['effective_scopes']
    assert allowed_response.data['employee_access'] == {'employee_id': str(hq_employee.id), 'allowed': True}
    assert denied_response.status_code == 200
    assert denied_response.data['employee_access'] == {'employee_id': str(remote_employee.id), 'allowed': False}
