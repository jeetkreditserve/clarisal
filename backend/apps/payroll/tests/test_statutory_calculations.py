from decimal import Decimal

import pytest

from apps.payroll.models import PayrollTaxSlab, PayrollTaxSlabSet


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


class TestSection87ARebate:
    def test_income_5_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
        from apps.payroll.services import calculate_income_tax_with_rebate

        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('500000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] == Decimal('0.00')
        assert result['rebate_87a'] == Decimal('10000.00')

    def test_income_6_5_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
        from apps.payroll.services import calculate_income_tax_with_rebate

        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('650000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] == Decimal('0.00')
        assert result['rebate_87a'] == Decimal('17500.00')

    def test_income_exactly_7_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
        from apps.payroll.services import calculate_income_tax_with_rebate

        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('700000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] == Decimal('0.00')
        assert result['rebate_87a'] == Decimal('20000.00')

    def test_income_above_7_lakh_does_not_get_rebate(self, india_new_regime_slabs):
        from apps.payroll.services import calculate_income_tax_with_rebate

        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('700001'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['annual_tax'] > Decimal('0.00')
        assert result['rebate_87a'] == Decimal('0.00')

    def test_income_10_lakh_has_cess_and_no_rebate(self, india_new_regime_slabs):
        from apps.payroll.services import calculate_income_tax_with_rebate

        result = calculate_income_tax_with_rebate(
            taxable_income=Decimal('1000000'),
            tax_slab_set=india_new_regime_slabs,
        )

        assert result['rebate_87a'] == Decimal('0.00')
        assert result['annual_tax'] == Decimal('52000.00')


class TestTaxHelpers:
    def test_standard_deduction_subtracted(self):
        from apps.payroll.services import calculate_taxable_income_after_standard_deduction

        assert calculate_taxable_income_after_standard_deduction(Decimal('1000000')) == Decimal('925000.00')

    def test_standard_deduction_never_returns_negative(self):
        from apps.payroll.services import calculate_taxable_income_after_standard_deduction

        assert calculate_taxable_income_after_standard_deduction(Decimal('50000')) == Decimal('0.00')

    def test_cess_applied_after_tax(self):
        from apps.payroll.services import apply_cess

        assert apply_cess(Decimal('50000.00')) == Decimal('52000.00')


class TestNegativeNetPayGuard:
    def test_net_pay_cannot_be_negative(self):
        from apps.payroll.services import ensure_non_negative_net_pay

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
