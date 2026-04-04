from __future__ import annotations

from decimal import Decimal
from typing import TypedDict

from apps.payroll.models import PayrollTDSChallan

from . import FilingGenerationResult, decimal_to_string, get_employee_identifier, quarter_months


class QuarterSummary(TypedDict):
    amount_paid: Decimal
    tax_deducted: Decimal
    tax_deposited: Decimal
    statement_receipt_number: str


class QuarterSummaryPayload(TypedDict):
    quarter: str
    statement_receipt_number: str
    amount_paid: str
    tax_deducted: str
    tax_deposited: str


class ChallanDetailPayload(TypedDict):
    period: str
    tax_deposited_for_employee: str
    bsr_code: str
    challan_serial_number: str
    deposit_date: str


class Form16EmployeePayload(TypedDict):
    employee_id: str
    employee_code: str
    employee_name: str
    employee_pan: str
    tax_regime: str
    gross_salary: str
    standard_deduction: str
    deductions_chapter_via: str
    taxable_income: str
    tax_before_rebate: str
    surcharge: str
    cess: str
    tax_deducted: str
    quarter_summaries: list[QuarterSummaryPayload]
    challan_details: list[ChallanDetailPayload]
    fiscal_year: str


def _escape_xml(value: str) -> str:
    return (
        value.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&apos;')
    )


