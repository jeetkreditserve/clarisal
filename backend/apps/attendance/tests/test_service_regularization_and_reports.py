from datetime import date, time
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.attendance.models import (
    AttendanceDayStatus,
    AttendanceRecord,
    AttendanceRecordSource,
    AttendanceRegularizationRequest,
    AttendanceRegularizationStatus,
)
from apps.attendance.services import (
    _make_aware_datetime,
    _month_window,
    apply_regularization_status_change,
    create_regularization_request,
    get_employee_attendance_calendar,
    get_employee_attendance_history,
    get_employee_attendance_summary,
    get_org_attendance_dashboard,
    get_org_attendance_report,
    get_payroll_attendance_summary,
    list_attendance_regularizations_for_org,
    list_org_attendance_days,
    upsert_attendance_override,
    withdraw_regularization_request,
)
from apps.employees.models import Employee, EmployeeStatus
from apps.timeoff.tests.test_services import _create_employee, _create_organisation


def _create_regularization_workflow(organisation):
    approver_user = User.objects.create_user(
        email=f'attendance-approver-{organisation.id}@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    approver_employee = Employee.objects.create(
        organisation=organisation,
        user=approver_user,
        employee_code='ATAPR',
        designation='Attendance Approver',
        status=EmployeeStatus.ACTIVE,
    )
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Attendance Regularization Workflow',
        is_default=True,
        default_request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        is_active=True,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=workflow,
        name='Attendance Rule',
        request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
        priority=100,
        is_active=True,
    )
    stage = ApprovalStage.objects.create(workflow=workflow, name='Review', sequence=1)
    ApprovalStageApprover.objects.create(
        stage=stage,
        approver_type=ApprovalApproverType.SPECIFIC_EMPLOYEE,
        approver_employee=approver_employee,
    )
    return workflow


@pytest.mark.django_db
def test_month_window_history_calendar_and_summary_use_requested_month(monkeypatch):
    organisation = _create_organisation('Attendance Summary Org')
    employee = _create_employee(organisation, email='attendance-summary@test.com')
    monkeypatch.setattr('apps.attendance.services._policy_local_date', lambda policy, dt=None: date(2026, 5, 20))

    upsert_attendance_override(
        employee,
        date(2026, 5, 2),
        check_in_at=_make_aware_datetime(date(2026, 5, 2), time(9, 5)),
        check_out_at=_make_aware_datetime(date(2026, 5, 2), time(18, 0)),
        source=AttendanceRecordSource.MANUAL_OVERRIDE,
    )
    for day_number in range(1, 7):
        AttendanceRegularizationRequest.objects.create(
            organisation=organisation,
            employee=employee,
            attendance_date=date(2026, 5, day_number),
            reason=f'Pending request {day_number}',
            status=AttendanceRegularizationStatus.PENDING,
        )

    start_date, end_date = _month_window(None, policy=employee.organisation.attendance_policies.first())
    history = get_employee_attendance_history(employee, month='2026-05')
    calendar = get_employee_attendance_calendar(employee, month='2026-05')
    summary = get_employee_attendance_summary(employee)

    assert start_date == date(2026, 5, 1)
    assert end_date == date(2026, 5, 31)
    assert len(history) == 31
    assert calendar['month'] == '2026-05'
    assert next(day for day in calendar['days'] if day['date'] == '2026-05-02')['status'] == AttendanceDayStatus.PRESENT
    assert len(summary['pending_regularizations']) == 5


@pytest.mark.django_db
def test_create_and_withdraw_regularization_request_preserves_withdrawn_status():
    organisation = _create_organisation('Attendance Withdraw Org')
    employee = _create_employee(organisation, email='attendance-withdraw@test.com')
    _create_regularization_workflow(organisation)

    regularization = create_regularization_request(
        employee,
        attendance_date=date(2026, 5, 10),
        requested_check_in_at=_make_aware_datetime(date(2026, 5, 10), time(9, 10)),
        reason='Missed punch',
        actor=employee.user,
    )

    with pytest.raises(ValueError, match='pending regularization request already exists'):
        create_regularization_request(
            employee,
            attendance_date=date(2026, 5, 10),
            requested_check_out_at=_make_aware_datetime(date(2026, 5, 10), time(18, 5)),
            reason='Duplicate request',
            actor=employee.user,
        )

    withdraw_regularization_request(regularization, actor=employee.user)
    regularization.refresh_from_db()
    regularization.approval_run.refresh_from_db()

    assert regularization.status == AttendanceRegularizationStatus.WITHDRAWN
    assert regularization.approval_run.status == ApprovalRunStatus.CANCELLED


