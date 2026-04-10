from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.attendance.models import AttendanceDay, AttendanceDayStatus
from apps.departments.models import Department
from apps.employees.models import Employee, EmployeeOffboardingProcess, EmployeeStatus, OffboardingProcessStatus
from apps.locations.models import OfficeLocation
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.payroll.models import PayrollRun, PayrollRunItem, PayrollRunStatus
from apps.timeoff.models import (
    CarryForwardMode,
    LeaveBalance,
    LeaveCycle,
    LeaveCycleType,
    LeavePlan,
    LeaveType,
)


@pytest.fixture
def reports_setup(db):
    organisation = Organisation.objects.create(
        name='Reports Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    org_admin_user = User.objects.create_user(
        email='reports-admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=org_admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )

    department = Department.objects.create(organisation=organisation, name='Engineering')
    location = OfficeLocation.objects.create(
        organisation=organisation,
        name='Ahmedabad HQ',
        address='SG Highway',
        city='Ahmedabad',
        state='Gujarat',
        country='India',
        pincode='380015',
        is_active=True,
    )

    employee_user = User.objects.create_user(
        email='reports-employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
        first_name='Asha',
        last_name='Patel',
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP500',
        designation='Engineer',
        department=department,
        office_location=location,
        status=EmployeeStatus.ACTIVE,
        probation_end_date=date(2026, 12, 31),
        date_of_joining=date(2025, 4, 1),
    )

    second_employee_user = User.objects.create_user(
        email='reports-employee-2@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
        first_name='Dev',
        last_name='Shah',
    )
    second_employee = Employee.objects.create(
        organisation=organisation,
        user=second_employee_user,
        employee_code='EMP501',
        designation='Analyst',
        department=department,
        office_location=location,
        status=EmployeeStatus.ACTIVE,
        probation_end_date=None,
        date_of_joining=date(2025, 6, 1),
    )

    exited_user = User.objects.create_user(
        email='reports-exit@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
        first_name='Nina',
        last_name='Rao',
    )
    exited_employee = Employee.objects.create(
        organisation=organisation,
        user=exited_user,
        employee_code='EMP599',
        designation='Designer',
        department=department,
        office_location=location,
        status=EmployeeStatus.RESIGNED,
        date_of_joining=date(2024, 1, 1),
        date_of_exit=date(2026, 4, 15),
    )
    EmployeeOffboardingProcess.objects.create(
        organisation=organisation,
        employee=exited_employee,
        initiated_by=org_admin_user,
        status=OffboardingProcessStatus.COMPLETED,
        exit_status=EmployeeStatus.RESIGNED,
        date_of_exit=date(2026, 4, 15),
        exit_reason='Higher studies',
    )

    leave_cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='FY Cycle',
        cycle_type=LeaveCycleType.FINANCIAL_YEAR,
        is_default=True,
        is_active=True,
    )
    leave_plan = LeavePlan.objects.create(
        organisation=organisation,
        leave_cycle=leave_cycle,
        name='Default Leave Plan',
        is_default=True,
        is_active=True,
    )
    leave_type = LeaveType.objects.create(
        leave_plan=leave_plan,
        code='AL',
        name='Annual Leave',
        annual_entitlement=Decimal('12.00'),
        carry_forward_mode=CarryForwardMode.CAPPED,
        carry_forward_cap=Decimal('5.00'),
        is_active=True,
    )
    LeaveBalance.objects.create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=date(2026, 4, 1),
        cycle_end=date(2027, 3, 31),
        opening_balance=Decimal('1.00'),
        carried_forward_amount=Decimal('2.00'),
        credited_amount=Decimal('12.00'),
        used_amount=Decimal('3.00'),
        pending_amount=Decimal('1.00'),
    )

    pay_run = PayrollRun.objects.create(
        organisation=organisation,
        name='April 2026 Payroll',
        period_year=2026,
        period_month=4,
        status=PayrollRunStatus.FINALIZED,
    )
    for current_employee, gross, net in (
        (employee, Decimal('50000.00'), Decimal('43000.00')),
        (second_employee, Decimal('60000.00'), Decimal('52000.00')),
    ):
        PayrollRunItem.objects.create(
            pay_run=pay_run,
            employee=current_employee,
            status='READY',
            gross_pay=gross,
            total_deductions=(gross - net),
            employee_deductions=Decimal('2000.00'),
            employer_contributions=Decimal('2500.00'),
            income_tax=Decimal('5000.00'),
            net_pay=net,
            snapshot={
                'professional_tax': '200.00',
                'tds_monthly': '5000.00',
                'lines': [
                    {'component_code': 'PF_EMPLOYEE', 'monthly_amount': '1800.00'},
                    {'component_code': 'PF_EMPLOYER', 'monthly_amount': '1800.00'},
                    {'component_code': 'ESI_EMPLOYEE', 'monthly_amount': '0.00'},
                    {'component_code': 'ESI_EMPLOYER', 'monthly_amount': '0.00'},
                    {'component_code': 'PROFESSIONAL_TAX', 'monthly_amount': '200.00'},
                ],
            },
        )

    AttendanceDay.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=date(2026, 4, 1),
        status=AttendanceDayStatus.PRESENT,
        is_late=True,
    )
    AttendanceDay.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=date(2026, 4, 2),
        status=AttendanceDayStatus.HALF_DAY,
    )
    AttendanceDay.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=date(2026, 4, 3),
        status=AttendanceDayStatus.ON_LEAVE,
    )
    AttendanceDay.objects.create(
        organisation=organisation,
        employee=second_employee,
        attendance_date=date(2026, 4, 1),
        status=AttendanceDayStatus.ABSENT,
    )

    client = APIClient()
    client.force_authenticate(user=org_admin_user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()

    return {
        'organisation': organisation,
        'client': client,
        'department': department,
        'location': location,
        'employee': employee,
        'second_employee': second_employee,
        'exited_employee': exited_employee,
        'leave_type': leave_type,
        'pay_run': pay_run,
    }


@pytest.mark.django_db
def test_payroll_register_report_includes_all_rows_and_statutory_fields(reports_setup):
    from apps.reports.payroll_register import PayrollRegisterReport

    report = PayrollRegisterReport(organisation=reports_setup['organisation'], pay_run_id=str(reports_setup['pay_run'].id))
    data = report.to_json()

    assert len(data['rows']) == 2
    assert data['rows'][0]['Employee Code'] == 'EMP500'
    assert data['rows'][0]['Professional Tax'] == '200.00'
    assert 'PF Employee' in data['rows'][0]


@pytest.mark.django_db
def test_headcount_attrition_leave_attendance_and_tax_reports_use_current_models(reports_setup):
    from apps.reports.attendance_summary import AttendanceSummaryReport
    from apps.reports.headcount import AttritionReport, HeadcountReport
    from apps.reports.leave_utilization import LeaveUtilizationReport
    from apps.reports.tax_summary import TaxSummaryReport

    headcount_rows = HeadcountReport(organisation=reports_setup['organisation']).generate_rows()
    attrition_rows = AttritionReport(
        organisation=reports_setup['organisation'],
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    ).generate_rows()
    leave_rows = LeaveUtilizationReport(organisation=reports_setup['organisation']).generate_rows()
    attendance_rows = AttendanceSummaryReport(organisation=reports_setup['organisation'], month=4, year=2026).generate_rows()
    tax_rows = TaxSummaryReport(organisation=reports_setup['organisation'], fiscal_year='2026-2027').generate_rows()

    assert headcount_rows[0]['Active Employees'] == 2
    assert headcount_rows[0]['On Probation'] == 1
    assert attrition_rows[0]['Reason'] == 'Higher studies'
    assert leave_rows[0]['Available'] == '11.00'
    assert attendance_rows[0]['Late Marks'] == 1
    assert tax_rows[0]['TDS Monthly'] == '5000.00'


@pytest.mark.django_db
def test_org_report_view_dispatches_json_and_xlsx_downloads(reports_setup):
    client = reports_setup['client']

    json_response = client.get('/api/v1/org/reports/headcount/')
    xlsx_response = client.get('/api/v1/org/reports/headcount/', {'file_format': 'xlsx'})

    assert json_response.status_code == 200
    assert json_response.data['title'] == 'Headcount by Department'
    assert xlsx_response.status_code == 200
    assert xlsx_response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
