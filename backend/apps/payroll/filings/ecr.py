from __future__ import annotations

from decimal import Decimal

from . import FilingGenerationResult, build_csv, decimal_to_rupee_int

ECR_FIELDNAMES = [
    'uan',
    'member_name',
    'gross_wages',
    'epf_wages',
    'eps_wages',
    'edli_wages',
    'epf_employee_share',
    'eps_employer_share',
    'epf_employer_share',
    'ncp_days',
    'refund_of_advance',
    'epf_admin_charges',
    'edli_charges',
]


def generate_ecr_export(*, organisation, payslips, period_year: int, period_month: int) -> FilingGenerationResult:
    rows: list[dict[str, str]] = []
    blockers: list[str] = []

    for payslip in payslips:
        snapshot = {**(payslip.pay_run_item.snapshot or {}), **(payslip.snapshot or {})}
        lines = snapshot.get('lines', [])
        pf_employee = Decimal(str(snapshot.get('auto_pf', snapshot.get('pf_employee', '0')) or '0'))
        pf_employer_total = Decimal(str(snapshot.get('pf_employer', '0') or '0'))
        if pf_employee <= 0 and pf_employer_total <= 0:
            continue

        employee = payslip.employee
        profile = getattr(employee, 'profile', None)
        uan_number = getattr(profile, 'uan_number', '').strip() if profile else ''
        if not uan_number:
            blockers.append(f'{employee.employee_code or employee.user.full_name}: missing UAN number for PF ECR.')
            continue

        basic_line = next((line for line in lines if line.get('component_code') == 'BASIC'), None)
        gross_wages = Decimal(str(snapshot.get('gross_pay', '0') or '0'))
        epf_wages = Decimal(str(basic_line.get('monthly_amount', '0') if basic_line else '0'))
        eps_wages = min(epf_wages, Decimal('15000.00'))
        edli_wages = epf_wages
        eps_employer_share = Decimal(str(getattr(payslip.pay_run_item, 'eps_employer', '0') or '0')).quantize(Decimal('1'))
        epf_employer_share = Decimal(str(getattr(payslip.pay_run_item, 'epf_employer', '0') or '0')).quantize(Decimal('1'))
        if eps_employer_share <= Decimal('0') and epf_employer_share <= Decimal('0'):
            eps_employer_share = min(eps_wages * Decimal('0.0833'), Decimal('1250.00')).quantize(Decimal('1'))
            epf_employer_share = max(Decimal('0.00'), pf_employer_total - eps_employer_share).quantize(Decimal('1'))
        epf_admin_charges = (epf_wages * Decimal('0.0050')).quantize(Decimal('1'))
        edli_charges = (edli_wages * Decimal('0.0050')).quantize(Decimal('1'))

        rows.append(
            {
                'uan': uan_number,
                'member_name': employee.user.full_name,
                'gross_wages': decimal_to_rupee_int(gross_wages),
                'epf_wages': decimal_to_rupee_int(epf_wages),
                'eps_wages': decimal_to_rupee_int(eps_wages),
                'edli_wages': decimal_to_rupee_int(edli_wages),
                'epf_employee_share': decimal_to_rupee_int(pf_employee),
                'eps_employer_share': decimal_to_rupee_int(eps_employer_share),
                'epf_employer_share': decimal_to_rupee_int(epf_employer_share),
                'ncp_days': str(int(Decimal(str(snapshot.get('lop_days', '0') or '0')).quantize(Decimal('1')))),
                'refund_of_advance': '0',
                'epf_admin_charges': decimal_to_rupee_int(epf_admin_charges),
                'edli_charges': decimal_to_rupee_int(edli_charges),
            }
        )

    rows.sort(key=lambda row: (row['uan'], row['member_name']))
    artifact_text = build_csv(rows, ECR_FIELDNAMES) if not blockers else ''
    return FilingGenerationResult(
        artifact_format='CSV',
        content_type='text/csv',
        file_name=f'pf-ecr-{organisation.slug}-{period_year}-{period_month:02d}.csv',
        artifact_text=artifact_text,
        structured_payload={
            'filing_type': 'PF_ECR',
            'period_year': period_year,
            'period_month': period_month,
            'rows': rows,
        },
        metadata={
            'row_count': len(rows),
            'total_epf_employee_share': sum(int(row['epf_employee_share']) for row in rows),
            'total_eps_employer_share': sum(int(row['eps_employer_share']) for row in rows),
            'total_epf_employer_share': sum(int(row['epf_employer_share']) for row in rows),
        },
        validation_errors=sorted(blockers),
    )
