from datetime import date
from decimal import Decimal

import pytest

from apps.payroll.models import PayrollTaxSlab, PayrollTaxSlabSet
from apps.payroll.statutory import (
    NEW_REGIME_SURCHARGE_TIERS,
    OLD_REGIME_SURCHARGE_TIERS,
    PF_WAGE_CEILING,
    apply_cess,
    calculate_annual_tax,
    calculate_epf_contributions,
    calculate_esi_contributions,
    calculate_gratuity_amount,
    calculate_gratuity_service_years,
    calculate_income_tax_with_rebate,
    calculate_labour_welfare_fund,
    calculate_professional_tax_monthly,
    calculate_taxable_income_after_standard_deduction,
    ensure_non_negative_net_pay,
    get_esi_contribution_period_bounds,
    get_rebate_87a_params,
    normalize_decimal,
)


@pytest.fixture
def india_new_regime_slabs(db):
    slab_set = PayrollTaxSlabSet.objects.create(
        name='India New Regime FY2024-25',
        country_code='IN',
        fiscal_year='2024-25',
        is_active=True,
        is_system_master=True,
    )
    slabs = [
        (0, 300000, Decimal('0')),
        (300000, 700000, Decimal('5')),
        (700000, 1000000, Decimal('10')),
        (1000000, 1200000, Decimal('15')),
        (1200000, 1500000, Decimal('20')),
        (1500000, None, Decimal('30')),
    ]
    for min_income, max_income, rate in slabs:
        PayrollTaxSlab.objects.create(
            slab_set=slab_set,
            min_income=Decimal(str(min_income)),
            max_income=Decimal(str(max_income)) if max_income is not None else None,
            rate_percent=rate,
        )
    return slab_set


@pytest.fixture
def india_old_regime_slabs(db):
    slab_set = PayrollTaxSlabSet.objects.create(
        name='India Old Regime FY2024-25',
        country_code='IN',
        fiscal_year='2024-25',
        is_active=True,
        is_system_master=False,
        is_old_regime=True,
    )
    slabs = [
        (0, 250000, Decimal('0')),
        (250000, 500000, Decimal('5')),
        (500000, 1000000, Decimal('20')),
        (1000000, None, Decimal('30')),
    ]
    for min_income, max_income, rate in slabs:
        PayrollTaxSlab.objects.create(
            slab_set=slab_set,
            min_income=Decimal(str(min_income)),
            max_income=Decimal(str(max_income)) if max_income is not None else None,
            rate_percent=rate,
        )
    return slab_set


@pytest.fixture
def india_new_regime_fy2025_26_slabs(db):
    slab_set = PayrollTaxSlabSet.objects.create(
        name='India New Regime FY2025-26',
        country_code='IN',
        fiscal_year='2025-26',
        is_active=True,
        is_system_master=True,
    )
    slabs = [
        (0, 400000, Decimal('0')),
        (400000, 800000, Decimal('5')),
        (800000, 1200000, Decimal('10')),
        (1200000, 1600000, Decimal('15')),
        (1600000, 2000000, Decimal('20')),
        (2000000, 2400000, Decimal('25')),
        (2400000, None, Decimal('30')),
    ]
    for min_income, max_income, rate in slabs:
        PayrollTaxSlab.objects.create(
            slab_set=slab_set,
            min_income=Decimal(str(min_income)),
            max_income=Decimal(str(max_income)) if max_income is not None else None,
            rate_percent=rate,
        )
    return slab_set