@pytest.mark.django_db
def test_apply_regularization_status_change_approved_creates_override_record():
    organisation = _create_organisation('Attendance Approval Org')
    employee = _create_employee(organisation, email='attendance-approval@test.com')
    regularization = AttendanceRegularizationRequest.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=date(2026, 5, 12),
        requested_check_in_at=_make_aware_datetime(date(2026, 5, 12), time(9, 0)),
        requested_check_out_at=_make_aware_datetime(date(2026, 5, 12), time(18, 0)),
        reason='Late sync',
        status=AttendanceRegularizationStatus.PENDING,
    )

    apply_regularization_status_change(regularization, AttendanceRegularizationStatus.APPROVED)

    record = AttendanceRecord.objects.get(employee=employee, attendance_date=date(2026, 5, 12))

    assert record.source == AttendanceRecordSource.REGULARIZATION
    assert regularization.status == AttendanceRegularizationStatus.APPROVED
    assert employee.attendance_days.get(attendance_date=date(2026, 5, 12)).note == 'Approved attendance regularization applied.'


@pytest.mark.django_db
def test_org_dashboard_lists_reports_and_payroll_summary_aggregate_days():
    organisation = _create_organisation('Attendance Dashboard Org')
    employee_one = _create_employee(organisation, email='dash-one@test.com')
    employee_two = _create_employee(organisation, email='dash-two@test.com')
    target_date = date(2026, 5, 15)

    upsert_attendance_override(
        employee_one,
        target_date,
        check_in_at=_make_aware_datetime(target_date, time(9, 0)),
        check_out_at=_make_aware_datetime(target_date, time(18, 0)),
        source=AttendanceRecordSource.MANUAL_OVERRIDE,
    )
    AttendanceRegularizationRequest.objects.create(
        organisation=organisation,
        employee=employee_two,
        attendance_date=target_date,
        reason='Pending approval',
        status=AttendanceRegularizationStatus.PENDING,
    )

    dashboard = get_org_attendance_dashboard(organisation, target_date=target_date)
    present_days = list_org_attendance_days(organisation, target_date=target_date, status_value=AttendanceDayStatus.PRESENT)
    payroll_summary = get_payroll_attendance_summary(employee_one, period_start=target_date, period_end=target_date)

    assert dashboard['present_count'] == 1
    assert dashboard['absent_count'] == 1
    assert dashboard['pending_regularizations'] == 1
    assert len(present_days) == 1
    assert present_days[0].employee == employee_one
    assert payroll_summary['paid_days'] == 1
    assert payroll_summary['lop_days'] == Decimal('0.00')


@pytest.mark.django_db
def test_org_report_and_regularization_listing_validate_inputs_and_filters():
    organisation = _create_organisation('Attendance Report Org')
    employee = _create_employee(organisation, email='attendance-report@test.com')
    target_date = date(2026, 5, 16)

    upsert_attendance_override(
        employee,
        target_date,
        check_in_at=_make_aware_datetime(target_date, time(9, 35)),
        check_out_at=_make_aware_datetime(target_date, time(18, 0)),
        source=AttendanceRecordSource.MANUAL_OVERRIDE,
    )
    pending_request = AttendanceRegularizationRequest.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=target_date,
        reason='Pending review',
        status=AttendanceRegularizationStatus.PENDING,
    )
    AttendanceRegularizationRequest.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=date(2026, 5, 17),
        reason='Resolved review',
        status=AttendanceRegularizationStatus.APPROVED,
    )

    with pytest.raises(ValueError, match='month must use YYYY-MM format'):
        get_org_attendance_report(organisation, month='2026/05')

    report = get_org_attendance_report(organisation, month='2026-05')
    pending_only = list_attendance_regularizations_for_org(
        organisation,
        status_value=AttendanceRegularizationStatus.PENDING,
    )

    assert report['month'] == '2026-05'
    assert report['employee_count'] == 1
    assert report['late_marks'] >= 1
    assert len(report['rows']) >= 1
    assert list(pending_only) == [pending_request]
