from datetime import date

import pytest
from django.core.management import call_command

from apps.accounts.models import AccountType, User, UserRole
from apps.departments.models import Department
from apps.employees.models import Employee, EmployeeStatus
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
from ..services import has_permission, mask_serializer_data, scope_employee_queryset, summarize_effective_scopes


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct-access@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(
        name='Access Org',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
        country_code='IN',
        currency='INR',
    )


@pytest.fixture
def org_owner_user(organisation, ct_user):
    user = User.objects.create_user(
        email='owner@test.com',
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
def department(organisation):
    return Department.objects.create(organisation=organisation, name='People')


@pytest.fixture
def location_hq(organisation):
    return OfficeLocation.objects.create(organisation=organisation, name='HQ')


@pytest.fixture
def location_remote(organisation):
    return OfficeLocation.objects.create(organisation=organisation, name='Remote')


@pytest.mark.django_db
def test_sync_access_control_seeds_roles_permissions_and_backfills_assignments(ct_user, organisation, org_owner_user):
    call_command('sync_access_control')

    assert AccessPermission.objects.filter(code='org.access_control.manage').exists()
    assert AccessRole.objects.filter(code='CT_SUPER_ADMIN').exists()
    assert AccessRole.objects.filter(code='ORG_OWNER').exists()
    assert AccessRoleAssignment.objects.filter(user=ct_user, role__code='CT_SUPER_ADMIN').exists()
    assert AccessRoleAssignment.objects.filter(
        user=org_owner_user,
        organisation=organisation,
        role__code='ORG_OWNER',
    ).exists()


@pytest.mark.django_db
def test_has_permission_reads_seeded_org_owner(org_owner_user, organisation):
    call_command('sync_access_control')

    assert has_permission(org_owner_user, 'org.access_control.manage', organisation=organisation) is True
    assert has_permission(org_owner_user, 'org.reports.export', organisation=organisation) is True

    scope_summary = summarize_effective_scopes(org_owner_user, organisation=organisation)
    assert {'kind': DataScopeKind.ALL_EMPLOYEES, 'label': 'All employees'} in scope_summary


@pytest.mark.django_db
def test_scope_employee_queryset_limits_results_to_selected_office_location(
    organisation,
    ct_user,
    location_hq,
    location_remote,
):
    call_command('sync_access_control')
    restricted_admin = User.objects.create_user(
        email='scoped@test.com',
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
    reader_role = AccessRole.objects.create(
        code='ORG_EMPLOYEE_READER',
        scope='ORGANISATION',
        name='Employee Reader',
        is_system=False,
    )
    AccessRolePermission.objects.create(
        role=reader_role,
        permission=AccessPermission.objects.get(code='org.employees.read'),
    )
    assignment = AccessRoleAssignment.objects.create(
        user=restricted_admin,
        organisation=organisation,
        role=reader_role,
    )
    AccessScope.objects.create(
        assignment=assignment,
        scope_kind=DataScopeKind.SELECTED_OFFICE_LOCATIONS,
        office_location=location_hq,
    )

    hq_user = User.objects.create_user(
        email='hq@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
    )
    remote_user = User.objects.create_user(
        email='remote@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
    )
    hq_employee = Employee.objects.create(
        organisation=organisation,
        user=hq_user,
        employee_code='E001',
        office_location=location_hq,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
    )
    Employee.objects.create(
        organisation=organisation,
        user=remote_user,
        employee_code='E002',
        office_location=location_remote,
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2024, 1, 1),
    )

    queryset = scope_employee_queryset(
        Employee.objects.filter(organisation=organisation),
        restricted_admin,
        organisation=organisation,
    )

    assert list(queryset) == [hq_employee]


@pytest.mark.django_db
def test_mask_serializer_data_hides_sensitive_fields_without_permission(organisation, ct_user):
    call_command('sync_access_control')
    restricted_admin = User.objects.create_user(
        email='masked@test.com',
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
    manager_role = AccessRole.objects.get(code='ORG_MANAGER')
    AccessRoleAssignment.objects.create(
        user=restricted_admin,
        organisation=organisation,
        role=manager_role,
    )

    masked = mask_serializer_data(
        {
            'profile': {'date_of_birth': '1991-02-03'},
            'government_ids': [{'identifier': 'ABCDE1234F'}],  # pragma: allowlist secret
            'bank_accounts': [{'account_number': 'XXXX'}],
            'full_name': 'Masked User',
        },
        {
            'profile': 'org.employee_sensitive.read',
            'government_ids': 'org.employee_sensitive.read',
            'bank_accounts': 'org.employee_sensitive.read',
        },
        restricted_admin,
        organisation=organisation,
    )

    assert masked['profile'] is None
    assert masked['government_ids'] == []
    assert masked['bank_accounts'] == []
    assert masked['full_name'] == 'Masked User'
