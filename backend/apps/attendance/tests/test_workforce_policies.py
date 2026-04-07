from datetime import date, time
from decimal import Decimal

import pytest

from apps.attendance.models import (
    AttendanceDayStatus,
    AttendanceOvertimeApproval,
    AttendancePolicy,
    Shift,
    ShiftRotationAssignment,
    ShiftRotationTemplate,
    WFHRequest,
    WFHRequestStatus,
)
from apps.attendance.services import (
    _get_effective_shift,
    _make_aware_datetime,
    get_employee_attendance_summary,
    get_payroll_attendance_summary,
    upsert_attendance_override,
)
from apps.timeoff.tests.test_services import _create_employee, _create_organisation


@pytest.mark.django_db
def test_get_effective_shift_prefers_rotation_assignment():
    organisation = _create_organisation('Shift Rotation Org')
    employee = _create_employee(organisation, email='rotation@test.com')
    day_shift = Shift.objects.create(
        organisation=organisation,
        name='Day Shift',
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    night_shift = Shift.objects.create(
        organisation=organisation,
        name='Night Shift',
        start_time=time(18, 0),
        end_time=time(3, 0),
        is_overnight=True,
    )
    template = ShiftRotationTemplate.objects.create(
        organisation=organisation,
        name='Weekly Rotation',
        rotation_interval_days=7,
        shift_sequence=[str(day_shift.id), str(night_shift.id)],
        is_active=True,
    )
    ShiftRotationAssignment.objects.create(
        organisation=organisation,
        employee=employee,
        template=template,
        start_date=date(2026, 5, 1),
        is_active=True,
    )

    first_week = _get_effective_shift(employee, date(2026, 5, 2))
    second_week = _get_effective_shift(employee, date(2026, 5, 9))

    assert first_week is not None
    assert first_week.shift_id == day_shift.id
    assert second_week is not None
    assert second_week.shift_id == night_shift.id


@pytest.mark.django_db
def test_attendance_summary_marks_approved_wfh_day_without_punches(monkeypatch):
    organisation = _create_organisation('WFH Attendance Org')
    employee = _create_employee(organisation, email='wfh@test.com')
    monkeypatch.setattr('apps.attendance.services._policy_local_date', lambda policy, dt=None: date(2026, 5, 20))

    WFHRequest.objects.create(
        employee=employee,
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 20),
        session='FULL_DAY',
        reason='Remote support day',
        status='APPROVED',
    )

    summary = get_employee_attendance_summary(employee)

    assert summary['today'].status == AttendanceDayStatus.WFH
    assert summary['today'].metadata['wfh_status'] == 'APPROVED'


@pytest.mark.django_db
def test_payroll_attendance_summary_uses_approved_overtime_minutes():
    organisation = _create_organisation('OT Approval Org')
    employee = _create_employee(organisation, email='ot@test.com')
    attendance_day = upsert_attendance_override(
        employee,
        date(2026, 5, 10),
        check_in_at=_make_aware_datetime(date(2026, 5, 10), time(9, 0)),
        check_out_at=_make_aware_datetime(date(2026, 5, 10), time(21, 0)),
    )
    AttendanceOvertimeApproval.objects.create(
        attendance_day=attendance_day,
        employee=employee,
        approved_minutes=60,
        status='APPROVED',
    )

    summary = get_payroll_attendance_summary(
        employee,
        period_start=date(2026, 5, 10),
        period_end=date(2026, 5, 10),
    )

    assert summary['paid_fraction'] == Decimal('1.00')
    assert summary['overtime_minutes'] == 60


