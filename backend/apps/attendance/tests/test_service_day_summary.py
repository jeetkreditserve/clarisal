from datetime import date, time
from decimal import Decimal

import pytest

from apps.attendance.models import (
    AttendanceDayStatus,
    AttendancePunch,
    AttendancePunchActionType,
    AttendancePunchSource,
    AttendanceRecord,
    AttendanceRecordSource,
)
from apps.attendance.services import (
    _make_aware_datetime,
    _pick_interval_from_punches,
    _summarize_day,
    assign_shift,
    create_shift,
    get_default_attendance_policy,
    recalculate_attendance_day,
)
from apps.timeoff.models import DaySession, HolidayCalendar, HolidayCalendarStatus, LeaveRequest, LeaveRequestStatus
from apps.timeoff.tests.test_services import _create_employee, _create_leave_type, _create_organisation


def _add_punch(employee, attendance_date, clock_time, action_type):
    return AttendancePunch.objects.create(
        organisation=employee.organisation,
        employee=employee,
        punch_at=_make_aware_datetime(attendance_date, clock_time),
        action_type=action_type,
        source=AttendancePunchSource.WEB,
    )


@pytest.mark.django_db
def test_pick_interval_prefers_explicit_check_in_and_check_out():
    organisation = _create_organisation('Attendance Punch Interval Org')
    employee = _create_employee(organisation, email='attendance-interval@test.com')
    attendance_date = date(2026, 4, 1)
    raw = _add_punch(employee, attendance_date, time(8, 55), AttendancePunchActionType.RAW)
    check_in = _add_punch(employee, attendance_date, time(9, 5), AttendancePunchActionType.CHECK_IN)
    check_out = _add_punch(employee, attendance_date, time(18, 2), AttendancePunchActionType.CHECK_OUT)

    resolved_check_in, resolved_check_out = _pick_interval_from_punches([raw, check_in, check_out])

    assert resolved_check_in == check_in.punch_at
    assert resolved_check_out == check_out.punch_at


@pytest.mark.django_db
def test_summarize_day_marks_holiday_without_punches():
    organisation = _create_organisation('Attendance Holiday Org')
    employee = _create_employee(organisation, email='attendance-holiday@test.com')
    calendar_obj = HolidayCalendar.objects.create(
        organisation=organisation,
        name='General Calendar',
        year=2026,
        status=HolidayCalendarStatus.PUBLISHED,
        is_default=True,
    )
    calendar_obj.holidays.create(
        name='Founders Day',
        holiday_date=date(2026, 5, 1),
        classification='PUBLIC',
        session=DaySession.FULL_DAY,
    )

    summary = _summarize_day(employee, date(2026, 5, 1))

    assert summary['status'] == AttendanceDayStatus.HOLIDAY
    assert summary['paid_fraction'] == Decimal('1.00')
    assert summary['metadata']['holiday_name'] == 'Founders Day'


@pytest.mark.django_db
def test_summarize_day_uses_manual_override_record():
    organisation = _create_organisation('Attendance Override Org')
    employee = _create_employee(organisation, email='attendance-override@test.com')
    attendance_date = date(2026, 5, 2)
    AttendanceRecord.objects.create(
        organisation=organisation,
        employee=employee,
        attendance_date=attendance_date,
        check_in_at=_make_aware_datetime(attendance_date, time(9, 0)),
        check_out_at=_make_aware_datetime(attendance_date, time(18, 0)),
        source=AttendanceRecordSource.MANUAL_OVERRIDE,
    )

    summary = _summarize_day(employee, attendance_date)

    assert summary['status'] == AttendanceDayStatus.PRESENT
    assert summary['source'] == AttendancePunchSource.MANUAL
    assert summary['metadata']['override_source'] == AttendanceRecordSource.MANUAL_OVERRIDE


