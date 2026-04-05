from datetime import datetime, time

import pytest

from apps.attendance.models import AttendanceDayStatus
from apps.attendance.services import calculate_attendance_day_status

SHIFT_START = time(9, 0)
FULL_DAY_MINUTES = 480
HALF_DAY_MINUTES = 240
GRACE_PERIOD_MINUTES = 15


def make_punches(checkin_dt, checkout_dt=None):
    punches = [{'punch_time': checkin_dt, 'direction': 'IN'}]
    if checkout_dt is not None:
        punches.append({'punch_time': checkout_dt, 'direction': 'OUT'})
    return punches


@pytest.mark.django_db
class TestAttendanceDailyCalculation:
    def test_present_when_worked_minutes_gte_full_day(self):
        result = calculate_attendance_day_status(
            make_punches(
                checkin_dt=datetime(2026, 4, 1, 9, 0),
                checkout_dt=datetime(2026, 4, 1, 18, 0),
            ),
            shift_start=SHIFT_START,
        )

        assert result['status'] == AttendanceDayStatus.PRESENT

    def test_half_day_when_worked_between_half_and_full(self):
        result = calculate_attendance_day_status(
            make_punches(
                checkin_dt=datetime(2026, 4, 1, 9, 0),
                checkout_dt=datetime(2026, 4, 1, 13, 0),
            ),
            shift_start=SHIFT_START,
        )

        assert result['status'] == AttendanceDayStatus.HALF_DAY

    def test_absent_when_worked_below_half_day(self):
        result = calculate_attendance_day_status(
            make_punches(
                checkin_dt=datetime(2026, 4, 1, 9, 0),
                checkout_dt=datetime(2026, 4, 1, 11, 0),
            ),
            shift_start=SHIFT_START,
        )

        assert result['status'] == AttendanceDayStatus.ABSENT

    def test_incomplete_when_checkin_has_no_checkout(self):
        result = calculate_attendance_day_status(
            make_punches(checkin_dt=datetime(2026, 4, 1, 9, 0)),
            shift_start=SHIFT_START,
        )

        assert result['status'] == AttendanceDayStatus.INCOMPLETE

    def test_late_mark_triggered_beyond_grace_period(self):
        result = calculate_attendance_day_status(
            make_punches(
                checkin_dt=datetime(2026, 4, 1, 9, 20),
                checkout_dt=datetime(2026, 4, 1, 18, 0),
            ),
            shift_start=SHIFT_START,
            grace_minutes=GRACE_PERIOD_MINUTES,
        )

        assert result['is_late'] is True

    def test_not_late_within_grace_period(self):
        result = calculate_attendance_day_status(
            make_punches(
                checkin_dt=datetime(2026, 4, 1, 9, 10),
                checkout_dt=datetime(2026, 4, 1, 18, 0),
            ),
            shift_start=SHIFT_START,
            grace_minutes=GRACE_PERIOD_MINUTES,
        )

        assert result['is_late'] is False

    def test_no_punches_returns_absent(self):
        result = calculate_attendance_day_status([], shift_start=SHIFT_START)

        assert result['status'] == AttendanceDayStatus.ABSENT

    def test_overtime_minutes_calculated(self):
        result = calculate_attendance_day_status(
            make_punches(
                checkin_dt=datetime(2026, 4, 1, 9, 0),
                checkout_dt=datetime(2026, 4, 1, 19, 0),
            ),
            shift_start=SHIFT_START,
            full_day_minutes=FULL_DAY_MINUTES,
        )

        assert result['overtime_minutes'] == 120

    def test_on_leave_override_sets_on_leave_status(self):
        result = calculate_attendance_day_status(
            [],
            shift_start=SHIFT_START,
            leave_override='ON_LEAVE',
        )

        assert result['status'] == AttendanceDayStatus.ON_LEAVE
