from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date
from decimal import Decimal

ZERO = Decimal('0.00')

# India statutory defaults.
INDIA_STANDARD_DEDUCTION = Decimal('75000.00')
INDIA_CESS_RATE = Decimal('0.04')
INDIA_REBATE_87A_MAX = Decimal('25000.00')
INDIA_REBATE_87A_THRESHOLD = Decimal('700000.00')
PF_RATE = Decimal('0.12')
PF_WAGE_CEILING = Decimal('15000.00')
ESI_EMPLOYEE_RATE = Decimal('0.0075')
ESI_EMPLOYER_RATE = Decimal('0.0325')
ESI_WAGE_CEILING = Decimal('21000.00')
GRATUITY_STATUTORY_CEILING = Decimal('2000000.00')
NEW_REGIME_SURCHARGE_TIERS = (
    (Decimal('5000000.00'), Decimal('0.10')),
    (Decimal('10000000.00'), Decimal('0.15')),
    (Decimal('20000000.00'), Decimal('0.25')),
)
OLD_REGIME_SURCHARGE_TIERS = (
    (Decimal('5000000.00'), Decimal('0.10')),
    (Decimal('10000000.00'), Decimal('0.15')),
    (Decimal('20000000.00'), Decimal('0.25')),
    (Decimal('50000000.00'), Decimal('0.37')),
)

def normalize_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal('0.01'))
    return Decimal(str(value)).quantize(Decimal('0.01'))


def calculate_annual_tax(tax_slab_set, annual_taxable_income):
    taxable = normalize_decimal(annual_taxable_income) or ZERO
    annual_tax = ZERO
    for slab in tax_slab_set.slabs.order_by('min_income', 'created_at'):
        slab_start = slab.min_income
        slab_end = slab.max_income
        if taxable <= slab_start:
            continue
        upper_bound = taxable if slab_end is None else min(taxable, slab_end)
        taxable_slice = upper_bound - slab_start
        if taxable_slice <= ZERO:
            continue
        annual_tax += taxable_slice * (slab.rate_percent / Decimal('100.00'))
        if slab_end is None or taxable <= slab_end:
            break
    return annual_tax.quantize(Decimal('0.01'))


def calculate_taxable_income_after_standard_deduction(gross_taxable_income):
    taxable_income = (normalize_decimal(gross_taxable_income) or ZERO) - INDIA_STANDARD_DEDUCTION
    return max(ZERO, taxable_income).quantize(Decimal('0.01'))


def apply_cess(tax_before_cess):
    base_tax = normalize_decimal(tax_before_cess) or ZERO
    return (base_tax * (Decimal('1.00') + INDIA_CESS_RATE)).quantize(Decimal('0.01'))


def calculate_surcharge(*, taxable_income, tax_after_rebate, surcharge_tiers=None):
    income = normalize_decimal(taxable_income) or ZERO
    surcharge_base = normalize_decimal(tax_after_rebate) or ZERO
    surcharge = ZERO
    for threshold, rate in sorted(surcharge_tiers or [], key=lambda item: item[0]):
        if income > threshold:
            surcharge = surcharge_base * rate
        else:
            break
    return surcharge.quantize(Decimal('0.01'))


def surcharge_tiers_for_regime(tax_regime: str):
    return OLD_REGIME_SURCHARGE_TIERS if str(tax_regime).upper() == 'OLD' else NEW_REGIME_SURCHARGE_TIERS


