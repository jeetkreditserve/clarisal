from io import StringIO

import pytest
from django.core.management import call_command

from apps.payroll.models import LabourWelfareFundRule, ProfessionalTaxGender, ProfessionalTaxRule


@pytest.mark.django_db
class TestStatutorySeedCommand:
    def test_seed_statutory_masters_creates_expected_state_rules(self):
        out = StringIO()

        call_command('seed_statutory_masters', stdout=out)

        assert ProfessionalTaxRule.objects.count() == 7
        assert LabourWelfareFundRule.objects.count() == 2
        assert set(ProfessionalTaxRule.objects.values_list('state_code', flat=True)) == {'MH', 'KA', 'TN', 'WB', 'AP', 'TG', 'MP'}
        assert set(LabourWelfareFundRule.objects.values_list('state_code', flat=True)) == {'MH', 'KA'}
        mh_rule = ProfessionalTaxRule.objects.get(state_code='MH')
        assert mh_rule.slabs.filter(gender=ProfessionalTaxGender.MALE, deduction_amount='300.00', applicable_months=[2]).exists()
        ka_lwf_rule = LabourWelfareFundRule.objects.get(state_code='KA')
        assert ka_lwf_rule.contributions.filter(employee_amount='20.00', employer_amount='40.00', applicable_months=[12]).exists()
        assert 'Seeded 7 PT rules and 2 LWF rules.' in out.getvalue()

    def test_seed_statutory_masters_is_repeatable(self):
        call_command('seed_statutory_masters')
        call_command('seed_statutory_masters')

        assert ProfessionalTaxRule.objects.count() == 7
        assert LabourWelfareFundRule.objects.count() == 2
        assert ProfessionalTaxRule.objects.get(state_code='TG').slabs.count() == 3
