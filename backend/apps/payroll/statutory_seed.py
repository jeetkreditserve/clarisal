from __future__ import annotations

from datetime import date

from .models import (
    LabourWelfareFundContribution,
    LabourWelfareFundRule,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    ProfessionalTaxGender,
    ProfessionalTaxRule,
    ProfessionalTaxSlab,
    StatutoryDeductionFrequency,
    StatutoryIncomeBasis,
    TaxCategory,
)

ALL_MONTHS_EXCEPT_FEBRUARY = [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
APRIL_TO_FEBRUARY = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]


PROFESSIONAL_TAX_RULES = [
    {
        'country_code': 'IN',
        'state_code': 'MH',
        'state_name': 'Maharashtra',
        'income_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.MONTHLY,
        'effective_from': date(2023, 7, 1),
        'source_label': 'Maharashtra Profession Tax Act, 1975 Schedule I (amended in 2023)',
        'source_url': 'https://www.mahagst.gov.in/public/uploads/mvatservices/1760346808Maharashtra%20Profession%20Tax%20Act%201975.pdf',
        'notes': 'Salary-earner slabs only. Gender-specific thresholds and February adjustment retained.',
        'slabs': [
            {'gender': ProfessionalTaxGender.MALE, 'min_income': '0.00', 'max_income': '7500.00', 'deduction_amount': '0.00'},
            {'gender': ProfessionalTaxGender.MALE, 'min_income': '7500.01', 'max_income': '10000.00', 'deduction_amount': '175.00'},
            {
                'gender': ProfessionalTaxGender.MALE,
                'min_income': '10000.01',
                'max_income': None,
                'deduction_amount': '200.00',
                'applicable_months': ALL_MONTHS_EXCEPT_FEBRUARY,
            },
            {
                'gender': ProfessionalTaxGender.MALE,
                'min_income': '10000.01',
                'max_income': None,
                'deduction_amount': '300.00',
                'applicable_months': [2],
                'notes': 'February annual balancing month.',
            },
            {'gender': ProfessionalTaxGender.FEMALE, 'min_income': '0.00', 'max_income': '25000.00', 'deduction_amount': '0.00'},
            {
                'gender': ProfessionalTaxGender.FEMALE,
                'min_income': '25000.01',
                'max_income': None,
                'deduction_amount': '200.00',
                'applicable_months': ALL_MONTHS_EXCEPT_FEBRUARY,
            },
            {
                'gender': ProfessionalTaxGender.FEMALE,
                'min_income': '25000.01',
                'max_income': None,
                'deduction_amount': '300.00',
                'applicable_months': [2],
                'notes': 'February annual balancing month.',
            },
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'KA',
        'state_name': 'Karnataka',
        'income_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.MONTHLY,
        'effective_from': date(2025, 4, 15),
        'source_label': 'Karnataka PT employer FAQ',
        'source_url': 'https://ptax.karnataka.gov.in/ptemployer/FAQ',
        'notes': 'Salary-earner slabs only. Threshold reflects the current FAQ. February adjustment retained.',
        'slabs': [
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '0.00', 'max_income': '24999.99', 'deduction_amount': '0.00'},
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '25000.00',
                'max_income': None,
                'deduction_amount': '200.00',
                'applicable_months': ALL_MONTHS_EXCEPT_FEBRUARY,
            },
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '25000.00',
                'max_income': None,
                'deduction_amount': '300.00',
                'applicable_months': [2],
                'notes': 'February annual balancing month.',
            },
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'TN',
        'state_name': 'Tamil Nadu',
        'income_basis': StatutoryIncomeBasis.HALF_YEARLY,
        'deduction_frequency': StatutoryDeductionFrequency.HALF_YEARLY,
        'effective_from': date(2024, 10, 1),
        'source_label': 'Greater Chennai Corporation profession tax schedule',
        'source_url': 'https://chennaicorporation.gov.in/gcc/department/revenue/',
        'notes': 'Half-yearly salaried slab schedule as displayed by Greater Chennai Corporation.',
        'slabs': [
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '0.00', 'max_income': '21000.00', 'deduction_amount': '0.00', 'applicable_months': [9, 3]},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '21001.00', 'max_income': '30000.00', 'deduction_amount': '180.00', 'applicable_months': [9, 3]},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '30001.00', 'max_income': '45000.00', 'deduction_amount': '425.00', 'applicable_months': [9, 3]},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '45001.00', 'max_income': '60000.00', 'deduction_amount': '930.00', 'applicable_months': [9, 3]},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '60001.00', 'max_income': '75000.00', 'deduction_amount': '1025.00', 'applicable_months': [9, 3]},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '75001.00', 'max_income': None, 'deduction_amount': '1250.00', 'applicable_months': [9, 3]},
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'WB',
        'state_name': 'West Bengal',
        'income_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.MONTHLY,
        'effective_from': date(2014, 4, 1),
        'source_label': 'West Bengal PT schedule effective 1-4-2014',
        'source_url': 'https://comtax.wb.gov.in/Ptax-Schedule-New_%28w.e.f._1-4-2014%29.pdf',
        'notes': 'Salary-earner slabs only.',
        'slabs': [
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '0.00', 'max_income': '10000.00', 'deduction_amount': '0.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '10000.01', 'max_income': '15000.00', 'deduction_amount': '110.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '15000.01', 'max_income': '25000.00', 'deduction_amount': '130.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '25000.01', 'max_income': '40000.00', 'deduction_amount': '150.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '40000.01', 'max_income': None, 'deduction_amount': '200.00'},
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'AP',
        'state_name': 'Andhra Pradesh',
        'income_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.MONTHLY,
        'effective_from': date(2013, 2, 6),
        'source_label': 'Andhra Pradesh PT Act schedule (secondary legal text)',
        'source_url': 'https://indiankanoon.org/doc/36616956/',
        'notes': 'Salary-earner slabs only. Official AP tax portal schedule was not directly discoverable; this seed uses the published act text mirrored by Indian Kanoon.',
        'slabs': [
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '0.00', 'max_income': '15000.00', 'deduction_amount': '0.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '15001.00', 'max_income': '20000.00', 'deduction_amount': '150.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '20000.01', 'max_income': None, 'deduction_amount': '200.00'},
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'TG',
        'state_name': 'Telangana',
        'income_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.MONTHLY,
        'effective_from': date(2013, 2, 6),
        'source_label': 'Telangana PT schedule',
        'source_url': 'https://www.tgct.gov.in/tgportal/AllActs/APPT/APPTSchedule.aspx',
        'notes': 'Salary-earner slabs only.',
        'slabs': [
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '0.00', 'max_income': '15000.00', 'deduction_amount': '0.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '15001.00', 'max_income': '20000.00', 'deduction_amount': '150.00'},
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '20000.01', 'max_income': None, 'deduction_amount': '200.00'},
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'MP',
        'state_name': 'Madhya Pradesh',
        'income_basis': StatutoryIncomeBasis.ANNUAL,
        'deduction_frequency': StatutoryDeductionFrequency.MONTHLY,
        'effective_from': date(2018, 4, 1),
        'source_label': 'Madhya Pradesh PT schedule (secondary compliance reference)',
        'source_url': 'https://www.simpliance.in/professional-tax-detail/madhya-pradesh',
        'notes': 'Annual salary slabs represented as monthly deductions. March is treated as the twelfth balancing month.',
        'slabs': [
            {'gender': ProfessionalTaxGender.ANY, 'min_income': '0.00', 'max_income': '225000.00', 'deduction_amount': '0.00'},
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '225001.00',
                'max_income': '300000.00',
                'deduction_amount': '125.00',
                'applicable_months': APRIL_TO_FEBRUARY + [3],
            },
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '300001.00',
                'max_income': '400000.00',
                'deduction_amount': '166.00',
                'applicable_months': APRIL_TO_FEBRUARY,
            },
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '300001.00',
                'max_income': '400000.00',
                'deduction_amount': '174.00',
                'applicable_months': [3],
                'notes': 'Twelfth balancing month.',
            },
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '400001.00',
                'max_income': None,
                'deduction_amount': '208.00',
                'applicable_months': APRIL_TO_FEBRUARY,
            },
            {
                'gender': ProfessionalTaxGender.ANY,
                'min_income': '400001.00',
                'max_income': None,
                'deduction_amount': '212.00',
                'applicable_months': [3],
                'notes': 'Twelfth balancing month.',
            },
        ],
    },
]