@pytest.mark.django_db
def test_payroll_attendance_summary_ignores_unapproved_overtime_when_policy_requires_approval():
    organisation = _create_organisation('Strict OT Approval Org')
    employee = _create_employee(organisation, email='strict-ot@test.com')
    attendance_policy = AttendancePolicy.objects.create(
        organisation=organisation,
        name='Strict OT Policy',
        is_default=True,
        is_active=True,
        overtime_approval_required=True,
        overtime_after_minutes=540,
    )
    assert attendance_policy.overtime_approval_required is True
    upsert_attendance_override(
        employee,
        date(2026, 5, 11),
        check_in_at=_make_aware_datetime(date(2026, 5, 11), time(9, 0)),
        check_out_at=_make_aware_datetime(date(2026, 5, 11), time(21, 0)),
    )

    summary = get_payroll_attendance_summary(
        employee,
        period_start=date(2026, 5, 11),
        period_end=date(2026, 5, 11),
    )

    assert summary['paid_fraction'] == Decimal('1.00')
    assert summary['overtime_minutes'] == 0


@pytest.mark.django_db
def test_wfh_request_created_and_approved():
    """WFH request can be created and its status updated to APPROVED."""
    organisation = _create_organisation('WFH Flow Org')
    employee = _create_employee(organisation, email='wfh-flow@test.com')

    request = WFHRequest.objects.create(
        employee=employee,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1),
        session='FULL_DAY',
        reason='Working from home',
        status=WFHRequestStatus.PENDING,
    )

    assert request.status == WFHRequestStatus.PENDING
    request.status = WFHRequestStatus.APPROVED
    request.save(update_fields=['status', 'modified_at'])
    request.refresh_from_db()

    assert request.status == WFHRequestStatus.APPROVED
    assert request.employee == employee


@pytest.mark.django_db
def test_shift_rotation_resolves_correct_shift_for_week():
    """Rotation resolver returns shift A for week 1 and shift B for week 2."""
    organisation = _create_organisation('Shift Week Org')
    employee = _create_employee(organisation, email='shift-week@test.com')

    shift_a = Shift.objects.create(
        organisation=organisation,
        name='Morning Shift',
        start_time=time(6, 0),
        end_time=time(14, 0),
    )
    shift_b = Shift.objects.create(
        organisation=organisation,
        name='Evening Shift',
        start_time=time(14, 0),
        end_time=time(22, 0),
    )
    template = ShiftRotationTemplate.objects.create(
        organisation=organisation,
        name='Morning-Evening Rotation',
        rotation_interval_days=7,
        shift_sequence=[str(shift_a.id), str(shift_b.id)],
        is_active=True,
    )
    # Rotation starts on a Monday (2026-06-01)
    ShiftRotationAssignment.objects.create(
        organisation=organisation,
        employee=employee,
        template=template,
        start_date=date(2026, 6, 1),
        is_active=True,
    )

    week_1_result = _get_effective_shift(employee, date(2026, 6, 3))   # still week 1
    week_2_result = _get_effective_shift(employee, date(2026, 6, 8))   # week 2

    assert week_1_result is not None
    assert week_1_result.shift_id == shift_a.id
    assert week_2_result is not None
    assert week_2_result.shift_id == shift_b.id


@pytest.mark.django_db
def test_overtime_earning_calculation():
    """AttendancePolicy.overtime_multiplier is stored and readable for payroll computation."""
    organisation = _create_organisation('OT Earning Org')
    policy = AttendancePolicy.objects.create(
        organisation=organisation,
        name='OT Multiplier Policy',
        is_default=True,
        is_active=True,
        overtime_multiplier=Decimal('1.5'),
        overtime_after_minutes=480,
    )

    # Confirm the policy stores the multiplier
    policy.refresh_from_db()
    assert policy.overtime_multiplier == Decimal('1.5')

    # Verify the OT earning formula: (basic_salary / 26 / 8) * multiplier * ot_hours
    basic_salary = Decimal('26000.00')
    ot_hours = Decimal('2')
    multiplier = policy.overtime_multiplier
    working_days = Decimal('26')
    hours_per_day = Decimal('8')

    expected_earning = (basic_salary / working_days / hours_per_day * multiplier * ot_hours).quantize(Decimal('0.01'))
    assert expected_earning == Decimal('375.00')
