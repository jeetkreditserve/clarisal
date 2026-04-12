from datetime import date

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.access_control.models import AccessPermission, AccessRole, AccessRoleAssignment, AccessRolePermission
from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


def build_org_admin_client(user, organisation):
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()
    return client


@pytest.fixture
def report_builder_client(db):
    organisation = Organisation.objects.create(
        name='Report Builder API Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='report-api-admin@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    Employee.objects.create(
        organisation=organisation,
        user=User.objects.create_user(
            email='report-api-employee@test.com',
            password='pass123!',  # pragma: allowlist secret
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=organisation,
            is_active=True,
            first_name='Dev',
            last_name='Shah',
        ),
        employee_code='EMP901',
        designation='Analyst',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 2, 1),
    )
    return build_org_admin_client(user, organisation), organisation


@pytest.fixture
def report_builder_no_export_client(db):
    call_command('sync_access_control')
    organisation = Organisation.objects.create(
        name='Report Reader Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='report-api-reader@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    reader_role = AccessRole.objects.create(
        code='ORG_REPORTS_BUILDER_NO_EXPORT',
        scope='ORGANISATION',
        organisation=organisation,
        name='Reports Builder Without Export',
        is_system=False,
    )
    for permission_code in ('org.reports.read', 'org.reports.builder.manage'):
        AccessRolePermission.objects.create(
            role=reader_role,
            permission=AccessPermission.objects.get(code=permission_code),
        )
    AccessRoleAssignment.objects.create(
        user=user,
        organisation=organisation,
        role=reader_role,
    )
    Employee.objects.create(
        organisation=organisation,
        user=User.objects.create_user(
            email='report-reader-employee@test.com',
            password='pass123!',  # pragma: allowlist secret
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=organisation,
            is_active=True,
            first_name='Ira',
            last_name='Vora',
        ),
        employee_code='EMP902',
        designation='Analyst',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 2, 1),
    )
    return build_org_admin_client(user, organisation), organisation


@pytest.mark.django_db
def test_report_builder_catalog_create_and_preview(report_builder_client):
    from apps.reports.services import sync_report_catalog

    client, _ = report_builder_client
    sync_report_catalog()

    datasets_response = client.get('/api/v1/org/reports/datasets/')
    create_response = client.post(
        '/api/v1/org/reports/templates/',
        {
            'dataset_code': 'employees',
            'name': 'Active employee list',
            'description': '',
            'status': 'DEPLOYED',
            'columns': ['employee.employee_number', 'employee.full_name'],
            'filters': [{'field': 'employee.status', 'operator': 'eq', 'value': 'ACTIVE'}],
        },
        format='json',
    )
    preview_response = client.post(
        '/api/v1/org/reports/templates/preview-draft/',
        {
            'dataset_code': 'employees',
            'name': 'Preview',
            'columns': ['employee.employee_number', 'employee.full_name'],
            'filters': [{'field': 'employee.status', 'operator': 'eq', 'value': 'ACTIVE'}],
        },
        format='json',
    )

    assert datasets_response.status_code == 200
    assert {dataset['code'] for dataset in datasets_response.data} >= {'employees', 'payroll_runs', 'leave_requests'}
    assert create_response.status_code == 201
    assert create_response.data['name'] == 'Active employee list'
    assert preview_response.status_code == 200
    assert preview_response.data['rows'][0]['employee.employee_number'] == 'EMP901'


@pytest.mark.django_db
def test_report_run_listing_detail_and_export_download(report_builder_client):
    from apps.reports.services import sync_report_catalog

    client, _ = report_builder_client
    sync_report_catalog()
    template_response = client.post(
        '/api/v1/org/reports/templates/',
        {
            'dataset_code': 'employees',
            'name': 'Exportable employee list',
            'description': '',
            'status': 'DEPLOYED',
            'columns': ['employee.employee_number', 'employee.full_name'],
            'filters': [{'field': 'employee.status', 'operator': 'eq', 'value': 'ACTIVE'}],
        },
        format='json',
    )
    template_id = template_response.data['id']

    run_response = client.post(
        f'/api/v1/org/reports/templates/{template_id}/run/',
        {'file_format': 'csv'},
        format='json',
    )

    assert run_response.status_code == 201
    assert run_response.data['status'] == 'SUCCEEDED'
    assert len(run_response.data['exports']) == 1

    run_id = run_response.data['id']
    export_id = run_response.data['exports'][0]['id']
    list_response = client.get('/api/v1/org/reports/runs/')
    detail_response = client.get(f'/api/v1/org/reports/runs/{run_id}/')
    export_response = client.get(f'/api/v1/org/reports/runs/{run_id}/exports/{export_id}/')

    assert list_response.status_code == 200
    assert list_response.data[0]['id'] == run_id
    assert detail_response.status_code == 200
    assert detail_response.data['template_name'] == 'Exportable employee list'
    assert detail_response.data['requested_by_email'] == 'report-api-admin@test.com'
    assert export_response.status_code == 200
    assert export_response['Content-Type'] == 'text/csv'


@pytest.mark.django_db
def test_report_run_requires_export_permission_for_downloadable_formats(report_builder_no_export_client):
    from apps.reports.services import sync_report_catalog

    client, _ = report_builder_no_export_client
    sync_report_catalog()
    template_response = client.post(
        '/api/v1/org/reports/templates/',
        {
            'dataset_code': 'employees',
            'name': 'Read only employee list',
            'description': '',
            'status': 'DRAFT',
            'columns': ['employee.employee_number'],
            'filters': [{'field': 'employee.status', 'operator': 'eq', 'value': 'ACTIVE'}],
        },
        format='json',
    )

    assert template_response.status_code == 201

    run_response = client.post(
        f"/api/v1/org/reports/templates/{template_response.data['id']}/run/",
        {'file_format': 'csv'},
        format='json',
    )

    assert run_response.status_code == 403
