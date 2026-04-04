from __future__ import annotations

from decimal import Decimal

from . import FilingGenerationResult, build_csv, decimal_to_string

ESI_FIELDNAMES = [
    'employee_code',
    'employee_name',
    'esic_ip_number',
    'gross_wages',
    'employee_contribution',
    'employer_contribution',
    'eligibility_mode',
    'contribution_period_start',
    'contribution_period_end',
]


def generate_esi_export(*, organisation, payslips, period_year: int, period_month: int) -> FilingGenerationResult:
    rows: list[dict[str, str]] = []
    blockers: list[str] = []

    for payslip in payslips:
        snapshot = {**(payslip.pay_run_item.snapshot or {}), **(payslip.snapshot or {})}
        esi_employee = Decimal(str(snapshot.get('esi_employee', '0') or '0'))
        esi_employer = Decimal(str(snapshot.get('esi_employer', '0') or '0'))
        if esi_employee <= 0 and esi_employer <= 0:
            continue

        employee = payslip.employee
        profile = getattr(employee, 'profile', None)
        ip_number = getattr(profile, 'esic_ip_number', '').strip() if profile else ''
        if not ip_number:
            blockers.append(f'{employee.employee_code or employee.user.full_name}: missing ESIC IP number for ESI filing.')
            continue

        rows.append(
            {
                'employee_code': employee.employee_code or '',
                'employee_name': employee.user.full_name,
                'esic_ip_number': ip_number,
                'gross_wages': decimal_to_string(snapshot.get('gross_pay', '0')),
                'employee_contribution': decimal_to_string(esi_employee),
                'employer_contribution': decimal_to_string(esi_employer),
                'eligibility_mode': payslip.esi_eligibility_mode,
                'contribution_period_start': payslip.esi_contribution_period_start.isoformat() if payslip.esi_contribution_period_start else '',
                'contribution_period_end': payslip.esi_contribution_period_end.isoformat() if payslip.esi_contribution_period_end else '',
            }
        )

    rows.sort(key=lambda row: (row['employee_code'], row['employee_name']))
    artifact_text = build_csv(rows, ESI_FIELDNAMES) if not blockers else ''
    return FilingGenerationResult(
        artifact_format='CSV',
        content_type='text/csv',
        file_name=f'esi-{organisation.slug}-{period_year}-{period_month:02d}.csv',
        artifact_text=artifact_text,
        structured_payload={
            'filing_type': 'ESI_MONTHLY',
            'period_year': period_year,
            'period_month': period_month,
            'rows': rows,
        },
        metadata={
            'row_count': len(rows),
            'employee_contribution_total': decimal_to_string(sum(Decimal(row['employee_contribution']) for row in rows), places='0.00'),
            'employer_contribution_total': decimal_to_string(sum(Decimal(row['employer_contribution']) for row in rows), places='0.00'),
        },
        validation_errors=sorted(blockers),
    )