def calculate_income_tax_with_rebate(*, taxable_income, tax_slab_set, surcharge_tiers=None):
    annual_taxable_income = normalize_decimal(taxable_income) or ZERO
    tax_before_rebate = calculate_annual_tax(tax_slab_set, annual_taxable_income)
    rebate_87a = ZERO
    if annual_taxable_income <= INDIA_REBATE_87A_THRESHOLD:
        rebate_87a = min(tax_before_rebate, INDIA_REBATE_87A_MAX).quantize(Decimal('0.01'))
    tax_after_rebate = max(ZERO, tax_before_rebate - rebate_87a).quantize(Decimal('0.01'))
    surcharge = calculate_surcharge(
        taxable_income=annual_taxable_income,
        tax_after_rebate=tax_after_rebate,
        surcharge_tiers=surcharge_tiers,
    )
    current_tier = None
    for threshold, rate in sorted(surcharge_tiers or [], key=lambda item: item[0]):
        if annual_taxable_income > threshold:
            current_tier = (threshold, rate)
        else:
            break
    if current_tier is not None:
        threshold, _rate = current_tier
        threshold_tax_before_rebate = calculate_annual_tax(tax_slab_set, threshold)
        threshold_rebate = ZERO
        if threshold <= INDIA_REBATE_87A_THRESHOLD:
            threshold_rebate = min(threshold_tax_before_rebate, INDIA_REBATE_87A_MAX).quantize(Decimal('0.01'))
        threshold_tax_after_rebate = max(ZERO, threshold_tax_before_rebate - threshold_rebate).quantize(Decimal('0.01'))
        threshold_surcharge = calculate_surcharge(
            taxable_income=threshold,
            tax_after_rebate=threshold_tax_after_rebate,
            surcharge_tiers=surcharge_tiers,
        )
        threshold_total_before_cess = (threshold_tax_after_rebate + threshold_surcharge).quantize(Decimal('0.01'))
        max_total_before_cess = (threshold_total_before_cess + (annual_taxable_income - threshold)).quantize(Decimal('0.01'))
        current_total_before_cess = (tax_after_rebate + surcharge).quantize(Decimal('0.01'))
        if current_total_before_cess > max_total_before_cess:
            surcharge = max(ZERO, max_total_before_cess - tax_after_rebate).quantize(Decimal('0.01'))
    tax_before_cess = (tax_after_rebate + surcharge).quantize(Decimal('0.01'))
    cess = (tax_before_cess * INDIA_CESS_RATE).quantize(Decimal('0.01'))
    annual_tax = apply_cess(tax_before_cess)
    return {
        'tax_before_rebate': tax_before_rebate,
        'rebate_87a': rebate_87a,
        'tax_after_rebate': tax_before_cess,
        'surcharge': surcharge,
        'cess': cess,
        'annual_tax': annual_tax,
    }


def ensure_non_negative_net_pay(net_pay):
    normalized_net_pay = normalize_decimal(net_pay) or ZERO
    if normalized_net_pay < ZERO:
        logging.getLogger(__name__).warning(
            'Net pay calculated as negative (%s). Clamping to zero. Check deduction components.',
            normalized_net_pay,
        )
    return max(ZERO, normalized_net_pay).quantize(Decimal('0.01'))


def calculate_epf_contributions(
    *,
    basic_pay,
    employee_rate: Decimal = PF_RATE,
    employer_rate: Decimal = PF_RATE,
    wage_ceiling: Decimal | None = None,
    cap_wages: bool = False,
):
    basic = normalize_decimal(basic_pay) or ZERO
    eligible_basic = min(basic, wage_ceiling) if cap_wages and wage_ceiling is not None else basic
    return {
        'eligible_basic': eligible_basic.quantize(Decimal('0.01')),
        'employee': (eligible_basic * employee_rate).quantize(Decimal('0.01')),
        'employer': (eligible_basic * employer_rate).quantize(Decimal('0.01')),
    }


def calculate_esi_contributions(
    *,
    gross_pay,
    employee_rate: Decimal = ESI_EMPLOYEE_RATE,
    employer_rate: Decimal = ESI_EMPLOYER_RATE,
    wage_ceiling: Decimal = ESI_WAGE_CEILING,
    force_eligible: bool = False,
):
    gross = normalize_decimal(gross_pay) or ZERO
    is_applicable = force_eligible or gross <= wage_ceiling
    if not is_applicable:
        return {'employee': ZERO, 'employer': ZERO, 'is_applicable': False}
    return {
        'employee': (gross * employee_rate).quantize(Decimal('0.01')),
        'employer': (gross * employer_rate).quantize(Decimal('0.01')),
        'is_applicable': True,
    }


def get_esi_contribution_period_bounds(period_year: int, period_month: int):
    if 4 <= period_month <= 9:
        return date(period_year, 4, 1), date(period_year, 9, 30)
    if period_month >= 10:
        return date(period_year, 10, 1), date(period_year + 1, 3, 31)
    return date(period_year - 1, 10, 1), date(period_year, 3, 31)


