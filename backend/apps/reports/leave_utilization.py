from __future__ import annotations

from decimal import Decimal

from apps.employees.models import Employee, EmployeeStatus
from apps.timeoff.models import LeaveBalance, LeaveType

from .base import BaseReport


class LeaveUtilizationReport(BaseReport):
    title = 'Leave Utilization'
    columns = ['Employee Name', 'Leave Type', 'Accrued', 'Used', 'Pending', 'Available']

    def __init__(self, *, organisation):
        self.organisation = organisation

    def generate_rows(self):
        employees = (
            Employee.objects.filter(organisation=self.organisation, status=EmployeeStatus.ACTIVE)
            .select_related('user')
            .order_by('employee_code', 'created_at')
        )
        leave_types = (
            LeaveType.objects.filter(leave_plan__organisation=self.organisation, is_active=True)
            .select_related('leave_plan')
            .order_by('name')
        )
        rows = []
        for employee in employees:
            for leave_type in leave_types:
                balance = LeaveBalance.objects.filter(employee=employee, leave_type=leave_type).order_by('-cycle_end', '-created_at').first()
                opening = balance.opening_balance if balance else Decimal('0.00')
                carried = balance.carried_forward_amount if balance else Decimal('0.00')
                credited = balance.credited_amount if balance else Decimal('0.00')
                used = balance.used_amount if balance else Decimal('0.00')
                pending = balance.pending_amount if balance else Decimal('0.00')
                accrued = opening + carried + credited
                available = accrued - used - pending
                rows.append(
                    {
                        'Employee Name': employee.user.full_name,
                        'Leave Type': leave_type.name,
                        'Accrued': f'{accrued:.2f}',
                        'Used': f'{used:.2f}',
                        'Pending': f'{pending:.2f}',
                        'Available': f'{available:.2f}',
                    }
                )
        return rows
