from io import StringIO

import pytest
from django.core.management import call_command

from apps.payroll.models import (
    LabourWelfareFundRule,
    PayrollTaxSlabSet,
    ProfessionalTaxGender,
    ProfessionalTaxRule,
    SurchargeRule,
)
from apps.payroll.services import _canonicalize_payroll_state_code


@pytest.mark.django_db
class TestStatutorySeedCommand:
    def test_seed_statutory_masters_creates_expected_state_rules(self):
        out = StringIO()

        call_command('seed_statutory_masters', stdout=out)

        # Payroll uses GST subdivision codes, so Odisha/Chhattisgarh are seeded as OD/CT.
        assert ProfessionalTaxRule.objects.count() == 15
        assert LabourWelfareFundRule.objects.count() == 8
        assert set(ProfessionalTaxRule.objects.values_list('state_code', flat=True)) == {
            'MH', 'KA', 'TN', 'WB', 'AP', 'TG', 'MP', 'GJ', 'HR', 'PB', 'OD', 'RJ', 'HP', 'CT', 'JH',
        }
        assert set(LabourWelfareFundRule.objects.values_list('state_code', flat=True)) == {'MH', 'KA', 'AP', 'TG', 'MP', 'HR', 'OD', 'WB'}
        mh_rule = ProfessionalTaxRule.objects.get(state_code='MH')
        assert mh_rule.slabs.filter(gender=ProfessionalTaxGender.MALE, deduction_amount='300.00', applicable_months=[2]).exists()
        rj_rule = ProfessionalTaxRule.objects.get(state_code='RJ')
        assert rj_rule.slabs.filter(deduction_amount='0.00').exists()
        ka_lwf_rule = LabourWelfareFundRule.objects.get(state_code='KA')
        assert ka_lwf_rule.contributions.filter(employee_amount='20.00', employer_amount='40.00', applicable_months=[12]).exists()
        ap_lwf_rule = LabourWelfareFundRule.objects.get(state_code='AP')
        assert ap_lwf_rule.contributions.filter(employee_amount='40.00', employer_amount='60.00', applicable_months=[12]).exists()
        wb_lwf_rule = LabourWelfareFundRule.objects.get(state_code='WB')
        assert wb_lwf_rule.contributions.filter(employee_amount='3.00', employer_amount='6.00', applicable_months=[12]).exists()
        assert '15 PT rules' in out.getvalue()
        assert '8 LWF rules' in out.getvalue()
        assert 'income tax masters' in out.getvalue()
        # 2 fiscal years × 2 regimes × 3 categories = 12 CT income tax masters
        assert PayrollTaxSlabSet.objects.filter(organisation__isnull=True, is_system_master=True).count() == 12

    def test_seed_statutory_masters_is_repeatable(self):
        call_command('seed_statutory_masters')
        call_command('seed_statutory_masters')

        assert ProfessionalTaxRule.objects.count() == 15
        assert LabourWelfareFundRule.objects.count() == 8
        assert ProfessionalTaxRule.objects.get(state_code='TG').slabs.count() == 3
        assert ProfessionalTaxRule.objects.get(state_code='RJ').slabs.count() == 1
        assert PayrollTaxSlabSet.objects.filter(organisation__isnull=True, is_system_master=True).count() == 12

    def test_seed_statutory_masters_adds_old_regime_thirty_seven_percent_surcharge_tier(self):
        call_command('seed_statutory_masters')

        assert SurchargeRule.objects.get(
            fiscal_year='2024-2025',
            tax_regime='OLD',
            income_threshold='50000000.00',
        ).surcharge_rate_percent == pytest.approx(37)
        assert SurchargeRule.objects.get(
            fiscal_year='2025-2026',
            tax_regime='OLD',
            income_threshold='50000000.00',
        ).surcharge_rate_percent == pytest.approx(37)

    def test_canonicalize_payroll_state_code_maps_ts_to_tg(self):
        assert _canonicalize_payroll_state_code('TS') == 'TG'
        assert _canonicalize_payroll_state_code('TG') == 'TG'