def _render_simple_pdf(lines: list[str]) -> bytes:
    chunks = [lines[index:index + 40] for index in range(0, len(lines), 40)] or [[]]
    objects: list[bytes] = []
    page_ids: list[int] = []

    def add_object(payload: str) -> int:
        objects.append(payload.encode('latin-1'))
        return len(objects)

    font_id = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    pages_id = len(objects) + 1

    content_ids: list[int] = []
    for page_lines in chunks:
        text_lines = ['BT', '/F1 11 Tf', '50 780 Td', '14 TL']
        if page_lines:
            text_lines.append(f'({_escape_pdf_text(page_lines[0])}) Tj')
            for line in page_lines[1:]:
                text_lines.append(f'T* ({_escape_pdf_text(line)}) Tj')
        text_lines.append('ET')
        stream = '\n'.join(text_lines)
        content_ids.append(add_object(f'<< /Length {len(stream.encode("latin-1"))} >>\nstream\n{stream}\nendstream'))

    for content_id in content_ids:
        page_ids.append(
            add_object(
                f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] '
                f'/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>'
            )
        )

    kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
    objects.insert(pages_id - 1, f'<< /Type /Pages /Count {len(page_ids)} /Kids [ {kids} ] >>'.encode('latin-1'))
    catalog_id = len(objects) + 1
    objects.append(f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode('latin-1'))

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode('latin-1'))
        pdf.extend(obj)
        pdf.extend(b'\nendobj\n')
    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('latin-1'))
    pdf.extend(
        (
            f'trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode('latin-1')
    )
    return bytes(pdf)


def _escape_pdf_text(value: str) -> str:
    safe_value = value.encode('latin-1', 'replace').decode('latin-1')
    return safe_value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _quarter_for_month(month: int) -> str:
    if month in {4, 5, 6}:
        return 'Q1'
    if month in {7, 8, 9}:
        return 'Q2'
    if month in {10, 11, 12}:
        return 'Q3'
    return 'Q4'


def _fiscal_year_challan_map(*, organisation, fiscal_year: str) -> dict[tuple[int, int], PayrollTDSChallan]:
    months = {
        month
        for quarter in ('Q1', 'Q2', 'Q3', 'Q4')
        for month in quarter_months(fiscal_year, quarter)
    }
    challans = PayrollTDSChallan.objects.filter(organisation=organisation, fiscal_year=fiscal_year).order_by(
        'period_year',
        'period_month',
        'deposit_date',
    )
    return {
        (challan.period_year, challan.period_month): challan
        for challan in challans
        if (challan.period_year, challan.period_month) in months
    }


def _aggregate_form16_dataset(*, organisation, fiscal_year: str, payslips_by_employee: dict[str, list]) -> tuple[list[Form16EmployeePayload], list[str]]:
    blockers: list[str] = []
    employees: list[Form16EmployeePayload] = []
    challan_map = _fiscal_year_challan_map(organisation=organisation, fiscal_year=fiscal_year)
    if not (organisation.tan_number or '').strip():
        blockers.append('Organisation TAN is required for Form 16 generation.')

    for employee_key in sorted(payslips_by_employee):
        payslips = payslips_by_employee[employee_key]
        employee = payslips[0].employee
        pan_identifier = get_employee_identifier(employee, id_type='PAN')
        if not pan_identifier:
            blockers.append(f'{employee.employee_code or employee.user.full_name}: missing PAN for Form 16 generation.')
            continue

        gross_salary = Decimal('0.00')
        tax_deducted = Decimal('0.00')
        investment_deductions = Decimal('0.00')
        taxable_income = Decimal('0.00')
        cess = Decimal('0.00')
        surcharge = Decimal('0.00')
        tax_before_rebate = Decimal('0.00')
        regime = 'NEW'
        quarter_summaries: dict[str, QuarterSummary] = {}
        challan_details: list[ChallanDetailPayload] = []
        for payslip in sorted(payslips, key=lambda item: (item.period_year, item.period_month)):
            snapshot = {**(payslip.pay_run_item.snapshot or {}), **(payslip.snapshot or {})}
            monthly_gross_salary = Decimal(str(snapshot.get('gross_pay', '0') or '0'))
            monthly_tax_deducted = Decimal(str(snapshot.get('income_tax', '0') or '0'))
            gross_salary += monthly_gross_salary
            tax_deducted += monthly_tax_deducted
            investment_deductions += Decimal(str(snapshot.get('annual_investment_deductions', '0') or '0'))
            taxable_income = max(taxable_income, Decimal(str(snapshot.get('annual_taxable_after_sd', '0') or '0')))
            cess = max(cess, Decimal(str(snapshot.get('annual_cess', '0') or '0')))
            surcharge = max(surcharge, Decimal(str(snapshot.get('annual_surcharge', '0') or '0')))
            tax_before_rebate = max(tax_before_rebate, Decimal(str(snapshot.get('annual_tax_before_rebate', '0') or '0')))
            regime = snapshot.get('tax_regime', regime)

            quarter = _quarter_for_month(payslip.period_month)
            quarter_summary = quarter_summaries.setdefault(
                quarter,
                {
                    'amount_paid': Decimal('0.00'),
                    'tax_deducted': Decimal('0.00'),
                    'tax_deposited': Decimal('0.00'),
                    'statement_receipt_number': '',
                },
            )
            quarter_summary['amount_paid'] += monthly_gross_salary
            quarter_summary['tax_deducted'] += monthly_tax_deducted
            quarter_summary['tax_deposited'] += monthly_tax_deducted

            period_label = f'{payslip.period_year}-{payslip.period_month:02d}'
            challan = challan_map.get((payslip.period_year, payslip.period_month))
            if monthly_tax_deducted > Decimal('0.00') and challan is None:
                blockers.append(f'{employee.employee_code or employee.user.full_name}: missing TDS challan for {period_label} Form 16 output.')
                continue
            if challan is None:
                continue
            if monthly_tax_deducted > Decimal('0.00') and challan.tax_deposited != monthly_tax_deducted:
                blockers.append(
                    f'{employee.employee_code or employee.user.full_name}: challan tax deposited '
                    f'{decimal_to_string(challan.tax_deposited)} does not match deducted tax '
                    f'{decimal_to_string(monthly_tax_deducted)} for {period_label}.'
                )
            existing_receipt = str(quarter_summary['statement_receipt_number'])
            if challan.statement_receipt_number:
                if existing_receipt and existing_receipt != challan.statement_receipt_number:
                    blockers.append(
                        f'{employee.employee_code or employee.user.full_name}: multiple statement receipt numbers found '
                        f'for {quarter} of {fiscal_year}.'
                    )
                else:
                    quarter_summary['statement_receipt_number'] = challan.statement_receipt_number
            challan_details.append(
                {
                    'period': period_label,
                    'tax_deposited_for_employee': decimal_to_string(monthly_tax_deducted),
                    'bsr_code': challan.bsr_code,
                    'challan_serial_number': challan.challan_serial_number,
                    'deposit_date': challan.deposit_date.isoformat(),
                }
            )

        employees.append(
            {
                'employee_id': str(employee.id),
                'employee_code': employee.employee_code or '',
                'employee_name': employee.user.full_name,
                'employee_pan': pan_identifier,
                'tax_regime': regime,
                'gross_salary': decimal_to_string(gross_salary),
                'standard_deduction': decimal_to_string('75000.00'),
                'deductions_chapter_via': decimal_to_string(investment_deductions),
                'taxable_income': decimal_to_string(taxable_income),
                'tax_before_rebate': decimal_to_string(tax_before_rebate),
                'surcharge': decimal_to_string(surcharge),
                'cess': decimal_to_string(cess),
                'tax_deducted': decimal_to_string(tax_deducted),
                'quarter_summaries': [
                    {
                        'quarter': quarter,
                        'statement_receipt_number': str(summary['statement_receipt_number']),
                        'amount_paid': decimal_to_string(summary['amount_paid']),
                        'tax_deducted': decimal_to_string(summary['tax_deducted']),
                        'tax_deposited': decimal_to_string(summary['tax_deposited']),
                    }
                    for quarter, summary in sorted(quarter_summaries.items())
                    if Decimal(summary['amount_paid']) > Decimal('0.00') or Decimal(summary['tax_deducted']) > Decimal('0.00')
                ],
                'challan_details': challan_details,
                'fiscal_year': fiscal_year,
            }
        )
    return employees, blockers


def generate_form16_xml(*, organisation, fiscal_year: str, payslips_by_employee: dict[str, list]) -> FilingGenerationResult:
    employees, blockers = _aggregate_form16_dataset(
        organisation=organisation,
        fiscal_year=fiscal_year,
        payslips_by_employee=payslips_by_employee,
    )
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<form16 fiscal_year="{_escape_xml(fiscal_year)}">',
        '  <employer>',
        f'    <name>{_escape_xml(organisation.name)}</name>',
        f'    <pan>{_escape_xml(organisation.pan_number or "")}</pan>',
        f'    <tan>{_escape_xml(organisation.tan_number or "")}</tan>',
        '  </employer>',
        '  <employees>',
    ]
    for employee in employees:
        xml_lines.extend(
            [
                '    <employee>',
                f'      <employee_code>{_escape_xml(str(employee["employee_code"]))}</employee_code>',
                f'      <employee_name>{_escape_xml(str(employee["employee_name"]))}</employee_name>',
                f'      <employee_pan>{_escape_xml(str(employee["employee_pan"]))}</employee_pan>',
                f'      <tax_regime>{_escape_xml(str(employee["tax_regime"]))}</tax_regime>',
                f'      <gross_salary>{_escape_xml(str(employee["gross_salary"]))}</gross_salary>',
                f'      <standard_deduction>{_escape_xml(str(employee["standard_deduction"]))}</standard_deduction>',
                f'      <deductions_chapter_via>{_escape_xml(str(employee["deductions_chapter_via"]))}</deductions_chapter_via>',
                f'      <taxable_income>{_escape_xml(str(employee["taxable_income"]))}</taxable_income>',
                f'      <tax_before_rebate>{_escape_xml(str(employee["tax_before_rebate"]))}</tax_before_rebate>',
                f'      <surcharge>{_escape_xml(str(employee["surcharge"]))}</surcharge>',
                f'      <cess>{_escape_xml(str(employee["cess"]))}</cess>',
                f'      <tax_deducted>{_escape_xml(str(employee["tax_deducted"]))}</tax_deducted>',
                '      <quarter_summaries>',
            ]
        )
        for summary in employee['quarter_summaries']:
            xml_lines.extend(
                [
                    '        <quarter_summary>',
                    f'          <quarter>{_escape_xml(str(summary["quarter"]))}</quarter>',
                    f'          <statement_receipt_number>{_escape_xml(str(summary["statement_receipt_number"]))}</statement_receipt_number>',
                    f'          <amount_paid>{_escape_xml(str(summary["amount_paid"]))}</amount_paid>',
                    f'          <tax_deducted>{_escape_xml(str(summary["tax_deducted"]))}</tax_deducted>',
                    f'          <tax_deposited>{_escape_xml(str(summary["tax_deposited"]))}</tax_deposited>',
                    '        </quarter_summary>',
                ]
            )
        xml_lines.append('      </quarter_summaries>')
        xml_lines.append('      <challan_details>')
        for challan in employee['challan_details']:
            xml_lines.extend(
                [
                    '        <challan>',
                    f'          <period>{_escape_xml(str(challan["period"]))}</period>',
                    f'          <tax_deposited_for_employee>{_escape_xml(str(challan["tax_deposited_for_employee"]))}</tax_deposited_for_employee>',
                    f'          <bsr_code>{_escape_xml(str(challan["bsr_code"]))}</bsr_code>',
                    f'          <challan_serial_number>{_escape_xml(str(challan["challan_serial_number"]))}</challan_serial_number>',
                    f'          <deposit_date>{_escape_xml(str(challan["deposit_date"]))}</deposit_date>',
                    '        </challan>',
                ]
            )
        xml_lines.extend(['      </challan_details>', '    </employee>'])
    xml_lines.extend(['  </employees>', '</form16>'])
    payload = {
        'filing_type': 'FORM16',
        'fiscal_year': fiscal_year,
        'employees': employees,
    }
    return FilingGenerationResult(
        artifact_format='XML',
        content_type='application/xml',
        file_name=f'form16-{organisation.slug}-{fiscal_year}.xml',
        artifact_text='' if blockers else '\n'.join(xml_lines) + '\n',
        structured_payload=payload,
        metadata={'employee_count': len(employees)},
        validation_errors=sorted(blockers),
    )


