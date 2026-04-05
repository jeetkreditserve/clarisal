from __future__ import annotations

from apps.payroll.models import PayrollRunItem, PayrollRunStatus

from .base import BaseReport
from .payroll_register import _snapshot_component_amount


class TaxSummaryReport(BaseReport):
    title = 'Tax Summary'
    columns = ['Employee Name', 'Employee Code', 'Month', 'Year', 'Professional Tax', 'TDS Monthly', 'PF Employee', 'PF Employer', 'ESI Employee', 'ESI Employer']

    def __init__(self, *, organisation, fiscal_year: str):
        self.organisation = organisation
        self.fiscal_year = fiscal_year

    def _get_fiscal_months(self):
        start_year = int(self.fiscal_year.split('-')[0])
        return [(month, start_year) for month in range(4, 13)] + [(month, start_year + 1) for month in range(1, 4)]

    def generate_rows(self):
        rows = []
        for month, year in self._get_fiscal_months():
            items = (
                PayrollRunItem.objects.filter(
                    pay_run__organisation=self.organisation,
                    pay_run__period_month=month,
                    pay_run__period_year=year,
                    pay_run__status=PayrollRunStatus.FINALIZED,
                )
                .select_related('employee__user', 'pay_run')
                .order_by('employee__employee_code', 'created_at')
            )
            for item in items:
                snapshot = item.snapshot or {}
                rows.append(
                    {
                        'Employee Name': item.employee.user.full_name,
                        'Employee Code': item.employee.employee_code or '',
                        'Month': month,
                        'Year': year,
                        'Professional Tax': str(snapshot.get('professional_tax') or _snapshot_component_amount(snapshot, 'PROFESSIONAL_TAX')),
                        'TDS Monthly': str(snapshot.get('tds_monthly') or item.income_tax or 0),
                        'PF Employee': _snapshot_component_amount(snapshot, 'PF_EMPLOYEE'),
                        'PF Employer': _snapshot_component_amount(snapshot, 'PF_EMPLOYER'),
                        'ESI Employee': _snapshot_component_amount(snapshot, 'ESI_EMPLOYEE'),
                        'ESI Employer': _snapshot_component_amount(snapshot, 'ESI_EMPLOYER'),
                    }
                )
        return rows
