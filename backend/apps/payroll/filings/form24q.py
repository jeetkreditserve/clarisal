from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import TypedDict

from apps.payroll.models import PayrollTDSChallan

from . import FilingGenerationResult, decimal_to_string, fiscal_year_bounds, get_employee_identifier, quarter_months

FORM24Q_SCHEMA_REFERENCE = 'protean-rpu-4.7'
FORM24Q_DATA_STRUCTURE_REFERENCE = 'cbdt-notification-2006-annexure-a'
FORM24Q_FVU_REFERENCE = 'protean-fvu-9.0'
FORM24Q_DEFAULT_SECTION_CODE = '192'
FORM24Q_DEFAULT_MINOR_HEAD = '200'


class Form24QPayPeriod(TypedDict):
    year: int
    month: int


class Form24QChallanReference(TypedDict):
    period: str
    bsr_code: str
    challan_serial_number: str
    deposit_date: str


class Form24QEmployeeRow(TypedDict):
    employee_sequence: int
    employee_id: str
    employee_code: str
    employee_name: str
    employee_pan: str
    section_code: str
    gross_salary: str
    taxable_income: str
    tax_deducted: str
    health_and_education_cess: str
    pay_periods: list[Form24QPayPeriod]
    challan_refs: list[Form24QChallanReference]


class Form24QChallanRow(TypedDict):
    period: str
    bsr_code: str
    challan_serial_number: str
    deposit_date: str
    tax_deposited: str
    interest_amount: str
    fee_amount: str
    statement_receipt_number: str


class Form24QChallanXmlRow(TypedDict):
    sequence_number: int
    period: str
    tax_amount: str
    surcharge_amount: str
    health_and_education_cess: str
    interest_amount: str
    fee_amount: str
    other_amount: str
    tax_deposited: str
    deposit_mode: str
    bsr_code: str
    challan_serial_number: str
    deposit_date: str
    minor_head: str
    statement_receipt_number: str
    deductee_rows: list[Form24QDeducteeXmlRow]


class Form24QDeducteeXmlRow(TypedDict):
    deductee_sequence: int
    employee_reference_number: str
    employee_id: str
    employee_code: str
    employee_name: str
    employee_pan: str
    section_code: str
    payment_date: str
    deduction_date: str
    amount_paid_or_credited: str
    tax_amount: str
    surcharge_amount: str
    health_and_education_cess: str
    total_tax_deducted: str
    total_tax_deposited: str
    deduction_reason_code: str
    certificate_number: str


class Form24QAnnexureIIRow(TypedDict):
    serial_number: str
    employee_pan: str
    employee_name: str
    employee_age_category: str
    employment_from: str
    employment_to: str
    tax_regime: str
    opting_out_of_section_115bac_1a: str
    taxable_amount_current_employer: str
    taxable_amount_previous_employer: str
    total_salary: str
    standard_deduction: str
    deduction_section_16_ii: str
    deduction_section_16_iii: str
    income_chargeable_under_salary: str
    other_special_allowances_under_section_10_14: str
    total_exemption_claimed_under_section_10: str
    other_income_declared: str
    gross_total_income: str
    deduction_section_80c_etc: str
    deduction_other_chapter_via: str
    deduction_80cch_employee_gross: str
    deduction_80cch_employee_deductible: str
    deduction_80cch_central_government_gross: str
    deduction_80cch_central_government_deductible: str
    total_deductible_chapter_via: str
    total_taxable_income: str
    income_tax_on_total_income: str
    surcharge_on_income_tax: str
    health_and_education_cess: str
    relief_under_section_89: str
    net_tax_payable: str
    tax_deducted_current_employer: str
    tax_deducted_previous_employer: str
    tax_deducted_total: str
    tax_shortfall_or_excess: str
    higher_rate_due_to_missing_pan: str
    hra_rent_above_one_lakh: str
    interest_under_house_property: str
    approved_superannuation_fund: str


def _escape_xml(value: str) -> str:
    return (
        value.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&apos;')
    )


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


def _deductor_category(organisation) -> str:
    if organisation.entity_type in {
        'PRIVATE_LIMITED',
        'PUBLIC_LIMITED',
        'ONE_PERSON_COMPANY',
        'SECTION_8_COMPANY',
    }:
        return 'COMPANY'
    if organisation.entity_type in {
        'LIMITED_LIABILITY_PARTNERSHIP',
        'PARTNERSHIP_FIRM',
        'SOLE_PROPRIETORSHIP',
    }:
        return 'FIRM'
    if organisation.entity_type == 'GOVERNMENT_BODY':
        return 'STATUTORY_BODY_GOVERNMENT'
    return 'OTHER'