@pytest.mark.django_db
def test_summarize_day_combines_half_day_leave_with_half_day_work():
    organisation = _create_organisation('Attendance Leave Mix Org')
    employee = _create_employee(organisation, email='attendance-leave-mix@test.com')
    attendance_date = date(2026, 5, 3)
    leave_type = _create_leave_type(organisation, code='HFL')
    LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=attendance_date,
        end_date=attendance_date,
        start_session=DaySession.FIRST_HALF,
        end_session=DaySession.FIRST_HALF,
        total_units=Decimal('0.50'),
        reason='Half day leave',
        status=LeaveRequestStatus.APPROVED,
    )
    _add_punch(employee, attendance_date, time(13, 0), AttendancePunchActionType.CHECK_IN)
    _add_punch(employee, attendance_date, time(18, 0), AttendancePunchActionType.CHECK_OUT)

    summary = _summarize_day(employee, attendance_date)

    assert summary['leave_fraction'] == Decimal('0.50')
    assert summary['status'] == AttendanceDayStatus.PRESENT
    assert summary['paid_fraction'] == Decimal('1.00')


@pytest.mark.django_db
def test_summarize_day_marks_incomplete_for_single_punch():
    organisation = _create_organisation('Attendance Incomplete Org')
    employee = _create_employee(organisation, email='attendance-incomplete@test.com')
    attendance_date = date(2026, 5, 4)
    _add_punch(employee, attendance_date, time(9, 10), AttendancePunchActionType.RAW)

    summary = _summarize_day(employee, attendance_date)

    assert summary['status'] == AttendanceDayStatus.INCOMPLETE
    assert summary['needs_regularization'] is True
    assert 'Only one punch' in summary['note']


@pytest.mark.django_db
def test_recalculate_attendance_day_updates_existing_summary_after_more_punches():
    organisation = _create_organisation('Attendance Recalc Org')
    employee = _create_employee(organisation, email='attendance-recalc@test.com')
    attendance_date = date(2026, 5, 5)
    _add_punch(employee, attendance_date, time(9, 0), AttendancePunchActionType.CHECK_IN)

    first_day = recalculate_attendance_day(employee, attendance_date)
    _add_punch(employee, attendance_date, time(18, 5), AttendancePunchActionType.CHECK_OUT)
    recalculated_day = recalculate_attendance_day(employee, attendance_date)

    assert first_day.status == AttendanceDayStatus.INCOMPLETE
    assert recalculated_day.status == AttendanceDayStatus.PRESENT
    assert recalculated_day.raw_punch_count == 2


@pytest.mark.django_db
def test_shift_assignment_and_overnight_window_feed_day_summary():
    organisation = _create_organisation('Attendance Overnight Org')
    employee = _create_employee(organisation, email='attendance-overnight@test.com')
    policy = get_default_attendance_policy(organisation)
    policy.default_start_time = time(9, 0)
    policy.default_end_time = time(18, 0)
    policy.save(update_fields=['default_start_time', 'default_end_time', 'modified_at'])
    overnight_shift = create_shift(
        organisation,
        name='Night Shift',
        start_time=time(22, 0),
        end_time=time(6, 0),
        is_overnight=True,
        full_day_min_minutes=420,
        half_day_min_minutes=210,
    )
    assign_shift(employee, overnight_shift, start_date=date(2026, 5, 6))
    _add_punch(employee, date(2026, 5, 6), time(22, 5), AttendancePunchActionType.CHECK_IN)
    AttendancePunch.objects.create(
        organisation=organisation,
        employee=employee,
        punch_at=_make_aware_datetime(date(2026, 5, 7), time(6, 0)),
        action_type=AttendancePunchActionType.CHECK_OUT,
        source=AttendancePunchSource.WEB,
    )

    summary = _summarize_day(employee, date(2026, 5, 6))

    assert summary['shift'] == overnight_shift
    assert summary['status'] == AttendanceDayStatus.PRESENT
    assert summary['worked_minutes'] >= 475
