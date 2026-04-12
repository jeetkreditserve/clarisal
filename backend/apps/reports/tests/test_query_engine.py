from datetime import date

import pytest
from django.core.management import call_command

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
from apps.payroll.models import PayrollRun, PayrollRunItem


@pytest.fixture
def report_builder_setup(db):
    organisation = Organisation.objects.create(
        name='Report Builder Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='report-builder@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
        first_name='Report',
        last_name='Admin',
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
            email='report-employee@test.com',
            password='pass123!',  # pragma: allowlist secret
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=organisation,
            is_active=True,
            first_name='Asha',
            last_name='Patel',
        ),
        employee_code='EMP900',
        designation='Engineer',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 1, 1),
    )
    return organisation, user


@pytest.mark.django_db
def test_preview_report_uses_seeded_field_catalog(report_builder_setup):
    from apps.reports.models import ReportDataset, ReportTemplate
    from apps.reports.query_engine import preview_report
    from apps.reports.services import sync_report_catalog

    organisation, user = report_builder_setup
    sync_report_catalog()
    template = ReportTemplate.objects.create(
        organisation=organisation,
        dataset=ReportDataset.objects.get(code='employees'),
        name='Active employees',
        owner=user,
        columns=['employee.employee_number', 'employee.full_name'],
        filters=[{'field': 'employee.status', 'operator': 'eq', 'value': 'ACTIVE'}],
    )

    result = preview_report(template, user, organisation)

    assert result['columns'][0]['code'] == 'employee.employee_number'
    assert result['rows'] == [{'employee.employee_number': 'EMP900', 'employee.full_name': 'Asha Patel'}]


@pytest.mark.django_db
def test_query_engine_rejects_unknown_field(report_builder_setup):
    from apps.reports.models import ReportDataset, ReportTemplate
    from apps.reports.query_engine import ReportValidationError, preview_report
    from apps.reports.services import sync_report_catalog

    organisation, user = report_builder_setup
    sync_report_catalog()
    template = ReportTemplate.objects.create(
        organisation=organisation,
        dataset=ReportDataset.objects.get(code='employees'),
        name='Unsafe employees',
        owner=user,
        columns=['employee.employee_number', 'employee.password_hash'],
    )

    with pytest.raises(ReportValidationError, match='Unknown report field'):
        preview_report(template, user, organisation)


@pytest.mark.django_db
def test_payroll_dataset_requires_payroll_permission(report_builder_setup):
    from apps.reports.models import ReportDataset, ReportTemplate
    from apps.reports.query_engine import ReportValidationError, preview_report
    from apps.reports.services import sync_report_catalog

    organisation, _ = report_builder_setup
    call_command('sync_access_control')
    sync_report_catalog()

    reports_reader = User.objects.create_user(
        email='reports-reader@test.com',
        password='pass123!',  # pragma: allowlist secret
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
        first_name='Rhea',
        last_name='Reader',
    )
    OrganisationMembership.objects.create(
        user=reports_reader,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    read_only_role = AccessRole.objects.create(
        code='ORG_REPORTS_READ_ONLY',
        scope='ORGANISATION',
        name='Reports Reader',
        organisation=organisation,
        is_system=False,
    )
    AccessRolePermission.objects.create(
        role=read_only_role,
        permission=AccessPermission.objects.get(code='org.reports.read'),
    )
    AccessRoleAssignment.objects.create(
        user=reports_reader,
        organisation=organisation,
        role=read_only_role,
    )

    pay_run = PayrollRun.objects.create(
        organisation=organisation,
        name='April 2026 Payroll',
        period_month=4,
        period_year=2026,
        status='FINALIZED',
    )
    employee = Employee.objects.get(organisation=organisation)
    PayrollRunItem.objects.create(
        pay_run=pay_run,
        employee=employee,
        gross_pay='60000.00',
        net_pay='52000.00',
        total_deductions='8000.00',
    )

    template = ReportTemplate.objects.create(
        organisation=organisation,
        dataset=ReportDataset.objects.get(code='payroll_runs'),
        name='Payroll employee list',
        owner=reports_reader,
        columns=['employee.employee_number'],
    )

    with pytest.raises(ReportValidationError, match='Missing permission for dataset: payroll_runs'):
        preview_report(template, reports_reader, organisation)
