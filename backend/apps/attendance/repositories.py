from __future__ import annotations

from datetime import date

from .models import AttendanceDay, AttendanceDayStatus, AttendancePunch


def get_attendance_day(employee_id, attendance_date: date):
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        attendance_date=attendance_date,
    ).first()


def get_attendance_days_in_range(employee_id, start_date: date, end_date: date):
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    ).order_by('attendance_date')


def count_present_days(employee_id, start_date: date, end_date: date) -> int:
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
        status__in=[AttendanceDayStatus.PRESENT, AttendanceDayStatus.HALF_DAY],
    ).count()


def count_absent_days(employee_id, start_date: date, end_date: date) -> int:
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
        status=AttendanceDayStatus.ABSENT,
    ).count()


def get_punches_for_day(employee_id, attendance_date: date):
    return AttendancePunch.objects.filter(
        employee_id=employee_id,
        punch_at__date=attendance_date,
    ).order_by('punch_at')
