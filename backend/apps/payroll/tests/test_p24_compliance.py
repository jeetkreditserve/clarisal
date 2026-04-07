from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.employees.models import EmployeeProfile, GenderChoice
from apps.payroll.models import LabourWelfareFundRule, ProfessionalTaxRule
from apps.payroll.services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
)

from .test_service_setup import _create_active_organisation, _create_employee, _create_user


def _seed_ct_tax_master(actor):
    create_tax_slab_set(
        fiscal_year='2026-2027',
        name='CT Master 2026-2027',
        country_code='IN',
        slabs=[
            {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
            {'min_income': '300000', 'max_income': '700000', 'rate_percent': '10'},
            {'min_income': '700000', 'max_income': None, 'rate_percent': '20'},
        ],
        organisation=None,
        actor=actor,
    )


def _set_organisation_state(organisation, *, state, state_code):
    organisation.addresses.filter(is_active=True).update(state=state, state_code=state_code)


def _set_employee_gender(employee, gender):
    EmployeeProfile.objects.update_or_create(employee=employee, defaults={'gender': gender})


def _basic_template(organisation, actor, *, name='P24 Template', monthly_amount='200000'):
    return create_compensation_template(
        organisation,
        name=name,
        actor=actor,
        lines=[
            {
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': 'EARNING',
                'monthly_amount': monthly_amount,
                'is_taxable': True,
            }
        ],
    )


@pytest.mark.django_db
class TestP24PayrollCompliance:
    @pytest.mark.parametrize(
        ('period_year', 'period_month', 'effective_from', 'expected_divisor'),
        [
            (2026, 4, date(2026, 4, 1), Decimal('12')),
            (2026, 10, date(2026, 10, 1), Decimal('6')),
            (2027, 2, date(2027, 2, 1), Decimal('2')),
            (2027, 3, date(2027, 3, 1), Decimal('1')),
        ],
    )
    def test_pay_run_allocates_tds_using_remaining_fiscal_months(
        self,
        period_year,
        period_month,
        effective_from,
        expected_divisor,
    ):
        organisation = _create_active_organisation(f'TDS {period_year}-{period_month:02d}')
        requester_user = _create_user(
            f'tds-{period_year}-{period_month:02d}-admin@test.com',
            organisation=organisation,
        )
        _employee_user, employee = _create_employee(
            organisation,
            f'tds-{period_year}-{period_month:02d}-employee@test.com',
            employee_code=f'EMPTDS{period_month:02d}',
        )
        employee.date_of_joining = effective_from
        employee.save(update_fields=['date_of_joining', 'modified_at'])

        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(
            organisation,
            requester_user,
            name=f'TDS Template {period_year}-{period_month:02d}',
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=effective_from,
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=period_year,
            period_month=period_month,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        annual_tax_total = Decimal(item.snapshot['annual_tax_total'])
        assert item.income_tax == (annual_tax_total / expected_divisor).quantize(Decimal('0.01'))

    def test_salary_revision_month_uses_remaining_fiscal_months_for_tds(self):
        organisation = _create_active_organisation('TDS Salary Revision Org')
        requester_user = _create_user('tds-revision-admin@test.com', organisation=organisation)
        _employee_user, employee = _create_employee(
            organisation,
            'tds-revision-employee@test.com',
            employee_code='EMPTDSREV1',
        )

        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        april_template = _basic_template(
            organisation,
            requester_user,
            name='April Salary Template',
            monthly_amount='50000',
        )
        october_template = _basic_template(
            organisation,
            requester_user,
            name='October Salary Revision Template',
            monthly_amount='200000',
        )
        assign_employee_compensation(
            employee,
            april_template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        assign_employee_compensation(
            employee,
            october_template,
            effective_from=date(2026, 10, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=10,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.gross_pay == Decimal('200000.00')
        annual_tax_total = Decimal(item.snapshot['annual_tax_total'])
        assert item.income_tax == (annual_tax_total / Decimal('6')).quantize(Decimal('0.01'))

    def test_pf_opt_out_rejects_pre_september_2014_joiner_without_exemption(self):
        organisation = _create_active_organisation('PF Guard Org')
        requester_user = _create_user('pf-guard-admin@test.com', organisation=organisation)
        _employee_user, employee = _create_employee(
            organisation,
            'pf-guard-employee@test.com',
            employee_code='EMPPFG1',
        )
        employee.date_of_joining = date(2014, 8, 31)
        employee.save(update_fields=['date_of_joining', 'modified_at'])

        template = _basic_template(
            organisation,
            requester_user,
            name='PF Guard Template',
            monthly_amount='50000',
        )

        with pytest.raises(ValueError, match='PF opt-out is only allowed'):
            assign_employee_compensation(
                employee,
                template,
                effective_from=date(2026, 4, 1),
                actor=requester_user,
                auto_approve=True,
                is_pf_opted_out=True,
            )

    def test_pf_opt_out_allows_pre_september_2014_joiner_with_explicit_exemption(self):
        organisation = _create_active_organisation('PF Exempt Org')
        requester_user = _create_user('pf-exempt-admin@test.com', organisation=organisation)
        _employee_user, employee = _create_employee(
            organisation,
            'pf-exempt-employee@test.com',
            employee_code='EMPPFG2',
        )
        employee.date_of_joining = date(2014, 8, 31)
        employee.save(update_fields=['date_of_joining', 'modified_at'])

        template = _basic_template(
            organisation,
            requester_user,
            name='PF Exempt Template',
            monthly_amount='50000',
        )
        assignment = assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
            is_pf_opted_out=True,
            is_epf_exempt=True,
        )

        assert assignment.is_pf_opted_out is True
        assert assignment.is_epf_exempt is True
        assert assignment.vpf_rate_percent == Decimal('0.00')

    @pytest.mark.parametrize(
        ('state', 'state_code', 'period_month', 'gross_amount', 'expected_pt', 'gender'),
        [
            ('Gujarat', 'GJ', 4, '12000.00', '200.00', None),
            ('Haryana', 'HR', 4, '25000.00', '200.00', None),
            ('Punjab', 'PB', 4, '21000.00', '200.00', GenderChoice.MALE),
            ('Punjab', 'PB', 4, '21000.00', '0.00', GenderChoice.FEMALE),
            ('Odisha', 'OD', 4, '25000.00', '200.00', None),
            ('Rajasthan', 'RJ', 4, '50000.00', '0.00', None),
            ('Himachal Pradesh', 'HP', 4, '10000.00', '200.00', None),
            ('Chhattisgarh', 'CT', 4, '25000.00', '200.00', None),
            ('Jharkhand', 'JH', 4, '25000.00', '100.00', None),
            ('Jharkhand', 'JH', 4, '42000.00', '150.00', None),
        ],
    )
    def test_seeded_professional_tax_rules_cover_new_states(
        self,
        state,
        state_code,
        period_month,
        gross_amount,
        expected_pt,
        gender,
    ):
        call_command('seed_statutory_masters')
        organisation = _create_active_organisation(f'{state} PT Org')
        requester_user = _create_user(f'{state_code.lower()}-pt-admin@test.com', organisation=organisation)
        _employee_user, employee = _create_employee(
            organisation,
            f'{state_code.lower()}-pt-employee@test.com',
            employee_code=f'EMP{state_code}PT',
        )
        _set_organisation_state(organisation, state=state, state_code=state_code)
        if gender is not None:
            _set_employee_gender(employee, gender)

        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(
            organisation,
            requester_user,
            name=f'{state} PT Template',
            monthly_amount=gross_amount,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, period_month, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=period_month,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert Decimal(item.snapshot['pt_monthly']) == Decimal(expected_pt)

    @pytest.mark.parametrize(
        ('state', 'state_code', 'period_month', 'gross_amount', 'expected_employee', 'expected_employer'),
        [
            ('Andhra Pradesh', 'AP', 12, '10000.00', '40.00', '60.00'),
            ('Telangana', 'TG', 12, '10000.00', '40.00', '60.00'),
            ('Madhya Pradesh', 'MP', 12, '10000.00', '10.00', '30.00'),
            ('Odisha', 'OD', 12, '10000.00', '20.00', '40.00'),
            ('Haryana', 'HR', 4, '10000.00', '7.50', '22.50'),
        ],
    )
    def test_seeded_labour_welfare_fund_rules_cover_new_states(
        self,
        state,
        state_code,
        period_month,
        gross_amount,
        expected_employee,
        expected_employer,
    ):
        call_command('seed_statutory_masters')
        organisation = _create_active_organisation(f'{state} LWF Org')
        requester_user = _create_user(f'{state_code.lower()}-lwf-admin@test.com', organisation=organisation)
        _employee_user, employee = _create_employee(
            organisation,
            f'{state_code.lower()}-lwf-employee@test.com',
            employee_code=f'EMP{state_code}LWF',
        )
        _set_organisation_state(organisation, state=state, state_code=state_code)

        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(
            organisation,
            requester_user,
            name=f'{state} LWF Template',
            monthly_amount=gross_amount,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, period_month, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=period_month,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert Decimal(item.snapshot['lwf_employee']) == Decimal(expected_employee)
        assert Decimal(item.snapshot['lwf_employer']) == Decimal(expected_employer)

    def test_pay_run_prefetches_pt_and_lwf_rules_once_per_state(self):
        call_command('seed_statutory_masters')
        organisation = _create_active_organisation('PT LWF Cache Org')
        _set_organisation_state(organisation, state='Karnataka', state_code='KA')
        requester_user = _create_user('pt-lwf-cache-admin@test.com', organisation=organisation)

        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(
            organisation,
            requester_user,
            name='PT LWF Cache Template',
            monthly_amount='30000',
        )
        for index in range(10):
            _employee_user, employee = _create_employee(
                organisation,
                f'pt-lwf-cache-{index}@test.com',
                employee_code=f'EMPCACHE{index:02d}',
            )
            assign_employee_compensation(
                employee,
                template,
                effective_from=date(2026, 12, 1),
                actor=requester_user,
                auto_approve=True,
            )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=12,
            requester_user=requester_user,
        )

        with (
            patch.object(ProfessionalTaxRule.objects, 'filter', wraps=ProfessionalTaxRule.objects.filter) as pt_filter,
            patch.object(LabourWelfareFundRule.objects, 'filter', wraps=LabourWelfareFundRule.objects.filter) as lwf_filter,
        ):
            calculate_pay_run(pay_run, actor=requester_user)

        assert pt_filter.call_count == 1
        assert lwf_filter.call_count == 1