class TestSection87ARebate:
    def test_income_5_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('500000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] == Decimal('0.00')
        assert result['rebate_87a'] == Decimal('10000.00')

    def test_income_6_5_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('650000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] == Decimal('0.00')
        assert result['rebate_87a'] == Decimal('17500.00')

    def test_income_exactly_7_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('700000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] == Decimal('0.00')
        assert result['rebate_87a'] == Decimal('20000.00')

    def test_income_above_7_lakh_does_not_get_rebate(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('700001'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] > Decimal('0.00')
        assert result['rebate_87a'] == Decimal('0.00')

    def test_income_10_lakh_has_cess_and_no_rebate(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('1000000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['rebate_87a'] == Decimal('0.00')
        assert result['annual_tax'] == Decimal('52000.00')

    @pytest.mark.parametrize(
        ('threshold', 'tiers'),
        [
            (Decimal('5000000.00'), NEW_REGIME_SURCHARGE_TIERS),
            (Decimal('10000000.00'), NEW_REGIME_SURCHARGE_TIERS),
            (Decimal('20000000.00'), NEW_REGIME_SURCHARGE_TIERS),
        ],
    )
    def test_new_regime_surcharge_marginal_relief_holds_at_boundary_plus_one(self, india_new_regime_slabs, threshold, tiers):
        at_threshold = calculate_income_tax_with_rebate(
            taxable_income=threshold,
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )
        just_above = calculate_income_tax_with_rebate(
            taxable_income=threshold + Decimal('1.00'),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )

        assert just_above['tax_after_rebate'] == at_threshold['tax_after_rebate'] + Decimal('1.00')
        assert just_above['annual_tax'] == apply_cess(at_threshold['tax_after_rebate'] + Decimal('1.00'))

    def test_new_regime_applies_25_percent_surcharge_above_two_crore_before_cess(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('30000000.00'),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=NEW_REGIME_SURCHARGE_TIERS,
        )

        assert result['tax_before_rebate'] == Decimal('8690000.00')
        assert result['surcharge'] == Decimal('2172500.00')
        assert result['tax_after_rebate'] == Decimal('10862500.00')
        assert result['cess'] == Decimal('434500.00')
        assert result['annual_tax'] == Decimal('11297000.00')

    @pytest.mark.parametrize(
        ('threshold', 'tiers'),
        [
            (Decimal('5000000.00'), OLD_REGIME_SURCHARGE_TIERS),
            (Decimal('10000000.00'), OLD_REGIME_SURCHARGE_TIERS),
            (Decimal('20000000.00'), OLD_REGIME_SURCHARGE_TIERS),
            (Decimal('50000000.00'), OLD_REGIME_SURCHARGE_TIERS),
        ],
    )
    def test_old_regime_surcharge_marginal_relief_holds_at_boundary_plus_one(self, india_old_regime_slabs, threshold, tiers):
        at_threshold = calculate_income_tax_with_rebate(
            taxable_income=threshold,
            tax_slab_set=india_old_regime_slabs,
            surcharge_tiers=tiers,
        )
        just_above = calculate_income_tax_with_rebate(
            taxable_income=threshold + Decimal('1.00'),
            tax_slab_set=india_old_regime_slabs,
            surcharge_tiers=tiers,
        )

        assert just_above['tax_after_rebate'] == at_threshold['tax_after_rebate'] + Decimal('1.00')
        assert just_above['annual_tax'] == apply_cess(at_threshold['tax_after_rebate'] + Decimal('1.00'))

    def test_old_regime_applies_37_percent_surcharge_above_five_crore_before_cess(self, india_old_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('60000000.00'),
            tax_slab_set=india_old_regime_slabs,
            surcharge_tiers=OLD_REGIME_SURCHARGE_TIERS,
        )

        assert result['tax_before_rebate'] == Decimal('17812500.00')
        assert result['surcharge'] == Decimal('6590625.00')
        assert result['tax_after_rebate'] == Decimal('24403125.00')
        assert result['cess'] == Decimal('976125.00')
        assert result['annual_tax'] == Decimal('25379250.00')

    def test_fy25_26_new_regime_uses_12_lakh_rebate_threshold(self, india_new_regime_fy2025_26_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('1000000.00'),
            tax_slab_set=india_new_regime_fy2025_26_slabs,
        )

        assert result['rebate_87a'] == Decimal('40000.00')
        assert result['annual_tax'] == Decimal('0.00')

    def test_fy25_26_new_regime_zeroes_tax_at_12_lakh(self, india_new_regime_fy2025_26_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('1200000.00'),
            tax_slab_set=india_new_regime_fy2025_26_slabs,
        )

        assert result['rebate_87a'] == Decimal('60000.00')
        assert result['annual_tax'] == Decimal('0.00')

    def test_fy25_26_new_regime_removes_rebate_above_12_lakh(self, india_new_regime_fy2025_26_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('1200001.00'),
            tax_slab_set=india_new_regime_fy2025_26_slabs,
        )

        assert result['rebate_87a'] == Decimal('0.00')
        assert result['annual_tax'] > Decimal('0.00')

    def test_get_rebate_87a_params_keeps_old_regime_threshold_unchanged(self):
        assert get_rebate_87a_params('2024-2025', 'OLD') == (Decimal('500000.00'), Decimal('12500.00'))
        assert get_rebate_87a_params('2025-2026', 'OLD') == (Decimal('500000.00'), Decimal('12500.00'))


class TestTaxHelpers:
    def test_normalize_decimal_handles_non_decimal_values(self):
        assert normalize_decimal('12.345') == Decimal('12.34')

    def test_standard_deduction_subtracted(self):
        assert calculate_taxable_income_after_standard_deduction(Decimal('1000000')) == Decimal('925000.00')

    def test_standard_deduction_never_returns_negative(self):
        assert calculate_taxable_income_after_standard_deduction(Decimal('50000')) == Decimal('0.00')

    def test_cess_applied_after_tax(self):
        assert apply_cess(Decimal('50000.00')) == Decimal('52000.00')

    def test_epf_defaults_to_uncapped_current_behavior(self):
        result = calculate_epf_contributions(basic_pay=Decimal('50000.00'))

        assert result['eligible_basic'] == Decimal('50000.00')
        assert result['employee'] == Decimal('6000.00')
        assert result['employer'] == Decimal('6000.00')

    def test_epf_can_cap_eligible_wages_when_requested(self):
        result = calculate_epf_contributions(
            basic_pay=Decimal('50000.00'),
            wage_ceiling=PF_WAGE_CEILING,
            cap_wages=True,
        )

        assert result['eligible_basic'] == Decimal('15000.00')
        assert result['employee'] == Decimal('1800.00')
        assert result['employer'] == Decimal('1800.00')

    def test_esi_returns_zero_above_ceiling_without_force_flag(self):
        result = calculate_esi_contributions(gross_pay=Decimal('21000.01'))

        assert result['is_applicable'] is False
        assert result['employee'] == Decimal('0.00')
        assert result['employer'] == Decimal('0.00')

    def test_esi_can_be_forced_for_contribution_period_continuity(self):
        result = calculate_esi_contributions(
            gross_pay=Decimal('25000.00'),
            force_eligible=True,
        )

        assert result['is_applicable'] is True
        assert result['employee'] == Decimal('187.50')
        assert result['employer'] == Decimal('812.50')

    def test_esi_contribution_period_bounds_follow_half_year_windows(self):
        assert get_esi_contribution_period_bounds(2026, 4) == (date(2026, 4, 1), date(2026, 9, 30))
        assert get_esi_contribution_period_bounds(2026, 9) == (date(2026, 4, 1), date(2026, 9, 30))
        assert get_esi_contribution_period_bounds(2026, 10) == (date(2026, 10, 1), date(2027, 3, 31))
        assert get_esi_contribution_period_bounds(2027, 1) == (date(2026, 10, 1), date(2027, 3, 31))

    def test_professional_tax_uses_state_mapping(self):
        slabs_by_state = {
            'MH': [
                (Decimal('10000.00'), Decimal('0.00')),
                (Decimal('15000.00'), Decimal('150.00')),
                (None, Decimal('200.00')),
            ],
            'KA': [
                (Decimal('25000.00'), Decimal('0.00')),
                (None, Decimal('200.00')),
            ],
        }
        assert calculate_professional_tax_monthly(Decimal('12000.00'), 'MH', slabs_by_state=slabs_by_state) == Decimal('150.00')
        assert calculate_professional_tax_monthly(Decimal('40000.00'), 'KA', slabs_by_state=slabs_by_state) == Decimal('200.00')

    def test_gratuity_helper_respects_service_eligibility_and_ceiling(self):
        assert calculate_gratuity_amount(last_basic_salary=Decimal('50000.00'), years_of_service=4) == Decimal('0.00')
        assert calculate_gratuity_amount(last_basic_salary=Decimal('26000.00'), years_of_service=5) == Decimal('75000.00')

    def test_gratuity_service_years_round_only_after_six_months(self):
        assert calculate_gratuity_service_years(
            date_of_joining=None,
            last_working_day=date(2026, 1, 31),
        ) == 0
        assert calculate_gratuity_service_years(
            date_of_joining=date(2026, 2, 1),
            last_working_day=date(2026, 1, 31),
        ) == 0
        assert calculate_gratuity_service_years(
            date_of_joining=date(2021, 1, 1),
            last_working_day=date(2026, 1, 31),
        ) == 5
        assert calculate_gratuity_service_years(
            date_of_joining=date(2021, 1, 1),
            last_working_day=date(2026, 7, 1),
        ) == 5
        assert calculate_gratuity_service_years(
            date_of_joining=date(2021, 1, 1),
            last_working_day=date(2026, 7, 2),
        ) == 6
        assert calculate_gratuity_service_years(
            date_of_joining=date(2021, 8, 31),
            last_working_day=date(2026, 2, 28),
        ) == 4

    def test_labour_welfare_fund_helper_picks_matching_contribution_window(self):
        result = calculate_labour_welfare_fund(
            state_code='MH',
            payroll_month=6,
            gross_pay=Decimal('4000.00'),
            contributions=[
                {
                    'min_wage': Decimal('0.00'),
                    'max_wage': Decimal('2999.99'),
                    'employee_amount': Decimal('6.00'),
                    'employer_amount': Decimal('18.00'),
                    'applicable_months': [6, 12],
                },
                {
                    'min_wage': Decimal('3000.00'),
                    'max_wage': None,
                    'employee_amount': Decimal('12.00'),
                    'employer_amount': Decimal('36.00'),
                    'applicable_months': [6, 12],
                },
            ],
        )

        assert result['is_applicable'] is True
        assert result['employee'] == Decimal('12.00')
        assert result['employer'] == Decimal('36.00')

    def test_labour_welfare_fund_helper_skips_non_matching_months(self):
        result = calculate_labour_welfare_fund(
            state_code='MH',
            payroll_month=7,
            gross_pay=Decimal('4000.00'),
            contributions=[
                {
                    'min_wage': Decimal('3000.00'),
                    'max_wage': None,
                    'employee_amount': Decimal('12.00'),
                    'employer_amount': Decimal('36.00'),
                    'applicable_months': [6, 12],
                },
            ],
        )

        assert result['is_applicable'] is False
        assert result['employee'] == Decimal('0.00')
        assert result['employer'] == Decimal('0.00')

    def test_labour_welfare_fund_helper_skips_contribution_below_minimum_wage(self):
        result = calculate_labour_welfare_fund(
            state_code='MH',
            payroll_month=6,
            gross_pay=Decimal('1000.00'),
            contributions=[
                {
                    'min_wage': Decimal('3000.00'),
                    'max_wage': None,
                    'employee_amount': Decimal('12.00'),
                    'employer_amount': Decimal('36.00'),
                    'applicable_months': [6, 12],
                },
            ],
        )

        assert result['is_applicable'] is False
        assert result['employee'] == Decimal('0.00')

    def test_calculate_annual_tax_skips_zero_width_slices(self, india_new_regime_slabs):
        result = calculate_annual_tax(india_new_regime_slabs, Decimal('300000.00'))

        assert result == Decimal('0.00')

    def test_calculate_annual_tax_skips_slab_with_zero_taxable_slice(self, db):
        slab_set = PayrollTaxSlabSet.objects.create(
            name='Zero Width Slice',
            country_code='IN',
            fiscal_year='2024-25',
            is_active=True,
        )
        PayrollTaxSlab.objects.create(
            slab_set=slab_set,
            min_income=Decimal('0.00'),
            max_income=Decimal('300000.00'),
            rate_percent=Decimal('0.00'),
        )
        PayrollTaxSlab.objects.create(
            slab_set=slab_set,
            min_income=Decimal('300000.00'),
            max_income=Decimal('300000.00'),
            rate_percent=Decimal('5.00'),
        )
        PayrollTaxSlab.objects.create(
            slab_set=slab_set,
            min_income=Decimal('300000.00'),
            max_income=None,
            rate_percent=Decimal('10.00'),
        )

        result = calculate_annual_tax(slab_set, Decimal('350000.00'))

        assert result == Decimal('5000.00')

    def test_income_tax_with_rebate_handles_threshold_rebate_in_marginal_relief_path(self, india_new_regime_slabs):
        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('700001.00'),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=[(Decimal('700000.00'), Decimal('0.10'))],
        )

        assert result['rebate_87a'] == Decimal('0.00')
        assert result['surcharge'] == Decimal('0.00')
        assert result['tax_after_rebate'] == Decimal('20000.10')


class TestNegativeNetPayGuard:
    def test_net_pay_cannot_be_negative(self):
        assert ensure_non_negative_net_pay(Decimal('-5000.00')) == Decimal('0.00')
        assert ensure_non_negative_net_pay(Decimal('0.00')) == Decimal('0.00')
        assert ensure_non_negative_net_pay(Decimal('45000.00')) == Decimal('45000.00')


class TestOldRegimeTaxConfiguration:
    @pytest.mark.django_db
    def test_old_regime_flag_on_tax_slab_set(self):
        from apps.payroll.models import PayrollTaxSlabSet

        old_regime_set = PayrollTaxSlabSet(
            name='India Old Regime FY2024-25',
            country_code='IN',
            fiscal_year='2024-25',
            is_system_master=False,
            is_old_regime=True,
        )

        old_regime_set.full_clean()

    def test_compensation_assignment_allows_tax_regime_selection(self):
        from apps.payroll.models import CompensationAssignment, TaxRegime

        assignment = CompensationAssignment(tax_regime=TaxRegime.OLD)

        assert assignment.tax_regime == TaxRegime.OLD

    def test_compensation_assignment_pf_defaults_are_statutory(self):
        from apps.payroll.models import CompensationAssignment

        assignment = CompensationAssignment()

        assert assignment.is_pf_opted_out is False
        assert assignment.vpf_rate_percent == Decimal('12.00')
@pytest.mark.django_db
class TestDBDrivenSurchargeRules:
    """Tests for SurchargeRule DB model and get_surcharge_tiers_from_db function."""

    def test_db_surcharge_rules_return_correct_tiers(self):
        from apps.payroll.models import SurchargeRule
        from apps.payroll.statutory import get_surcharge_tiers_from_db

        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="NEW",
            income_threshold=Decimal("5000000.00"),
            surcharge_rate_percent=Decimal("10.00"),
            effective_from=date(2025, 4, 1),
        )
        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="NEW",
            income_threshold=Decimal("10000000.00"),
            surcharge_rate_percent=Decimal("15.00"),
            effective_from=date(2025, 4, 1),
        )
        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="NEW",
            income_threshold=Decimal("20000000.00"),
            surcharge_rate_percent=Decimal("25.00"),
            effective_from=date(2025, 4, 1),
        )

        tiers = get_surcharge_tiers_from_db("2025-2026", "NEW")

        assert tiers == [
            (Decimal("5000000.00"), Decimal("0.10")),
            (Decimal("10000000.00"), Decimal("0.15")),
            (Decimal("20000000.00"), Decimal("0.25")),
        ]

    def test_get_surcharge_tiers_falls_back_when_no_db_rules(self):
        from apps.payroll.models import SurchargeRule
        from apps.payroll.statutory import get_surcharge_tiers_from_db

        SurchargeRule.objects.all().delete()

        tiers = get_surcharge_tiers_from_db("2025-2026", "NEW")

        assert tiers == NEW_REGIME_SURCHARGE_TIERS

    def test_get_surcharge_tiers_falls_back_for_unknown_fiscal_year(self):
        from apps.payroll.models import SurchargeRule
        from apps.payroll.statutory import get_surcharge_tiers_from_db

        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="NEW",
            income_threshold=Decimal("5000000.00"),
            surcharge_rate_percent=Decimal("10.00"),
            effective_from=date(2025, 4, 1),
        )

        tiers = get_surcharge_tiers_from_db("2020-2021", "NEW")

        assert tiers == NEW_REGIME_SURCHARGE_TIERS

    def test_surcharge_calculation_uses_db_tiers_with_exact_values(
        self, india_new_regime_slabs
    ):
        from apps.payroll.models import SurchargeRule
        from apps.payroll.statutory import get_surcharge_tiers_from_db

        india_new_regime_slabs.fiscal_year = "2025-2026"
        india_new_regime_slabs.save(update_fields=["fiscal_year"])

        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="NEW",
            income_threshold=Decimal("5000000.00"),
            surcharge_rate_percent=Decimal("10.00"),
            effective_from=date(2025, 4, 1),
        )

        tiers = get_surcharge_tiers_from_db("2025-2026", "NEW")

        result_below = calculate_income_tax_with_rebate(
            taxable_income=Decimal("4000000.00"),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )
        assert result_below["surcharge"] == Decimal("0.00")

        result_at_threshold = calculate_income_tax_with_rebate(
            taxable_income=Decimal("5000000.00"),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )
        assert result_at_threshold["surcharge"] == Decimal("0.00")

        result_above = calculate_income_tax_with_rebate(
            taxable_income=Decimal("6000000.00"),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )
        assert result_above["surcharge"] > Decimal("0.00")

    def test_surcharge_db_tiers_marginal_relief_at_50_lakh_boundary(
        self, india_new_regime_slabs
    ):
        from apps.payroll.models import SurchargeRule
        from apps.payroll.statutory import get_surcharge_tiers_from_db

        india_new_regime_slabs.fiscal_year = "2025-2026"
        india_new_regime_slabs.save(update_fields=["fiscal_year"])

        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="NEW",
            income_threshold=Decimal("5000000.00"),
            surcharge_rate_percent=Decimal("10.00"),
            effective_from=date(2025, 4, 1),
        )
        tiers = get_surcharge_tiers_from_db("2025-2026", "NEW")

        at_threshold = calculate_income_tax_with_rebate(
            taxable_income=Decimal("5000000.00"),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )
        just_above = calculate_income_tax_with_rebate(
            taxable_income=Decimal("5000001.00"),
            tax_slab_set=india_new_regime_slabs,
            surcharge_tiers=tiers,
        )

        assert just_above["tax_after_rebate"] == at_threshold[
            "tax_after_rebate"
        ] + Decimal("1.00")

    def test_old_regime_db_surcharge_tiers_work_correctly(self, india_old_regime_slabs):
        from apps.payroll.models import SurchargeRule
        from apps.payroll.statutory import get_surcharge_tiers_from_db

        india_old_regime_slabs.fiscal_year = "2025-2026"
        india_old_regime_slabs.save(update_fields=["fiscal_year"])

        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="OLD",
            income_threshold=Decimal("5000000.00"),
            surcharge_rate_percent=Decimal("10.00"),
            effective_from=date(2025, 4, 1),
        )
        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="OLD",
            income_threshold=Decimal("10000000.00"),
            surcharge_rate_percent=Decimal("15.00"),
            effective_from=date(2025, 4, 1),
        )
        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="OLD",
            income_threshold=Decimal("20000000.00"),
            surcharge_rate_percent=Decimal("25.00"),
            effective_from=date(2025, 4, 1),
        )
        SurchargeRule.objects.create(
            fiscal_year="2025-2026",
            tax_regime="OLD",
            income_threshold=Decimal("50000000.00"),
            surcharge_rate_percent=Decimal("37.00"),
            effective_from=date(2025, 4, 1),
        )

        tiers = get_surcharge_tiers_from_db("2025-2026", "OLD")

        assert tiers == [
            (Decimal("5000000.00"), Decimal("0.10")),
            (Decimal("10000000.00"), Decimal("0.15")),
            (Decimal("20000000.00"), Decimal("0.25")),
            (Decimal("50000000.00"), Decimal("0.37")),
        ]

        result_above_5_crore = calculate_income_tax_with_rebate(
            taxable_income=Decimal("60000000.00"),
            tax_slab_set=india_old_regime_slabs,
            surcharge_tiers=tiers,
        )

        assert result_above_5_crore["surcharge"] == Decimal("6590625.00")
