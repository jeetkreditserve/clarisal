from __future__ import annotations

from decimal import Decimal

from . import FilingGenerationResult, build_csv, decimal_to_string

SUPPORTED_PT_TEMPLATES = {
    'MH': 'PT_SUMMARY_V1',
    'KA': 'PT_SUMMARY_V1',
    'TN': 'PT_SUMMARY_V1',
    'WB': 'PT_SUMMARY_V1',
    'AP': 'PT_SUMMARY_V1',
    'TG': 'PT_SUMMARY_V1',
    'MP': 'PT_SUMMARY_V1',
}

PT_FIELDNAMES = [
    'state_code',
    'template_code',
    'employee_code',
    'employee_name',
    'gross_pay',
    'professional_tax',
]


def generate_professional_tax_export(*, organisation, payslips, period_year: int, period_month: int) -> FilingGenerationResult:
    rows: list[dict[str, str]] = []
    blockers: list[str] = []

    for payslip in payslips:
        snapshot = {**(payslip.pay_run_item.snapshot or {}), **(payslip.snapshot or {})}
        pt_amount = Decimal(str(snapshot.get('pt_monthly', '0') or '0'))
        if pt_amount <= 0:
            continue
        state_code = (snapshot.get('pt_state_code') or '').strip().upper()
        if state_code not in SUPPORTED_PT_TEMPLATES:
            blockers.append(f'{payslip.employee.employee_code or payslip.employee.user.full_name}: PT return template is not defined for state {state_code or "UNKNOWN"}.')
            continue
        rows.append(
            {
                'state_code': state_code,
                'template_code': SUPPORTED_PT_TEMPLATES[state_code],
                'employee_code': payslip.employee.employee_code or '',
                'employee_name': payslip.employee.user.full_name,
                'gross_pay': decimal_to_string(snapshot.get('gross_pay', '0')),
                'professional_tax': decimal_to_string(pt_amount),
            }
        )

    rows.sort(key=lambda row: (row['state_code'], row['employee_code'], row['employee_name']))
    return FilingGenerationResult(
        artifact_format='CSV',
        content_type='text/csv',
        file_name=f'professional-tax-{organisation.slug}-{period_year}-{period_month:02d}.csv',
        artifact_text='' if blockers else build_csv(rows, PT_FIELDNAMES),
        structured_payload={
            'filing_type': 'PROFESSIONAL_TAX',
            'period_year': period_year,
            'period_month': period_month,
            'rows': rows,
        },
        metadata={
            'row_count': len(rows),
            'states': sorted({row['state_code'] for row in rows}),
        },
        validation_errors=sorted(blockers),
    )
