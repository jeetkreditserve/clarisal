from __future__ import annotations

from apps.attendance.models import AttendanceDay, AttendanceDayStatus
from apps.employees.models import Employee, EmployeeStatus

from .base import BaseReport


class AttendanceSummaryReport(BaseReport):
    title = 'Attendance Summary'
    columns = ['Employee Name', 'Employee Code', 'Department', 'Present Days', 'Half Days', 'Absent Days', 'On Leave Days', 'Late Marks']

    def __init__(self, *, organisation, month: int, year: int):
        self.organisation = organisation
        self.month = month
        self.year = year

    def generate_rows(self):
        employees = (
            Employee.objects.filter(organisation=self.organisation, status=EmployeeStatus.ACTIVE)
            .select_related('user', 'department')
            .order_by('employee_code', 'created_at')
        )
        rows = []
        for employee in employees:
            days = AttendanceDay.objects.filter(
                organisation=self.organisation,
                employee=employee,
                attendance_date__year=self.year,
                attendance_date__month=self.month,
            )
            rows.append(
                {
                    'Employee Name': employee.user.full_name,
                    'Employee Code': employee.employee_code or '',
                    'Department': employee.department.name if employee.department else '',
                    'Present Days': days.filter(status=AttendanceDayStatus.PRESENT).count(),
                    'Half Days': days.filter(status=AttendanceDayStatus.HALF_DAY).count(),
                    'Absent Days': days.filter(status=AttendanceDayStatus.ABSENT).count(),
                    'On Leave Days': days.filter(status=AttendanceDayStatus.ON_LEAVE).count(),
                    'Late Marks': days.filter(is_late=True).count(),
                }
            )
        return rows