def generate_form16_pdf(*, organisation, fiscal_year: str, payslips_by_employee: dict[str, list]) -> FilingGenerationResult:
    employees, blockers = _aggregate_form16_dataset(
        organisation=organisation,
        fiscal_year=fiscal_year,
        payslips_by_employee=payslips_by_employee,
    )
    lines = [f'Form 16 - {organisation.name} - FY {fiscal_year}', f'TAN: {organisation.tan_number or ""}', '']
    for employee in employees:
        lines.extend(
            [
                f'Employee: {employee["employee_name"]} ({employee["employee_code"]})',
                f'PAN: {employee["employee_pan"]}',
                f'Tax Regime: {employee["tax_regime"]}',
                f'Gross Salary: INR {employee["gross_salary"]}',
                f'Standard Deduction: INR {employee["standard_deduction"]}',
                f'Chapter VI-A Deductions: INR {employee["deductions_chapter_via"]}',
                f'Taxable Income: INR {employee["taxable_income"]}',
                f'Tax Before Rebate: INR {employee["tax_before_rebate"]}',
                f'Surcharge: INR {employee["surcharge"]}',
                f'Cess: INR {employee["cess"]}',
                f'Tax Deducted: INR {employee["tax_deducted"]}',
                'Quarter summaries:',
            ]
        )
        for summary in employee['quarter_summaries']:
            lines.append(
                '  '
                f'{summary["quarter"]} | Receipt {summary["statement_receipt_number"] or "Pending"} | '
                f'Amount Paid INR {summary["amount_paid"]} | Tax Deducted INR {summary["tax_deducted"]} | '
                f'Tax Deposited INR {summary["tax_deposited"]}'
            )
        if employee['challan_details']:
            lines.append('Challan details:')
            for challan in employee['challan_details']:
                lines.append(
                    '  '
                    f'{challan["period"]} | BSR {challan["bsr_code"]} | Challan {challan["challan_serial_number"]} | '
                    f'Deposit {challan["deposit_date"]} | Employee Tax INR {challan["tax_deposited_for_employee"]}'
                )
        lines.append('')
    payload = {
        'filing_type': 'FORM16',
        'fiscal_year': fiscal_year,
        'employees': employees,
    }
    return FilingGenerationResult(
        artifact_format='PDF',
        content_type='application/pdf',
        file_name=f'form16-{organisation.slug}-{fiscal_year}.pdf',
        artifact_binary=b'' if blockers else _render_simple_pdf(lines),
        structured_payload=payload,
        metadata={'employee_count': len(employees)},
        validation_errors=sorted(blockers),
    )