def calculate_professional_tax_monthly(gross_monthly, state_code='MH', slabs_by_state=None):
    gross = normalize_decimal(gross_monthly) or ZERO
    state = (state_code or '').upper()
    slabs = (slabs_by_state or {}).get(state, [])
    for ceiling, amount in slabs:
        if ceiling is None or gross < ceiling:
            return amount
    return ZERO


def _statutory_row_value(row, field_name):
    if isinstance(row, dict):
        return row.get(field_name)
    return getattr(row, field_name, None)


def calculate_labour_welfare_fund(*, state_code, payroll_month, gross_pay, contributions=None):
    gross = normalize_decimal(gross_pay) or ZERO
    for contribution in contributions or []:
        applicable_months = list(_statutory_row_value(contribution, 'applicable_months') or [])
        if applicable_months and payroll_month not in applicable_months:
            continue
        min_wage = normalize_decimal(_statutory_row_value(contribution, 'min_wage'))
        max_wage = normalize_decimal(_statutory_row_value(contribution, 'max_wage'))
        if min_wage is not None and gross < min_wage:
            continue
        if max_wage is not None and gross > max_wage:
            continue
        return {
            'employee': normalize_decimal(_statutory_row_value(contribution, 'employee_amount')) or ZERO,
            'employer': normalize_decimal(_statutory_row_value(contribution, 'employer_amount')) or ZERO,
            'is_applicable': True,
            'state_code': (state_code or '').upper(),
            'payroll_month': payroll_month,
            'gross_pay': gross,
        }
    return {
        'employee': ZERO,
        'employer': ZERO,
        'is_applicable': False,
        'state_code': (state_code or '').upper(),
        'payroll_month': payroll_month,
        'gross_pay': gross,
    }


def calculate_gratuity_service_years(*, date_of_joining, last_working_day):
    if date_of_joining is None or last_working_day is None or last_working_day < date_of_joining:
        return 0

    years = last_working_day.year - date_of_joining.year
    months = last_working_day.month - date_of_joining.month
    days = last_working_day.day - date_of_joining.day

    if days < 0:
        months -= 1
        previous_month = 12 if last_working_day.month == 1 else last_working_day.month - 1
        previous_month_year = last_working_day.year - 1 if last_working_day.month == 1 else last_working_day.year
        days += monthrange(previous_month_year, previous_month)[1]
    if months < 0:
        years -= 1
        months += 12

    if months > 6 or (months == 6 and days > 0):
        years += 1
    return max(years, 0)


def calculate_gratuity_amount(
    *,
    last_basic_salary,
    years_of_service,
    eligibility_years: int = 5,
    statutory_ceiling: Decimal = GRATUITY_STATUTORY_CEILING,
):
    basic = normalize_decimal(last_basic_salary) or ZERO
    service_years = int(years_of_service)
    if service_years < eligibility_years or basic <= ZERO:
        return ZERO
    gratuity = ((basic / Decimal('26.00')) * Decimal('15.00') * Decimal(str(service_years))).quantize(Decimal('0.01'))
    return min(gratuity, statutory_ceiling).quantize(Decimal('0.01'))


def calculate_fnf_salary_proration(
    gross_monthly_salary: Decimal,
    last_working_day: date,
    period_year: int,
    period_month: int,
) -> Decimal:
    total_days = Decimal(str(monthrange(period_year, period_month)[1]))
    paid_days = Decimal(str(last_working_day.day))
    salary = normalize_decimal(gross_monthly_salary) or ZERO
    return (salary * paid_days / total_days).quantize(Decimal('0.01'))


def calculate_leave_encashment_amount(
    leave_days: Decimal,
    monthly_basic_salary: Decimal,
) -> Decimal:
    per_day_basic = ((normalize_decimal(monthly_basic_salary) or ZERO) / Decimal('26')).quantize(Decimal('0.01'))
    encashment_days = normalize_decimal(leave_days) or ZERO
    return (encashment_days * per_day_basic).quantize(Decimal('0.01'))