LABOUR_WELFARE_FUND_RULES = [
    {
        'country_code': 'IN',
        'state_code': 'MH',
        'state_name': 'Maharashtra',
        'wage_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.HALF_YEARLY,
        'effective_from': date(1984, 6, 23),
        'source_label': 'Maharashtra Labour Welfare Fund Form A-1',
        'source_url': 'https://mail.mlwb.in/pdf/form_a1_english.pdf',
        'notes': 'Half-yearly contribution. June and December deduction months retained.',
        'contributions': [
            {
                'min_wage': '0.00',
                'max_wage': '2999.99',
                'employee_amount': '6.00',
                'employer_amount': '18.00',
                'applicable_months': [6, 12],
            },
            {
                'min_wage': '3000.00',
                'max_wage': None,
                'employee_amount': '12.00',
                'employer_amount': '36.00',
                'applicable_months': [6, 12],
            },
        ],
    },
    {
        'country_code': 'IN',
        'state_code': 'KA',
        'state_name': 'Karnataka',
        'wage_basis': StatutoryIncomeBasis.MONTHLY,
        'deduction_frequency': StatutoryDeductionFrequency.ANNUAL,
        'effective_from': date(2025, 1, 1),
        'source_label': 'Karnataka Labour Welfare Board Form-D for calendar year 2025',
        'source_url': 'https://klwbapps.karnataka.gov.in/FormD2025English',
        'notes': 'Annual contribution for calendar year 2025 as published by the Karnataka Labour Welfare Board.',
        'contributions': [
            {
                'min_wage': None,
                'max_wage': None,
                'employee_amount': '20.00',
                'employer_amount': '40.00',
                'applicable_months': [12],
            },
        ],
    },
]


