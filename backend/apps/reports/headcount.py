from __future__ import annotations

from datetime import date

from apps.employees.models import Employee, EmployeeStatus

from .base import BaseReport


class HeadcountReport(BaseReport):
    title = 'Headcount by Department'
    columns = ['Department', 'Location', 'Active Employees', 'On Probation']

    def __init__(self, *, organisation):
        self.organisation = organisation

    def generate_rows(self):
        employees = (
            Employee.objects.filter(organisation=self.organisation, status=EmployeeStatus.ACTIVE)
            .select_related('department', 'office_location')
            .order_by('department__name', 'office_location__name', 'employee_code')
        )
        grouped = {}
        today = date.today()
        for employee in employees:
            key = (
                employee.department.name if employee.department else 'Unassigned',
                employee.office_location.name if employee.office_location else 'Unassigned',
            )
            bucket = grouped.setdefault(key, {'active': 0, 'probation': 0})
            bucket['active'] += 1
            if employee.probation_end_date and employee.probation_end_date >= today:
                bucket['probation'] += 1

        return [
            {
                'Department': department,
                'Location': location,
                'Active Employees': counts['active'],
                'On Probation': counts['probation'],
            }
            for (department, location), counts in grouped.items()
        ]


class AttritionReport(BaseReport):
    title = 'Attrition Report'
    columns = ['Employee Name', 'Department', 'Last Working Day', 'Exit Type', 'Reason']

    def __init__(self, *, organisation, start_date=None, end_date=None):
        self.organisation = organisation
        self.start_date = start_date
        self.end_date = end_date

    def generate_rows(self):
        queryset = Employee.objects.filter(
            organisation=self.organisation,
            status__in=[EmployeeStatus.RESIGNED, EmployeeStatus.RETIRED, EmployeeStatus.TERMINATED],
        ).select_related('user', 'department')
        if self.start_date is not None:
            queryset = queryset.filter(date_of_exit__gte=self.start_date)
        if self.end_date is not None:
            queryset = queryset.filter(date_of_exit__lte=self.end_date)

        rows = []
        for employee in queryset.order_by('-date_of_exit', 'employee_code'):
            process = employee.offboarding_process if hasattr(employee, 'offboarding_process') else None
            rows.append(
                {
                    'Employee Name': employee.user.full_name,
                    'Department': employee.department.name if employee.department else '',
                    'Last Working Day': str(employee.date_of_exit or ''),
                    'Exit Type': employee.status,
                    'Reason': process.exit_reason if process else '',
                }
            )
        return rows