def _responsible_person_payload(organisation) -> dict[str, str]:
    membership = organisation.memberships.filter(is_org_admin=True, status='ACTIVE').select_related('user').order_by('created_at').first()
    responsible_person = organisation.primary_admin_user or organisation.created_by or (membership.user if membership else None)
    if responsible_person is None:
        return {
            'name': '',
            'pan': '',
            'address': organisation.address or '',
            'phone': organisation.phone or '',
            'email': organisation.email or '',
        }

    full_name = responsible_person.full_name or responsible_person.email
    return {
        'name': full_name,
        'pan': '',
        'address': organisation.address or '',
        'phone': organisation.phone or '',
        'email': responsible_person.email or organisation.email or '',
    }


def _empty_breakdown() -> dict[str, Decimal]:
    return {
        'tax_amount': Decimal('0.00'),
        'surcharge_amount': Decimal('0.00'),
        'health_and_education_cess': Decimal('0.00'),
    }


def _format_form24q_date(value: date | None) -> str:
    if value is None:
        return ''
    return value.strftime('%d/%m/%Y')


def _period_end_date(*, year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def _split_monthly_tds_components(snapshot: dict[str, object], total_deducted: Decimal) -> dict[str, Decimal]:
    if total_deducted <= Decimal('0.00'):
        return _empty_breakdown()

    annual_tax_total = Decimal(str(snapshot.get('annual_tax_total', '0') or '0'))
    if annual_tax_total <= Decimal('0.00'):
        return {
            'tax_amount': total_deducted.quantize(Decimal('0.01')),
            'surcharge_amount': Decimal('0.00'),
            'health_and_education_cess': Decimal('0.00'),
        }

    annual_surcharge = Decimal(str(snapshot.get('annual_surcharge', '0') or '0'))
    annual_cess = Decimal(str(snapshot.get('annual_cess', '0') or '0'))
    # TODO(P24-T7-001): persist monthly challan tax/cess splits instead of proportionally deriving them from annual snapshots.
    surcharge_amount = (total_deducted * annual_surcharge / annual_tax_total).quantize(Decimal('0.01'))
    cess_amount = (total_deducted * annual_cess / annual_tax_total).quantize(Decimal('0.01'))
    tax_amount = (total_deducted - surcharge_amount - cess_amount).quantize(Decimal('0.01'))
    if tax_amount < Decimal('0.00'):
        tax_amount = Decimal('0.00')
    return {
        'tax_amount': tax_amount,
        'surcharge_amount': surcharge_amount,
        'health_and_education_cess': cess_amount,
    }


def _employee_age_flag(employee, *, fiscal_year: str) -> str:
    profile = getattr(employee, 'profile', None)
    if profile is None or profile.date_of_birth is None:
        return 'G'

    fiscal_year_end = fiscal_year_bounds(fiscal_year)[1]
    age = fiscal_year_end.year - profile.date_of_birth.year - (
        (fiscal_year_end.month, fiscal_year_end.day) < (profile.date_of_birth.month, profile.date_of_birth.day)
    )
    if age >= 80:
        return 'O'
    if age >= 60:
        return 'S'
    if profile.gender == 'FEMALE':
        return 'W'
    return 'G'


def _employment_period(employee, *, fiscal_year: str) -> tuple[str, str]:
    fiscal_year_start, fiscal_year_end = fiscal_year_bounds(fiscal_year)
    from_date = max(employee.date_of_joining or fiscal_year_start, fiscal_year_start)
    to_date = min(employee.date_of_exit or fiscal_year_end, fiscal_year_end)
    return _format_form24q_date(from_date), _format_form24q_date(to_date)


def _annexure_ii_payload(
    *,
    employee,
    fiscal_year: str,
    summary: Form24QEmployeeRow,
    latest_snapshot: dict[str, object],
) -> Form24QAnnexureIIRow:
    employment_from, employment_to = _employment_period(employee, fiscal_year=fiscal_year)
    total_salary = Decimal(str(latest_snapshot.get('annual_taxable_gross', summary['gross_salary']) or '0'))
    tax_regime = str(latest_snapshot.get('tax_regime', 'NEW') or 'NEW').upper()
    standard_deduction = Decimal(str(latest_snapshot.get('annual_standard_deduction', '0') or '0'))
    total_deductions = Decimal(str(latest_snapshot.get('annual_investment_deductions', '0') or '0'))
    taxable_income = Decimal(str(latest_snapshot.get('annual_taxable_after_sd', summary['taxable_income']) or '0'))
    tax_before_rebate = Decimal(str(latest_snapshot.get('annual_tax_before_rebate', '0') or '0'))
    surcharge = Decimal(str(latest_snapshot.get('annual_surcharge', '0') or '0'))
    cess = Decimal(str(latest_snapshot.get('annual_cess', summary['health_and_education_cess']) or '0'))
    total_tax_deducted = Decimal(str(summary['tax_deducted']))
    total_tax_payable = Decimal(str(latest_snapshot.get('annual_tax_total', summary['tax_deducted']) or '0'))
    chapter_via_other = Decimal('0.00')
    total_deductible_chapter_via = (total_deductions + chapter_via_other).quantize(Decimal('0.01'))
    # TODO(P24-T7-002): enrich Annexure II once previous-employer and HRA/lender disclosure data is modelled explicitly.
    return {
        'serial_number': str(summary['employee_sequence']),
        'employee_pan': str(summary['employee_pan']),
        'employee_name': str(summary['employee_name']),
        'employee_age_category': _employee_age_flag(employee, fiscal_year=fiscal_year),
        'employment_from': employment_from,
        'employment_to': employment_to,
        'tax_regime': tax_regime,
        'opting_out_of_section_115bac_1a': 'YES' if tax_regime == 'OLD' else 'NO',
        'taxable_amount_current_employer': decimal_to_string(taxable_income),
        'taxable_amount_previous_employer': decimal_to_string('0.00'),
        'total_salary': decimal_to_string(total_salary),
        'standard_deduction': decimal_to_string(standard_deduction),
        'deduction_section_16_ii': decimal_to_string('0.00'),
        'deduction_section_16_iii': decimal_to_string('0.00'),
        'income_chargeable_under_salary': decimal_to_string(taxable_income),
        'other_special_allowances_under_section_10_14': decimal_to_string('0.00'),
        'total_exemption_claimed_under_section_10': decimal_to_string('0.00'),
        'other_income_declared': decimal_to_string('0.00'),
        'gross_total_income': decimal_to_string(total_salary),
        'deduction_section_80c_etc': decimal_to_string(total_deductions),
        'deduction_other_chapter_via': decimal_to_string(chapter_via_other),
        'deduction_80cch_employee_gross': decimal_to_string('0.00'),
        'deduction_80cch_employee_deductible': decimal_to_string('0.00'),
        'deduction_80cch_central_government_gross': decimal_to_string('0.00'),
        'deduction_80cch_central_government_deductible': decimal_to_string('0.00'),
        'total_deductible_chapter_via': decimal_to_string(total_deductible_chapter_via),
        'total_taxable_income': decimal_to_string(taxable_income),
        'income_tax_on_total_income': decimal_to_string(tax_before_rebate),
        'surcharge_on_income_tax': decimal_to_string(surcharge),
        'health_and_education_cess': decimal_to_string(cess),
        'relief_under_section_89': decimal_to_string('0.00'),
        'net_tax_payable': decimal_to_string(total_tax_payable),
        'tax_deducted_current_employer': decimal_to_string(total_tax_deducted),
        'tax_deducted_previous_employer': decimal_to_string('0.00'),
        'tax_deducted_total': decimal_to_string(total_tax_deducted),
        'tax_shortfall_or_excess': decimal_to_string(total_tax_payable - total_tax_deducted),
        'higher_rate_due_to_missing_pan': 'NO',
        'hra_rent_above_one_lakh': 'NO',
        'interest_under_house_property': 'NO',
        'approved_superannuation_fund': 'NO',
    }


def _render_form24q_xml(
    *,
    organisation,
    quarter: str,
    fiscal_year: str,
    challans: list[Form24QChallanXmlRow],
    employees: list[Form24QEmployeeRow],
    annexure_ii: list[Form24QAnnexureIIRow],
) -> str:
    responsible_person = _responsible_person_payload(organisation)
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<form24q schema_reference="{FORM24Q_SCHEMA_REFERENCE}" '
            f'data_structure_reference="{FORM24Q_DATA_STRUCTURE_REFERENCE}" '
            f'fvu_reference="{FORM24Q_FVU_REFERENCE}" '
            f'fiscal_year="{_escape_xml(fiscal_year)}" quarter="{_escape_xml(quarter)}">'
        ),
        '  <statement_details>',
        '    <statement_type>REGULAR</statement_type>',
        f'    <quarter>{_escape_xml(quarter)}</quarter>',
        f'    <financial_year>{_escape_xml(fiscal_year)}</financial_year>',
        f'    <deductor_category>{_escape_xml(_deductor_category(organisation))}</deductor_category>',
        '  </statement_details>',
        '  <deductor_details>',
        f'    <tan>{_escape_xml(organisation.tan_number or "")}</tan>',
        f'    <pan>{_escape_xml(organisation.pan_number or "")}</pan>',
        f'    <name>{_escape_xml(organisation.name)}</name>',
        f'    <address>{_escape_xml(organisation.address or "")}</address>',
        f'    <phone>{_escape_xml(organisation.phone or "")}</phone>',
        f'    <email>{_escape_xml(organisation.email or "")}</email>',
        f'    <gstin>{_escape_xml(getattr(organisation, "gstin", "") or "")}</gstin>',
        '  </deductor_details>',
        '  <responsible_person_details>',
        f'    <name>{_escape_xml(responsible_person["name"])}</name>',
        f'    <pan>{_escape_xml(responsible_person["pan"])}</pan>',
        f'    <address>{_escape_xml(responsible_person["address"])}</address>',
        f'    <phone>{_escape_xml(responsible_person["phone"])}</phone>',
        f'    <email>{_escape_xml(responsible_person["email"])}</email>',
        '  </responsible_person_details>',
        '  <tax_deducted_and_paid_to_central_government>',
    ]
    for challan in challans:
        xml_lines.extend(
            [
                '    <challan>',
                f'      <sequence_number>{_escape_xml(str(challan["sequence_number"]))}</sequence_number>',
                f'      <period>{_escape_xml(str(challan["period"]))}</period>',
                f'      <tax_amount>{_escape_xml(str(challan["tax_amount"]))}</tax_amount>',
                f'      <surcharge_amount>{_escape_xml(str(challan["surcharge_amount"]))}</surcharge_amount>',
                (
                    '      <health_and_education_cess>'
                    f'{_escape_xml(str(challan["health_and_education_cess"]))}'
                    '</health_and_education_cess>'
                ),
                f'      <interest_amount>{_escape_xml(str(challan["interest_amount"]))}</interest_amount>',
                f'      <fee_amount>{_escape_xml(str(challan["fee_amount"]))}</fee_amount>',
                f'      <other_amount>{_escape_xml(str(challan["other_amount"]))}</other_amount>',
                f'      <total_tax_deposited>{_escape_xml(str(challan["tax_deposited"]))}</total_tax_deposited>',
                f'      <deposit_mode>{_escape_xml(str(challan["deposit_mode"]))}</deposit_mode>',
                f'      <bsr_code>{_escape_xml(str(challan["bsr_code"]))}</bsr_code>',
                f'      <challan_serial_number>{_escape_xml(str(challan["challan_serial_number"]))}</challan_serial_number>',
                f'      <deposit_date>{_escape_xml(str(challan["deposit_date"]))}</deposit_date>',
                f'      <minor_head>{_escape_xml(str(challan["minor_head"]))}</minor_head>',
                (
                    '      <statement_receipt_number>'
                    f'{_escape_xml(str(challan["statement_receipt_number"]))}'
                    '</statement_receipt_number>'
                ),
                '      <deductee_entries>',
            ]
        )
        for deductee in challan['deductee_rows']:
            xml_lines.extend(
                [
                    '        <deductee>',
                    f'          <deductee_sequence>{_escape_xml(str(deductee["deductee_sequence"]))}</deductee_sequence>',
                    (
                        '          <employee_reference_number>'
                        f'{_escape_xml(deductee["employee_reference_number"])}'
                        '</employee_reference_number>'
                    ),
                    f'          <employee_id>{_escape_xml(deductee["employee_id"])}</employee_id>',
                    f'          <employee_code>{_escape_xml(deductee["employee_code"])}</employee_code>',
                    f'          <employee_name>{_escape_xml(deductee["employee_name"])}</employee_name>',
                    f'          <employee_pan>{_escape_xml(deductee["employee_pan"])}</employee_pan>',
                    f'          <section_code>{_escape_xml(deductee["section_code"])}</section_code>',
                    f'          <payment_date>{_escape_xml(deductee["payment_date"])}</payment_date>',
                    f'          <deduction_date>{_escape_xml(deductee["deduction_date"])}</deduction_date>',
                    (
                        '          <amount_paid_or_credited>'
                        f'{_escape_xml(deductee["amount_paid_or_credited"])}'
                        '</amount_paid_or_credited>'
                    ),
                    f'          <tax_amount>{_escape_xml(deductee["tax_amount"])}</tax_amount>',
                    f'          <surcharge_amount>{_escape_xml(deductee["surcharge_amount"])}</surcharge_amount>',
                    (
                        '          <health_and_education_cess>'
                        f'{_escape_xml(deductee["health_and_education_cess"])}'
                        '</health_and_education_cess>'
                    ),
                    (
                        '          <total_tax_deducted>'
                        f'{_escape_xml(deductee["total_tax_deducted"])}'
                        '</total_tax_deducted>'
                    ),
                    (
                        '          <total_tax_deposited>'
                        f'{_escape_xml(deductee["total_tax_deposited"])}'
                        '</total_tax_deposited>'
                    ),
                    (
                        '          <deduction_reason_code>'
                        f'{_escape_xml(deductee["deduction_reason_code"])}'
                        '</deduction_reason_code>'
                    ),
                    (
                        '          <certificate_number>'
                        f'{_escape_xml(deductee["certificate_number"])}'
                        '</certificate_number>'
                    ),
                    '        </deductee>',
                ]
            )
        xml_lines.extend(
            [
                '      </deductee_entries>',
                '    </challan>',
            ]
        )
    xml_lines.append('  </tax_deducted_and_paid_to_central_government>')
    xml_lines.append('  <annexure_i_employee_summaries>')
    for employee in employees:
        xml_lines.extend(
            [
                '    <employee>',
                f'      <employee_id>{_escape_xml(str(employee["employee_id"]))}</employee_id>',
                f'      <employee_code>{_escape_xml(str(employee["employee_code"]))}</employee_code>',
                f'      <employee_name>{_escape_xml(str(employee["employee_name"]))}</employee_name>',
                f'      <employee_pan>{_escape_xml(str(employee["employee_pan"]))}</employee_pan>',
                f'      <section_code>{_escape_xml(str(employee["section_code"]))}</section_code>',
                '      <pay_periods>',
            ]
        )
        for pay_period in employee['pay_periods']:
            xml_lines.append(
                f'        <period year="{_escape_xml(str(pay_period["year"]))}" month="{_escape_xml(str(pay_period["month"]))}" />'
            )
        xml_lines.extend(
            [
                '      </pay_periods>',
                f'      <gross_salary>{_escape_xml(str(employee["gross_salary"]))}</gross_salary>',
                f'      <taxable_income>{_escape_xml(str(employee["taxable_income"]))}</taxable_income>',
                f'      <tax_deducted>{_escape_xml(str(employee["tax_deducted"]))}</tax_deducted>',
                (
                    '      <health_and_education_cess>'
                    f'{_escape_xml(str(employee["health_and_education_cess"]))}'
                    '</health_and_education_cess>'
                ),
                '      <challan_refs>',
            ]
        )
        for challan_ref in employee['challan_refs']:
            xml_lines.extend(
                [
                    '        <challan_ref>',
                    f'          <period>{_escape_xml(str(challan_ref["period"]))}</period>',
                    f'          <bsr_code>{_escape_xml(str(challan_ref["bsr_code"]))}</bsr_code>',
                    (
                        '          <challan_serial_number>'
                        f'{_escape_xml(str(challan_ref["challan_serial_number"]))}'
                        '</challan_serial_number>'
                    ),
                    f'          <deposit_date>{_escape_xml(str(challan_ref["deposit_date"]))}</deposit_date>',
                    '        </challan_ref>',
                ]
            )
        xml_lines.extend(['      </challan_refs>', '    </employee>'])
    xml_lines.append('  </annexure_i_employee_summaries>')
    if annexure_ii:
        xml_lines.append('  <annexure_ii_salary_details>')
        for salary_detail in annexure_ii:
            xml_lines.extend(
                [
                    '    <employee>',
                    f'      <serial_number>{_escape_xml(salary_detail["serial_number"])}</serial_number>',
                    f'      <employee_pan>{_escape_xml(salary_detail["employee_pan"])}</employee_pan>',
                    f'      <employee_name>{_escape_xml(salary_detail["employee_name"])}</employee_name>',
                    f'      <employee_age_category>{_escape_xml(salary_detail["employee_age_category"])}</employee_age_category>',
                    f'      <employment_from>{_escape_xml(salary_detail["employment_from"])}</employment_from>',
                    f'      <employment_to>{_escape_xml(salary_detail["employment_to"])}</employment_to>',
                    f'      <tax_regime>{_escape_xml(salary_detail["tax_regime"])}</tax_regime>',
                    (
                        '      <opting_out_of_section_115bac_1a>'
                        f'{_escape_xml(salary_detail["opting_out_of_section_115bac_1a"])}'
                        '</opting_out_of_section_115bac_1a>'
                    ),
                    (
                        '      <taxable_amount_current_employer>'
                        f'{_escape_xml(salary_detail["taxable_amount_current_employer"])}'
                        '</taxable_amount_current_employer>'
                    ),
                    (
                        '      <taxable_amount_previous_employer>'
                        f'{_escape_xml(salary_detail["taxable_amount_previous_employer"])}'
                        '</taxable_amount_previous_employer>'
                    ),
                    f'      <total_salary>{_escape_xml(salary_detail["total_salary"])}</total_salary>',
                    f'      <standard_deduction>{_escape_xml(salary_detail["standard_deduction"])}</standard_deduction>',
                    (
                        '      <deduction_section_16_ii>'
                        f'{_escape_xml(salary_detail["deduction_section_16_ii"])}'
                        '</deduction_section_16_ii>'
                    ),
                    (
                        '      <deduction_section_16_iii>'
                        f'{_escape_xml(salary_detail["deduction_section_16_iii"])}'
                        '</deduction_section_16_iii>'
                    ),
                    (
                        '      <income_chargeable_under_salary>'
                        f'{_escape_xml(salary_detail["income_chargeable_under_salary"])}'
                        '</income_chargeable_under_salary>'
                    ),
                    (
                        '      <other_special_allowances_under_section_10_14>'
                        f'{_escape_xml(salary_detail["other_special_allowances_under_section_10_14"])}'
                        '</other_special_allowances_under_section_10_14>'
                    ),
                    (
                        '      <total_exemption_claimed_under_section_10>'
                        f'{_escape_xml(salary_detail["total_exemption_claimed_under_section_10"])}'
                        '</total_exemption_claimed_under_section_10>'
                    ),
                    f'      <other_income_declared>{_escape_xml(salary_detail["other_income_declared"])}</other_income_declared>',
                    f'      <gross_total_income>{_escape_xml(salary_detail["gross_total_income"])}</gross_total_income>',
                    (
                        '      <deduction_section_80c_etc>'
                        f'{_escape_xml(salary_detail["deduction_section_80c_etc"])}'
                        '</deduction_section_80c_etc>'
                    ),
                    (
                        '      <deduction_other_chapter_via>'
                        f'{_escape_xml(salary_detail["deduction_other_chapter_via"])}'
                        '</deduction_other_chapter_via>'
                    ),
                    (
                        '      <deduction_80cch_employee_gross>'
                        f'{_escape_xml(salary_detail["deduction_80cch_employee_gross"])}'
                        '</deduction_80cch_employee_gross>'
                    ),
                    (
                        '      <deduction_80cch_employee_deductible>'
                        f'{_escape_xml(salary_detail["deduction_80cch_employee_deductible"])}'
                        '</deduction_80cch_employee_deductible>'
                    ),
                    (
                        '      <deduction_80cch_central_government_gross>'
                        f'{_escape_xml(salary_detail["deduction_80cch_central_government_gross"])}'
                        '</deduction_80cch_central_government_gross>'
                    ),
                    (
                        '      <deduction_80cch_central_government_deductible>'
                        f'{_escape_xml(salary_detail["deduction_80cch_central_government_deductible"])}'
                        '</deduction_80cch_central_government_deductible>'
                    ),
                    (
                        '      <total_deductible_chapter_via>'
                        f'{_escape_xml(salary_detail["total_deductible_chapter_via"])}'
                        '</total_deductible_chapter_via>'
                    ),
                    f'      <total_taxable_income>{_escape_xml(salary_detail["total_taxable_income"])}</total_taxable_income>',
                    (
                        '      <income_tax_on_total_income>'
                        f'{_escape_xml(salary_detail["income_tax_on_total_income"])}'
                        '</income_tax_on_total_income>'
                    ),
                    (
                        '      <surcharge_on_income_tax>'
                        f'{_escape_xml(salary_detail["surcharge_on_income_tax"])}'
                        '</surcharge_on_income_tax>'
                    ),
                    (
                        '      <health_and_education_cess>'
                        f'{_escape_xml(salary_detail["health_and_education_cess"])}'
                        '</health_and_education_cess>'
                    ),
                    (
                        '      <relief_under_section_89>'
                        f'{_escape_xml(salary_detail["relief_under_section_89"])}'
                        '</relief_under_section_89>'
                    ),
                    f'      <net_tax_payable>{_escape_xml(salary_detail["net_tax_payable"])}</net_tax_payable>',
                    (
                        '      <tax_deducted_current_employer>'
                        f'{_escape_xml(salary_detail["tax_deducted_current_employer"])}'
                        '</tax_deducted_current_employer>'
                    ),
                    (
                        '      <tax_deducted_previous_employer>'
                        f'{_escape_xml(salary_detail["tax_deducted_previous_employer"])}'
                        '</tax_deducted_previous_employer>'
                    ),
                    f'      <tax_deducted_total>{_escape_xml(salary_detail["tax_deducted_total"])}</tax_deducted_total>',
                    (
                        '      <tax_shortfall_or_excess>'
                        f'{_escape_xml(salary_detail["tax_shortfall_or_excess"])}'
                        '</tax_shortfall_or_excess>'
                    ),
                    (
                        '      <higher_rate_due_to_missing_pan>'
                        f'{_escape_xml(salary_detail["higher_rate_due_to_missing_pan"])}'
                        '</higher_rate_due_to_missing_pan>'
                    ),
                    (
                        '      <hra_rent_above_one_lakh>'
                        f'{_escape_xml(salary_detail["hra_rent_above_one_lakh"])}'
                        '</hra_rent_above_one_lakh>'
                    ),
                    (
                        '      <interest_under_house_property>'
                        f'{_escape_xml(salary_detail["interest_under_house_property"])}'
                        '</interest_under_house_property>'
                    ),
                    (
                        '      <approved_superannuation_fund>'
                        f'{_escape_xml(salary_detail["approved_superannuation_fund"])}'
                        '</approved_superannuation_fund>'
                    ),
                    '    </employee>',
                ]
            )
        xml_lines.append('  </annexure_ii_salary_details>')
    xml_lines.append('</form24q>')
    return '\n'.join(xml_lines) + '\n'