# ─── Income Tax Slab Masters ──────────────────────────────────────────────────
# Source: Finance Act 2024 (AY 2024-25) and Finance Act 2025 (AY 2025-26).
# New Regime: all three age categories share identical slabs (Section 115BAC).
# Old Regime: Individual < 2.5 L; Senior Citizen (60-79) < 3 L; Super Senior (80+) < 5 L.
# Amounts are annual income in INR.

_NEW_REGIME_2024_SLABS = [
    {'min_income': '0.00',        'max_income': '300000.00',   'rate_percent': '0.00'},
    {'min_income': '300000.00',   'max_income': '700000.00',   'rate_percent': '5.00'},
    {'min_income': '700000.00',   'max_income': '1000000.00',  'rate_percent': '10.00'},
    {'min_income': '1000000.00',  'max_income': '1200000.00',  'rate_percent': '15.00'},
    {'min_income': '1200000.00',  'max_income': '1500000.00',  'rate_percent': '20.00'},
    {'min_income': '1500000.00',  'max_income': None,           'rate_percent': '30.00'},
]

_NEW_REGIME_2025_SLABS = [
    {'min_income': '0.00',        'max_income': '400000.00',   'rate_percent': '0.00'},
    {'min_income': '400000.00',   'max_income': '800000.00',   'rate_percent': '5.00'},
    {'min_income': '800000.00',   'max_income': '1200000.00',  'rate_percent': '10.00'},
    {'min_income': '1200000.00',  'max_income': '1600000.00',  'rate_percent': '15.00'},
    {'min_income': '1600000.00',  'max_income': '2000000.00',  'rate_percent': '20.00'},
    {'min_income': '2000000.00',  'max_income': '2400000.00',  'rate_percent': '25.00'},
    {'min_income': '2400000.00',  'max_income': None,           'rate_percent': '30.00'},
]

