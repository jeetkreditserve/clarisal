from __future__ import annotations

from decimal import Decimal

from apps.payroll.models import PayrollTDSChallan

from . import FilingGenerationResult, decimal_to_string, get_employee_identifier, quarter_months, stable_json


def _quarter_challan_map(*, organisation, fiscal_year: str, quarter: str) -> dict[tuple[int, int], PayrollTDSChallan]:
    months = set(quarter_months(fiscal_year, quarter))
    challans = PayrollTDSChallan.objects.filter(organisation=organisation, fiscal_year=fiscal_year, quarter=quarter).order_by(
        'period_year',
        'period_month',
        'deposit_date',
    )
    return {
        (challan.period_year, challan.period_month): challan
        for challan in challans
        if (challan.period_year, challan.period_month) in months
    }


def generate_form24q_export(*, organisation, quarter: str, fiscal_year: str, payslips_by_employee: dict[str, list]) -> FilingGenerationResult:
    blockers: list[str] = []
    employee_rows: list[dict[str, object]] = []
    period_tax_totals: dict[tuple[int, int], Decimal] = {}
    challan_map = _quarter_challan_map(organisation=organisation, fiscal_year=fiscal_year, quarter=quarter)

    if not (organisation.tan_number or '').strip():
        blockers.append('Organisation TAN is required for Form 24Q export.')

    for employee_key in sorted(payslips_by_employee):
        payslips = payslips_by_employee[employee_key]
        employee = payslips[0].employee
        pan_identifier = get_employee_identifier(employee, id_type='PAN')
        if not pan_identifier:
            blockers.append(f'{employee.employee_code or employee.user.full_name}: missing PAN for Form 24Q export.')
            continue

        gross_salary = Decimal('0.00')
        taxable_income = Decimal('0.00')
        tax_deducted = Decimal('0.00')
        cess = Decimal('0.00')
        for payslip in sorted(payslips, key=lambda item: (item.period_year, item.period_month)):
            snapshot = {**(payslip.pay_run_item.snapshot or {}), **(payslip.snapshot or {})}
            gross_salary += Decimal(str(snapshot.get('gross_pay', '0') or '0'))
            taxable_income += Decimal(str(snapshot.get('annual_taxable_after_sd', '0') or '0'))
            monthly_tax_deducted = Decimal(str(snapshot.get('income_tax', '0') or '0'))
            tax_deducted += monthly_tax_deducted
            cess += Decimal(str(snapshot.get('annual_cess', '0') or '0'))
            period_key = (payslip.period_year, payslip.period_month)
            period_tax_totals[period_key] = period_tax_totals.get(period_key, Decimal('0.00')) + monthly_tax_deducted

        employee_rows.append(
            {
                'employee_id': str(employee.id),
                'employee_code': employee.employee_code or '',
                'employee_name': employee.user.full_name,
                'employee_pan': pan_identifier,
                'gross_salary': decimal_to_string(gross_salary),
                'taxable_income': decimal_to_string(taxable_income),
                'tax_deducted': decimal_to_string(tax_deducted),
                'health_and_education_cess': decimal_to_string(cess),
                'pay_periods': [
                    {'year': payslip.period_year, 'month': payslip.period_month}
                    for payslip in sorted(payslips, key=lambda item: (item.period_year, item.period_month))
                ],
            }
        )

    challan_rows: list[dict[str, str]] = []
    for period_key in sorted(period_tax_totals):
        period_label = f'{period_key[0]}-{period_key[1]:02d}'
        expected_tax = period_tax_totals[period_key]
        challan = challan_map.get(period_key)
        if expected_tax > Decimal('0.00') and challan is None:
            blockers.append(f'{period_label}: missing TDS challan for Form 24Q export.')
            continue
        if challan is None:
            continue
        if expected_tax > Decimal('0.00') and challan.tax_deposited != expected_tax:
            blockers.append(
                f'{period_label}: challan tax deposited {decimal_to_string(challan.tax_deposited)} '
                f'does not match deducted tax {decimal_to_string(expected_tax)}.'
            )
        challan_rows.append(
            {
                'period': period_label,
                'bsr_code': challan.bsr_code,
                'challan_serial_number': challan.challan_serial_number,
                'deposit_date': challan.deposit_date.isoformat(),
                'tax_deposited': decimal_to_string(challan.tax_deposited),
                'interest_amount': decimal_to_string(challan.interest_amount),
                'fee_amount': decimal_to_string(challan.fee_amount),
                'statement_receipt_number': challan.statement_receipt_number,
            }
        )

    payload = {
        'filing_type': 'FORM24Q',
        'fiscal_year': fiscal_year,
        'quarter': quarter,
        'deductor': {
            'organisation_name': organisation.name,
            'tan_number': organisation.tan_number or '',
            'pan_number': organisation.pan_number or '',
        },
        'challans': challan_rows,
        'employees': employee_rows,
    }
    return FilingGenerationResult(
        artifact_format='JSON',
        content_type='application/json',
        file_name=f'form24q-{organisation.slug}-{fiscal_year}-{quarter.lower()}.json',
        artifact_text='' if blockers else stable_json(payload),
        structured_payload=payload,
        metadata={
            'employee_count': len(employee_rows),
            'challan_count': len(challan_rows),
            'total_tax_deposited': decimal_to_string(
                sum((Decimal(row['tax_deposited']) for row in challan_rows), start=Decimal('0.00')),
                places='0.00',
            ),
        },
        validation_errors=sorted(blockers),
    )