def generate_form24q_export(*, organisation, quarter: str, fiscal_year: str, payslips_by_employee: dict[str, list]) -> FilingGenerationResult:
    blockers: list[str] = []
    employee_rows: list[Form24QEmployeeRow] = []
    challan_rows: list[Form24QChallanRow] = []
    challan_xml_rows: list[Form24QChallanXmlRow] = []
    deductee_rows_by_period: dict[tuple[int, int], list[Form24QDeducteeXmlRow]] = {}
    annexure_ii_rows: list[Form24QAnnexureIIRow] = []
    period_tax_totals: dict[tuple[int, int], Decimal] = {}
    period_tax_breakdowns: dict[tuple[int, int], dict[str, Decimal]] = {}
    challan_map = _quarter_challan_map(organisation=organisation, fiscal_year=fiscal_year, quarter=quarter)
    challan_sequence_by_period = {
        period_key: sequence_number
        for sequence_number, period_key in enumerate(sorted(challan_map), start=1)
    }

    if not (organisation.tan_number or '').strip():
        blockers.append('Organisation TAN is required for Form 24Q export.')
    if _deductor_category(organisation) != 'STATUTORY_BODY_GOVERNMENT' and not (organisation.pan_number or '').strip():
        blockers.append('Organisation PAN is required for Form 24Q export for non-government deductors.')

    for employee_sequence, employee_key in enumerate(sorted(payslips_by_employee), start=1):
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
        latest_snapshot: dict[str, object] = {}
        challan_refs: list[Form24QChallanReference] = []
        for payslip in sorted(payslips, key=lambda item: (item.period_year, item.period_month)):
            snapshot = {**(payslip.pay_run_item.snapshot or {}), **(payslip.snapshot or {})}
            latest_snapshot = snapshot
            monthly_gross_salary = Decimal(str(snapshot.get('gross_pay', '0') or '0'))
            monthly_tax_deducted = Decimal(str(snapshot.get('income_tax', '0') or '0'))
            monthly_breakdown = _split_monthly_tds_components(snapshot, monthly_tax_deducted)
            gross_salary += monthly_gross_salary
            taxable_income = max(taxable_income, Decimal(str(snapshot.get('annual_taxable_after_sd', '0') or '0')))
            tax_deducted += monthly_tax_deducted
            cess += monthly_breakdown['health_and_education_cess']

            period_key = (payslip.period_year, payslip.period_month)
            period_tax_totals[period_key] = period_tax_totals.get(period_key, Decimal('0.00')) + monthly_tax_deducted
            period_breakdown = period_tax_breakdowns.setdefault(period_key, _empty_breakdown())
            for key, value in monthly_breakdown.items():
                period_breakdown[key] = (period_breakdown[key] + value).quantize(Decimal('0.01'))

            challan = challan_map.get(period_key)
            if challan is not None:
                challan_refs.append(
                    {
                        'period': f'{period_key[0]}-{period_key[1]:02d}',
                        'bsr_code': challan.bsr_code,
                        'challan_serial_number': challan.challan_serial_number,
                        'deposit_date': _format_form24q_date(challan.deposit_date),
                    }
                )
                deductee_rows_by_period.setdefault(period_key, []).append(
                    {
                        'deductee_sequence': len(deductee_rows_by_period.get(period_key, [])) + 1,
                        'employee_reference_number': employee.employee_code or str(employee.id),
                        'employee_id': str(employee.id),
                        'employee_code': employee.employee_code or '',
                        'employee_name': employee.user.full_name,
                        'employee_pan': pan_identifier,
                        'section_code': FORM24Q_DEFAULT_SECTION_CODE,
                        'payment_date': _format_form24q_date(_period_end_date(year=payslip.period_year, month=payslip.period_month)),
                        'deduction_date': _format_form24q_date(_period_end_date(year=payslip.period_year, month=payslip.period_month)),
                        'amount_paid_or_credited': decimal_to_string(monthly_gross_salary),
                        'tax_amount': decimal_to_string(monthly_breakdown['tax_amount']),
                        'surcharge_amount': decimal_to_string(monthly_breakdown['surcharge_amount']),
                        'health_and_education_cess': decimal_to_string(monthly_breakdown['health_and_education_cess']),
                        'total_tax_deducted': decimal_to_string(monthly_tax_deducted),
                        'total_tax_deposited': decimal_to_string(monthly_tax_deducted),
                        'deduction_reason_code': '',
                        'certificate_number': '',
                    }
                )

        summary: Form24QEmployeeRow = {
            'employee_sequence': employee_sequence,
            'employee_id': str(employee.id),
            'employee_code': employee.employee_code or '',
            'employee_name': employee.user.full_name,
            'employee_pan': pan_identifier,
            'section_code': FORM24Q_DEFAULT_SECTION_CODE,
            'gross_salary': decimal_to_string(gross_salary),
            'taxable_income': decimal_to_string(taxable_income),
            'tax_deducted': decimal_to_string(tax_deducted),
            'health_and_education_cess': decimal_to_string(cess),
            'pay_periods': [
                {'year': payslip.period_year, 'month': payslip.period_month}
                for payslip in sorted(payslips, key=lambda item: (item.period_year, item.period_month))
            ],
            'challan_refs': challan_refs,
        }
        employee_rows.append(summary)
        if quarter == 'Q4':
            annexure_ii_rows.append(
                _annexure_ii_payload(
                    employee=employee,
                    fiscal_year=fiscal_year,
                    summary=summary,
                    latest_snapshot=latest_snapshot,
                )
            )

    for period_key in sorted(period_tax_totals):
        period_label = f'{period_key[0]}-{period_key[1]:02d}'
        xml_period_label = f'{period_key[1]:02d}/{period_key[0]}'
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

        breakdown = period_tax_breakdowns.get(period_key, _empty_breakdown())
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
        challan_xml_rows.append(
            {
                'sequence_number': challan_sequence_by_period[period_key],
                'period': xml_period_label,
                'tax_amount': decimal_to_string(breakdown['tax_amount']),
                'surcharge_amount': decimal_to_string(breakdown['surcharge_amount']),
                'health_and_education_cess': decimal_to_string(breakdown['health_and_education_cess']),
                'interest_amount': decimal_to_string(challan.interest_amount),
                'fee_amount': decimal_to_string(challan.fee_amount),
                'other_amount': decimal_to_string('0.00'),
                'tax_deposited': decimal_to_string(challan.tax_deposited),
                'deposit_mode': 'C',
                'bsr_code': challan.bsr_code,
                'challan_serial_number': challan.challan_serial_number,
                'deposit_date': _format_form24q_date(challan.deposit_date),
                'minor_head': FORM24Q_DEFAULT_MINOR_HEAD,
                'statement_receipt_number': challan.statement_receipt_number,
                'deductee_rows': deductee_rows_by_period.get(period_key, []),
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
            'category': _deductor_category(organisation),
        },
        'responsible_person': _responsible_person_payload(organisation),
        'challans': challan_rows,
        'employees': employee_rows,
        'annexure_ii': annexure_ii_rows,
    }
    return FilingGenerationResult(
        artifact_format='XML',
        content_type='application/xml',
        file_name=f'form24q-{organisation.slug}-{fiscal_year}-{quarter.lower()}.xml',
        artifact_text='' if blockers else _render_form24q_xml(
            organisation=organisation,
            quarter=quarter,
            fiscal_year=fiscal_year,
            challans=challan_xml_rows,
            employees=employee_rows,
            annexure_ii=annexure_ii_rows,
        ),
        structured_payload=payload,
        metadata={
            'employee_count': len(employee_rows),
            'challan_count': len(challan_rows),
            'total_tax_deposited': decimal_to_string(
                sum((Decimal(row['tax_deposited']) for row in challan_rows), start=Decimal('0.00')),
                places='0.00',
            ),
            'schema_reference': FORM24Q_SCHEMA_REFERENCE,
            'data_structure_reference': FORM24Q_DATA_STRUCTURE_REFERENCE,
            'fvu_reference': FORM24Q_FVU_REFERENCE,
            'manual_release_checklist': [
                'Validate generated Form 24Q with the official Protean RPU 4.7 and FVU 9.0 utilities before customer use.',
            ],
        },
        validation_errors=sorted(blockers),
    )