INCOME_TAX_SLAB_MASTERS = [
    # ── FY 2024-2025 ─────────────────────────────────────────────────────────
    {
        'fiscal_year': '2024-2025', 'country_code': 'IN', 'is_old_regime': False,
        'tax_category': TaxCategory.INDIVIDUAL,
        'name': 'India New Regime 2024-2025 (Individual)',
        'slabs': _NEW_REGIME_2024_SLABS,
    },
    {
        'fiscal_year': '2024-2025', 'country_code': 'IN', 'is_old_regime': False,
        'tax_category': TaxCategory.SENIOR_CITIZEN,
        'name': 'India New Regime 2024-2025 (Senior Citizen)',
        'slabs': _NEW_REGIME_2024_SLABS,
    },
    {
        'fiscal_year': '2024-2025', 'country_code': 'IN', 'is_old_regime': False,
        'tax_category': TaxCategory.SUPER_SENIOR_CITIZEN,
        'name': 'India New Regime 2024-2025 (Super Senior Citizen)',
        'slabs': _NEW_REGIME_2024_SLABS,
    },
    {
        'fiscal_year': '2024-2025', 'country_code': 'IN', 'is_old_regime': True,
        'tax_category': TaxCategory.INDIVIDUAL,
        'name': 'India Old Regime 2024-2025 (Individual)',
        'slabs': [
            {'min_income': '0.00',       'max_income': '250000.00',   'rate_percent': '0.00'},
            {'min_income': '250000.00',  'max_income': '500000.00',   'rate_percent': '5.00'},
            {'min_income': '500000.00',  'max_income': '1000000.00',  'rate_percent': '20.00'},
            {'min_income': '1000000.00', 'max_income': None,           'rate_percent': '30.00'},
        ],
    },
    {
        'fiscal_year': '2024-2025', 'country_code': 'IN', 'is_old_regime': True,
        'tax_category': TaxCategory.SENIOR_CITIZEN,
        'name': 'India Old Regime 2024-2025 (Senior Citizen)',
        'slabs': [
            {'min_income': '0.00',       'max_income': '300000.00',   'rate_percent': '0.00'},
            {'min_income': '300000.00',  'max_income': '500000.00',   'rate_percent': '5.00'},
            {'min_income': '500000.00',  'max_income': '1000000.00',  'rate_percent': '20.00'},
            {'min_income': '1000000.00', 'max_income': None,           'rate_percent': '30.00'},
        ],
    },
    {
        'fiscal_year': '2024-2025', 'country_code': 'IN', 'is_old_regime': True,
        'tax_category': TaxCategory.SUPER_SENIOR_CITIZEN,
        'name': 'India Old Regime 2024-2025 (Super Senior Citizen)',
        'slabs': [
            {'min_income': '0.00',       'max_income': '500000.00',   'rate_percent': '0.00'},
            {'min_income': '500000.00',  'max_income': '1000000.00',  'rate_percent': '20.00'},
            {'min_income': '1000000.00', 'max_income': None,           'rate_percent': '30.00'},
        ],
    },
    # ── FY 2025-2026 ─────────────────────────────────────────────────────────
    {
        'fiscal_year': '2025-2026', 'country_code': 'IN', 'is_old_regime': False,
        'tax_category': TaxCategory.INDIVIDUAL,
        'name': 'India New Regime 2025-2026 (Individual)',
        'slabs': _NEW_REGIME_2025_SLABS,
    },
    {
        'fiscal_year': '2025-2026', 'country_code': 'IN', 'is_old_regime': False,
        'tax_category': TaxCategory.SENIOR_CITIZEN,
        'name': 'India New Regime 2025-2026 (Senior Citizen)',
        'slabs': _NEW_REGIME_2025_SLABS,
    },
    {
        'fiscal_year': '2025-2026', 'country_code': 'IN', 'is_old_regime': False,
        'tax_category': TaxCategory.SUPER_SENIOR_CITIZEN,
        'name': 'India New Regime 2025-2026 (Super Senior Citizen)',
        'slabs': _NEW_REGIME_2025_SLABS,
    },
    {
        'fiscal_year': '2025-2026', 'country_code': 'IN', 'is_old_regime': True,
        'tax_category': TaxCategory.INDIVIDUAL,
        'name': 'India Old Regime 2025-2026 (Individual)',
        'slabs': [
            {'min_income': '0.00',       'max_income': '250000.00',   'rate_percent': '0.00'},
            {'min_income': '250000.00',  'max_income': '500000.00',   'rate_percent': '5.00'},
            {'min_income': '500000.00',  'max_income': '1000000.00',  'rate_percent': '20.00'},
            {'min_income': '1000000.00', 'max_income': None,           'rate_percent': '30.00'},
        ],
    },
    {
        'fiscal_year': '2025-2026', 'country_code': 'IN', 'is_old_regime': True,
        'tax_category': TaxCategory.SENIOR_CITIZEN,
        'name': 'India Old Regime 2025-2026 (Senior Citizen)',
        'slabs': [
            {'min_income': '0.00',       'max_income': '300000.00',   'rate_percent': '0.00'},
            {'min_income': '300000.00',  'max_income': '500000.00',   'rate_percent': '5.00'},
            {'min_income': '500000.00',  'max_income': '1000000.00',  'rate_percent': '20.00'},
            {'min_income': '1000000.00', 'max_income': None,           'rate_percent': '30.00'},
        ],
    },
    {
        'fiscal_year': '2025-2026', 'country_code': 'IN', 'is_old_regime': True,
        'tax_category': TaxCategory.SUPER_SENIOR_CITIZEN,
        'name': 'India Old Regime 2025-2026 (Super Senior Citizen)',
        'slabs': [
            {'min_income': '0.00',       'max_income': '500000.00',   'rate_percent': '0.00'},
            {'min_income': '500000.00',  'max_income': '1000000.00',  'rate_percent': '20.00'},
            {'min_income': '1000000.00', 'max_income': None,           'rate_percent': '30.00'},
        ],
    },
]


