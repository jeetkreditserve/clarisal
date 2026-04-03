from __future__ import annotations

from apps.payroll.models import PayrollRunItem

from .base import BaseReport


def _snapshot_component_amount(snapshot, component_code):
    for line in snapshot.get('lines', []):
        if line.get('component_code') == component_code:
            return str(line.get('monthly_amount', '0'))
    return '0'


class PayrollRegisterReport(BaseReport):
    title = 'Payroll Register'
    columns = [
        'Employee Code',
        'Employee Name',
        'Department',
        'Location',
        'Gross Pay',
        'Total Deductions',
        'Net Pay',
        'PF Employee',
        'ESI Employee',
        'Professional Tax',
        'TDS',
    ]

    def __init__(self, *, organisation, pay_run_id: str):
        self.organisation = organisation
        self.pay_run_id = pay_run_id

    def generate_rows(self):
        items = (
            PayrollRunItem.objects.filter(pay_run__organisation=self.organisation, pay_run_id=self.pay_run_id)
            .select_related('employee__user', 'employee__department', 'employee__office_location')
            .order_by('employee__employee_code', 'created_at')
        )
        rows = []
        for item in items:
            snapshot = item.snapshot or {}
            rows.append(
                {
                    'Employee Code': item.employee.employee_code or '',
                    'Employee Name': item.employee.user.full_name,
                    'Department': item.employee.department.name if item.employee.department else '',
                    'Location': item.employee.office_location.name if item.employee.office_location else '',
                    'Gross Pay': str(item.gross_pay or 0),
                    'Total Deductions': str(item.total_deductions or 0),
                    'Net Pay': str(item.net_pay or 0),
                    'PF Employee': _snapshot_component_amount(snapshot, 'PF_EMPLOYEE'),
                    'ESI Employee': _snapshot_component_amount(snapshot, 'ESI_EMPLOYEE'),
                    'Professional Tax': str(snapshot.get('professional_tax') or _snapshot_component_amount(snapshot, 'PROFESSIONAL_TAX')),
                    'TDS': str(snapshot.get('tds_monthly') or item.income_tax or 0),
                }
            )
        return rows