def seed_income_tax_masters():
    """Idempotent seed of all CT-level income tax slab sets defined in INCOME_TAX_SLAB_MASTERS."""
    count = 0
    for master_data in INCOME_TAX_SLAB_MASTERS:
        slabs = master_data['slabs']
        slab_set, _ = PayrollTaxSlabSet.objects.update_or_create(
            organisation=None,
            country_code=master_data['country_code'],
            fiscal_year=master_data['fiscal_year'],
            is_old_regime=master_data['is_old_regime'],
            tax_category=master_data['tax_category'],
            defaults={
                'name': master_data['name'],
                'is_system_master': True,
                'is_active': True,
            },
        )
        slab_set.slabs.all().delete()
        PayrollTaxSlab.objects.bulk_create([
            PayrollTaxSlab(
                slab_set=slab_set,
                min_income=slab['min_income'],
                max_income=slab.get('max_income'),
                rate_percent=slab['rate_percent'],
            )
            for slab in slabs
        ])
        count += 1
    return count


def seed_statutory_master_data():
    pt_count = 0
    lwf_count = 0
    for rule_data in PROFESSIONAL_TAX_RULES:
        slabs = rule_data['slabs']
        defaults = {key: value for key, value in rule_data.items() if key != 'slabs'}
        rule, _ = ProfessionalTaxRule.objects.update_or_create(
            country_code=rule_data['country_code'],
            state_code=rule_data['state_code'],
            effective_from=rule_data['effective_from'],
            defaults=defaults,
        )
        rule.slabs.all().delete()
        ProfessionalTaxSlab.objects.bulk_create(
            [
                ProfessionalTaxSlab(
                    rule=rule,
                    gender=slab.get('gender'),
                    min_income=slab['min_income'],
                    max_income=slab.get('max_income'),
                    deduction_amount=slab['deduction_amount'],
                    applicable_months=slab.get('applicable_months', []),
                    notes=slab.get('notes', ''),
                )
                for slab in slabs
            ]
        )
        pt_count += 1

    for rule_data in LABOUR_WELFARE_FUND_RULES:
        contributions = rule_data['contributions']
        defaults = {key: value for key, value in rule_data.items() if key != 'contributions'}
        rule, _ = LabourWelfareFundRule.objects.update_or_create(
            country_code=rule_data['country_code'],
            state_code=rule_data['state_code'],
            effective_from=rule_data['effective_from'],
            defaults=defaults,
        )
        rule.contributions.all().delete()
        LabourWelfareFundContribution.objects.bulk_create(
            [
                LabourWelfareFundContribution(
                    rule=rule,
                    min_wage=contribution.get('min_wage'),
                    max_wage=contribution.get('max_wage'),
                    employee_amount=contribution['employee_amount'],
                    employer_amount=contribution['employer_amount'],
                    applicable_months=contribution.get('applicable_months', []),
                    notes=contribution.get('notes', ''),
                )
                for contribution in contributions
            ]
        )
        lwf_count += 1

    it_count = seed_income_tax_masters()
    return {'professional_tax_rules': pt_count, 'labour_welfare_fund_rules': lwf_count, 'income_tax_masters': it_count}
