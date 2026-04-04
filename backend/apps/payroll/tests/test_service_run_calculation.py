from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.approvals.models import ApprovalRequestKind
from apps.employees.models import EmployeeProfile, EmployeeStatus, GenderChoice
from apps.locations.models import OfficeLocation
from apps.organisations.models import OrganisationAddress, OrganisationAddressType
from apps.payroll.models import PayrollRunItemStatus, PayrollRunStatus, TaxRegime
from apps.payroll.services import (
    _create_payroll_approval_run,
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
)

from .test_service_setup import (
    _create_active_organisation,
    _create_employee,
    _create_workflow,
)


def _basic_template(organisation, actor, name='Run Calc Template', monthly_amount='30000'):
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
            },
        ],
    )


def _seed_ct_tax_master(requester_user):
    create_tax_slab_set(
        fiscal_year='2026-2027',
        name='CT Master',
        country_code='IN',
        slabs=[
            {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
            {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
        ],
        organisation=None,
        actor=requester_user,
    )


def _set_organisation_state(organisation, *, state, state_code):
    organisation.addresses.filter(is_active=True).update(state=state, state_code=state_code)


def _set_employee_gender(employee, gender):
    EmployeeProfile.objects.update_or_create(
        employee=employee,
        defaults={'gender': gender},
    )


@pytest.mark.django_db
class TestPayrollRunCalculationService:
    def test_calculate_pay_run_rejects_approved_and_finalized_runs(self):
        organisation = _create_active_organisation('Run Status Guard Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'status-guard@test.com',
            employee_code='EMPRC1',
        )
        approved_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        approved_run.status = PayrollRunStatus.APPROVED
        approved_run.save(update_fields=['status'])

        with pytest.raises(ValueError):
            calculate_pay_run(approved_run, actor=requester_user)

        approved_run.status = PayrollRunStatus.FINALIZED
        approved_run.save(update_fields=['status'])
        with pytest.raises(ValueError):
            calculate_pay_run(approved_run, actor=requester_user)

    def test_calculate_pay_run_cancels_pending_approval_run_before_recalculation(self):
        organisation = _create_active_organisation('Run Approval Cancel Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'recalc-requester@test.com',
            employee_code='EMPRC2',
        )
        _approver_user, approver_employee = _create_employee(
            organisation,
            'recalc-approver@test.com',
            employee_code='EMPRC3',
        )
        _create_workflow(organisation, approver_employee, ApprovalRequestKind.PAYROLL_PROCESSING)
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        approval_run = _create_payroll_approval_run(
            pay_run,
            ApprovalRequestKind.PAYROLL_PROCESSING,
            organisation,
            requester_user,
            requester_employee=requester_employee,
            subject_label=pay_run.name,
        )
        pay_run.approval_run = approval_run
        pay_run.save(update_fields=['approval_run'])

        with patch('apps.payroll.services.cancel_approval_run') as mock_cancel:
            calculate_pay_run(pay_run, actor=requester_user)

        pay_run.refresh_from_db()
        mock_cancel.assert_called_once_with(approval_run, actor=requester_user, subject_status=None)
        assert pay_run.approval_run is None
        assert pay_run.status == PayrollRunStatus.CALCULATED

    def test_calculate_pay_run_creates_exception_for_old_regime_without_old_slab_set(self):
        organisation = _create_active_organisation('Old Regime Missing Slab Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'old-regime-requester@test.com',
            employee_code='EMPRC4',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'old-regime-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC5',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 New Regime',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=organisation,
            actor=requester_user,
            is_old_regime=False,
        )
        template = _basic_template(organisation, requester_user, name='Old Regime Calc Template')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
            tax_regime=TaxRegime.OLD,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.EXCEPTION
        assert 'old tax slab set' in item.message.lower()
        assert item.snapshot['tax_regime'] == TaxRegime.OLD

    def test_calculate_pay_run_caps_pf_wages_at_15000(self):
        organisation = _create_active_organisation('PF Ceiling Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'pf-ceiling-requester@test.com',
            employee_code='EMPRC11',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'pf-ceiling-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC12',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='PF Ceiling Template', monthly_amount='50000')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert Decimal(item.snapshot['pf_eligible_basic']) == Decimal('15000.00')
        assert Decimal(item.snapshot['auto_pf']) == Decimal('1800.00')
        assert Decimal(item.snapshot['pf_employer']) == Decimal('1800.00')
        assert Decimal(item.snapshot['pf_employee_rate_percent']) == Decimal('12.00')
        assert item.snapshot['pf_is_opted_out'] is False

    def test_calculate_pay_run_handles_pf_ceiling_boundary_values(self):
        organisation = _create_active_organisation('PF Boundary Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'pf-boundary-requester@test.com',
            employee_code='EMPRC17',
        )
        _employee_user, employee_exact = _create_employee(
            organisation,
            'pf-boundary-exact@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC18',
        )
        _employee_user, employee_above = _create_employee(
            organisation,
            'pf-boundary-above@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC19',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        exact_template = _basic_template(organisation, requester_user, name='PF Exact Template', monthly_amount='15000')
        above_template = _basic_template(organisation, requester_user, name='PF Above Template', monthly_amount='15000.01')
        assign_employee_compensation(
            employee_exact,
            exact_template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        assign_employee_compensation(
            employee_above,
            above_template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        exact_item = pay_run.items.get(employee=employee_exact)
        above_item = pay_run.items.get(employee=employee_above)
        assert Decimal(exact_item.snapshot['pf_eligible_basic']) == Decimal('15000.00')
        assert Decimal(above_item.snapshot['pf_eligible_basic']) == Decimal('15000.00')
        assert Decimal(exact_item.snapshot['auto_pf']) == Decimal('1800.00')
        assert Decimal(above_item.snapshot['auto_pf']) == Decimal('1800.00')

    def test_calculate_pay_run_honours_pf_opt_out_for_higher_wage_joiner(self):
        organisation = _create_active_organisation('PF Opt Out Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'pf-optout-requester@test.com',
            employee_code='EMPRC13',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'pf-optout-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC14',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='PF Opt Out Template', monthly_amount='50000')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
            is_pf_opted_out=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert Decimal(item.snapshot['auto_pf']) == Decimal('0.00')
        assert Decimal(item.snapshot['pf_employer']) == Decimal('0.00')
        assert item.snapshot['pf_is_opted_out'] is True

    def test_calculate_pay_run_applies_vpf_rate_above_12_percent(self):
        organisation = _create_active_organisation('VPF Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'vpf-requester@test.com',
            employee_code='EMPRC15',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'vpf-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC16',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='VPF Template', monthly_amount='50000')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
            vpf_rate_percent=Decimal('20.00'),
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert Decimal(item.snapshot['pf_eligible_basic']) == Decimal('15000.00')
        assert Decimal(item.snapshot['auto_pf']) == Decimal('3000.00')
        assert Decimal(item.snapshot['pf_employer']) == Decimal('1800.00')
        assert Decimal(item.snapshot['pf_employee_rate_percent']) == Decimal('20.00')

    def test_calculate_pay_run_uses_attendance_inputs_for_lop_and_overtime(self):
        organisation = _create_active_organisation('Attendance Payroll Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'attendance-requester@test.com',
            employee_code='EMPRC6',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'attendance-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC7',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, monthly_amount='30000')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
            use_attendance_inputs=True,
        )

        with patch('apps.attendance.services.get_payroll_attendance_summary') as mock_summary:
            mock_summary.return_value = {
                'paid_fraction': Decimal('20.00'),
                'overtime_minutes': 45,
                'lop_days': Decimal('10.00'),
            }
            calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert item.snapshot['attendance']['attendance_source'] == 'attendance_service'
        assert item.snapshot['attendance']['attendance_paid_days'] == '20.00'
        assert item.snapshot['attendance']['effective_lop_days'] == '10.00'
        assert item.snapshot['attendance_overtime_minutes'] == 45
        assert Decimal(item.snapshot['lop_deduction']) == Decimal('10000.00')

    def test_calculate_pay_run_continues_esi_after_salary_crosses_threshold_within_same_window(self):
        organisation = _create_active_organisation('ESI Continuation Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'esi-continuation-requester@test.com',
            employee_code='EMPRC20',
        )
        requester_employee.status = EmployeeStatus.RESIGNED
        requester_employee.save(update_fields=['status'])
        _employee_user, employee = _create_employee(
            organisation,
            'esi-continuation-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC21',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        april_template = _basic_template(organisation, requester_user, name='ESI April Template', monthly_amount='21000')
        assign_employee_compensation(
            employee,
            april_template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        april_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        calculate_pay_run(april_run, actor=requester_user)
        finalize_pay_run(april_run, actor=requester_user, skip_approval=True)

        may_template = _basic_template(organisation, requester_user, name='ESI May Template', monthly_amount='25000')
        assign_employee_compensation(
            employee,
            may_template,
            effective_from=date(2026, 5, 1),
            actor=requester_user,
            auto_approve=True,
        )
        may_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=5,
            requester_user=requester_user,
        )

        calculate_pay_run(may_run, actor=requester_user)

        item = may_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert item.snapshot['esi_eligibility_mode'] == 'CONTINUED'
        assert item.snapshot['esi_contribution_period_start'] == '2026-04-01'
        assert item.snapshot['esi_contribution_period_end'] == '2026-09-30'
        assert Decimal(item.snapshot['esi_employee']) == Decimal('187.50')
        assert Decimal(item.snapshot['esi_employer']) == Decimal('812.50')

    def test_calculate_pay_run_applies_esi_at_exact_threshold(self):
        organisation = _create_active_organisation('ESI Threshold Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'esi-threshold-requester@test.com',
            employee_code='EMPRC22',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'esi-threshold-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC23',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='ESI Threshold Template', monthly_amount='21000')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.snapshot['esi_eligibility_mode'] == 'DIRECT'
        assert Decimal(item.snapshot['esi_employee']) == Decimal('157.50')
        assert Decimal(item.snapshot['esi_employer']) == Decimal('682.50')

    def test_calculate_pay_run_resets_esi_continuation_in_new_contribution_window(self):
        organisation = _create_active_organisation('ESI Reset Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'esi-reset-requester@test.com',
            employee_code='EMPRC24',
        )
        requester_employee.status = EmployeeStatus.RESIGNED
        requester_employee.save(update_fields=['status'])
        _employee_user, employee = _create_employee(
            organisation,
            'esi-reset-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC25',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        september_template = _basic_template(organisation, requester_user, name='ESI September Template', monthly_amount='21000')
        assign_employee_compensation(
            employee,
            september_template,
            effective_from=date(2026, 9, 1),
            actor=requester_user,
            auto_approve=True,
        )
        september_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=9,
            requester_user=requester_user,
        )
        calculate_pay_run(september_run, actor=requester_user)
        finalize_pay_run(september_run, actor=requester_user, skip_approval=True)

        october_template = _basic_template(organisation, requester_user, name='ESI October Template', monthly_amount='25000')
        assign_employee_compensation(
            employee,
            october_template,
            effective_from=date(2026, 10, 1),
            actor=requester_user,
            auto_approve=True,
        )
        october_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=10,
            requester_user=requester_user,
        )

        calculate_pay_run(october_run, actor=requester_user)

        item = october_run.items.get(employee=employee)
        assert item.snapshot['esi_eligibility_mode'] == 'NONE'
        assert item.snapshot['esi_contribution_period_start'] == ''
        assert item.snapshot['esi_contribution_period_end'] == ''
        assert Decimal(item.snapshot['esi_employee']) == Decimal('0.00')
        assert Decimal(item.snapshot['esi_employer']) == Decimal('0.00')

    def test_calculate_pay_run_re_enters_esi_eligibility_in_new_contribution_window(self):
        organisation = _create_active_organisation('ESI Reentry Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'esi-reentry-requester@test.com',
            employee_code='EMPRC26',
        )
        requester_employee.status = EmployeeStatus.RESIGNED
        requester_employee.save(update_fields=['status'])
        _employee_user, employee = _create_employee(
            organisation,
            'esi-reentry-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC27',
        )
        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        april_template = _basic_template(organisation, requester_user, name='ESI April High Template', monthly_amount='25000')
        assign_employee_compensation(
            employee,
            april_template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        april_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        calculate_pay_run(april_run, actor=requester_user)
        april_item = april_run.items.get(employee=employee)
        assert april_item.snapshot['esi_eligibility_mode'] == 'NONE'

        october_template = _basic_template(organisation, requester_user, name='ESI October Low Template', monthly_amount='21000')
        assign_employee_compensation(
            employee,
            october_template,
            effective_from=date(2026, 10, 1),
            actor=requester_user,
            auto_approve=True,
        )
        october_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=10,
            requester_user=requester_user,
        )
        calculate_pay_run(october_run, actor=requester_user)

        october_item = october_run.items.get(employee=employee)
        assert october_item.snapshot['esi_eligibility_mode'] == 'DIRECT'
        assert october_item.snapshot['esi_contribution_period_start'] == '2026-10-01'
        assert october_item.snapshot['esi_contribution_period_end'] == '2027-03-31'
        assert Decimal(october_item.snapshot['esi_employee']) == Decimal('157.50')

    @pytest.mark.parametrize(
        ('state', 'state_code', 'period_month', 'gross_amount', 'expected_pt', 'expected_basis', 'gender'),
        [
            ('Maharashtra', 'MH', 1, '10000.00', '175.00', '10000.00', GenderChoice.MALE),
            ('Karnataka', 'KA', 2, '25000.00', '300.00', '25000.00', None),
            ('Tamil Nadu', 'TN', 9, '5000.00', '180.00', '30000.00', None),
            ('West Bengal', 'WB', 1, '15000.01', '130.00', '15000.01', None),
            ('Andhra Pradesh', 'AP', 1, '20000.01', '200.00', '20000.01', None),
            ('Telangana', 'TG', 1, '20000.01', '200.00', '20000.01', None),
            ('Madhya Pradesh', 'MP', 3, '33334.00', '212.00', '400008.00', None),
        ],
    )
    def test_calculate_pay_run_applies_seeded_professional_tax_rules_by_state(
        self,
        state,
        state_code,
        period_month,
        gross_amount,
        expected_pt,
        expected_basis,
        gender,
    ):
        organisation = _create_active_organisation(f'{state} PT Org')
        _set_organisation_state(organisation, state=state, state_code=state_code)
        requester_user, _requester_employee = _create_employee(
            organisation,
            f'{state_code.lower()}-pt-requester@test.com',
            employee_code=f'EMP{state_code}PT1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            f'{state_code.lower()}-pt-employee@test.com',
            role='EMPLOYEE',
            employee_code=f'EMP{state_code}PT2',
        )
        if gender:
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
        pt_lines = [line for line in item.snapshot['lines'] if line['component_code'] == 'PROFESSIONAL_TAX']
        assert item.status == PayrollRunItemStatus.READY
        assert item.snapshot['pt_state_code'] == state_code
        assert Decimal(item.snapshot['pt_taxable_basis']) == Decimal(expected_basis)
        assert Decimal(item.snapshot['pt_monthly']) == Decimal(expected_pt)
        assert len(pt_lines) == 1
        assert Decimal(pt_lines[0]['monthly_amount']) == Decimal(expected_pt)

    def test_calculate_pay_run_skips_half_yearly_professional_tax_outside_due_month(self):
        organisation = _create_active_organisation('Tamil Nadu PT Quiet Month Org')
        _set_organisation_state(organisation, state='Tamil Nadu', state_code='TN')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'tn-pt-quiet-requester@test.com',
            employee_code='EMPTNPT1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'tn-pt-quiet-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPTNPT2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='TN PT Quiet Template', monthly_amount='5000.00')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        pt_lines = [line for line in item.snapshot['lines'] if line['component_code'] == 'PROFESSIONAL_TAX']
        assert Decimal(item.snapshot['pt_taxable_basis']) == Decimal('30000.00')
        assert Decimal(item.snapshot['pt_monthly']) == Decimal('0.00')
        assert pt_lines == []

    @pytest.mark.parametrize(
        ('state', 'state_code', 'period_month', 'gross_amount', 'expected_employee', 'expected_employer'),
        [
            ('Maharashtra', 'MH', 6, '4000.00', '12.00', '36.00'),
            ('Karnataka', 'KA', 12, '18000.00', '20.00', '40.00'),
        ],
    )
    def test_calculate_pay_run_applies_seeded_labour_welfare_fund_rules(
        self,
        state,
        state_code,
        period_month,
        gross_amount,
        expected_employee,
        expected_employer,
    ):
        organisation = _create_active_organisation(f'{state} LWF Org')
        _set_organisation_state(organisation, state=state, state_code=state_code)
        requester_user, _requester_employee = _create_employee(
            organisation,
            f'{state_code.lower()}-lwf-requester@test.com',
            employee_code=f'EMP{state_code}L1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            f'{state_code.lower()}-lwf-employee@test.com',
            role='EMPLOYEE',
            employee_code=f'EMP{state_code}L2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name=f'{state} LWF Template', monthly_amount=gross_amount)
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
        employee_lines = [line for line in item.snapshot['lines'] if line['component_code'] == 'LWF_EMPLOYEE']
        employer_lines = [line for line in item.snapshot['lines'] if line['component_code'] == 'LWF_EMPLOYER']
        assert Decimal(item.snapshot['lwf_employee']) == Decimal(expected_employee)
        assert Decimal(item.snapshot['lwf_employer']) == Decimal(expected_employer)
        assert len(employee_lines) == 1
        assert len(employer_lines) == 1
        assert Decimal(employee_lines[0]['monthly_amount']) == Decimal(expected_employee)
        assert Decimal(employer_lines[0]['monthly_amount']) == Decimal(expected_employer)

    def test_calculate_pay_run_skips_labour_welfare_fund_outside_applicable_month(self):
        organisation = _create_active_organisation('Maharashtra LWF Quiet Month Org')
        _set_organisation_state(organisation, state='Maharashtra', state_code='MH')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'mh-lwf-quiet-requester@test.com',
            employee_code='EMPMHLQ1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'mh-lwf-quiet-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPMHLQ2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='MH LWF Quiet Template', monthly_amount='4000.00')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 7, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=7,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert Decimal(item.snapshot['lwf_employee']) == Decimal('0.00')
        assert Decimal(item.snapshot['lwf_employer']) == Decimal('0.00')
        assert [line for line in item.snapshot['lines'] if line['component_code'].startswith('LWF_')] == []

    def test_calculate_pay_run_marks_all_employees_exception_when_org_state_is_unconfigured(self):
        organisation = _create_active_organisation('Missing State Org')
        organisation.addresses.filter(is_active=True).update(state_code='')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'missing-state-requester@test.com',
            employee_code='EMPMS1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'missing-state-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPMS2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='Missing State Template')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.EXCEPTION
        assert 'registered or billing organisation address' in item.message.lower()
        assert pay_run.attendance_snapshot['exception_item_count'] == 2

    def test_calculate_pay_run_marks_exception_when_office_location_state_has_no_pt_rule(self):
        organisation = _create_active_organisation('Office State PT Exception Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'office-state-requester@test.com',
            employee_code='EMPOFF1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'office-state-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPOFF2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        address = OrganisationAddress.objects.create(
            organisation=organisation,
            address_type=OrganisationAddressType.CUSTOM,
            label='Branch',
            line1='Branch Road',
            city='Pune',
            state='Unseeded',
            state_code='ZZ',
            country='India',
            country_code='IN',
            pincode='411001',
            is_active=True,
        )
        employee.office_location = OfficeLocation.objects.create(
            organisation=organisation,
            organisation_address=address,
            name='Branch Office',
            city='Pune',
            state='Unseeded',
            country='India',
            pincode='411001',
        )
        employee.save(update_fields=['office_location'])
        template = _basic_template(organisation, requester_user, name='Office State Template')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.EXCEPTION
        assert item.snapshot['employee_state'] == 'ZZ'

    def test_calculate_pay_run_uses_employee_office_location_state_override(self):
        organisation = _create_active_organisation('Office State Override Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'office-override-requester@test.com',
            employee_code='EMPOVR1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'office-override-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPOVR2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        address = OrganisationAddress.objects.create(
            organisation=organisation,
            address_type=OrganisationAddressType.CUSTOM,
            label='AP Branch',
            line1='AP Road',
            city='Vijayawada',
            state='Andhra Pradesh',
            state_code='AP',
            country='India',
            country_code='IN',
            pincode='520001',
            is_active=True,
        )
        employee.office_location = OfficeLocation.objects.create(
            organisation=organisation,
            organisation_address=address,
            name='AP Branch Office',
            city='Vijayawada',
            state='Andhra Pradesh',
            country='India',
            pincode='520001',
        )
        employee.save(update_fields=['office_location'])
        template = _basic_template(organisation, requester_user, name='Office Override Template', monthly_amount='20001.00')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.status == PayrollRunItemStatus.READY
        assert item.snapshot['pt_state_code'] == 'AP'
        assert Decimal(item.snapshot['pt_monthly']) == Decimal('200.00')

    def test_calculate_pay_run_replaces_existing_pf_template_lines_and_keeps_other_deduction_components(self):
        organisation = _create_active_organisation('PF Template Line Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'pf-template-requester@test.com',
            employee_code='EMPPFT1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'pf-template-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPPFT2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = create_compensation_template(
            organisation,
            name='PF Existing Lines Template',
            actor=requester_user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '50000',
                    'is_taxable': True,
                },
                {
                    'component_code': 'PF_EMPLOYEE',
                    'name': 'Employee PF',
                    'component_type': 'EMPLOYEE_DEDUCTION',
                    'monthly_amount': '999',
                    'is_taxable': False,
                },
                {
                    'component_code': 'PF_EMPLOYER',
                    'name': 'Employer PF',
                    'component_type': 'EMPLOYER_CONTRIBUTION',
                    'monthly_amount': '999',
                    'is_taxable': False,
                },
                {
                    'component_code': 'MEAL_CARD',
                    'name': 'Meal Card',
                    'component_type': 'EMPLOYEE_DEDUCTION',
                    'monthly_amount': '500',
                    'is_taxable': False,
                },
                {
                    'component_code': 'NPS_EMPLOYER',
                    'name': 'NPS Employer',
                    'component_type': 'EMPLOYER_CONTRIBUTION',
                    'monthly_amount': '750',
                    'is_taxable': False,
                },
            ],
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        pf_employer_line = next(line for line in item.snapshot['lines'] if line['component_code'] == 'PF_EMPLOYER')
        meal_card_line = next(line for line in item.snapshot['lines'] if line['component_code'] == 'MEAL_CARD')
        nps_line = next(line for line in item.snapshot['lines'] if line['component_code'] == 'NPS_EMPLOYER')
        assert pf_employer_line['auto_calculated'] is True
        assert Decimal(pf_employer_line['monthly_amount']) == Decimal('1800.00')
        assert meal_card_line['auto_calculated'] is False
        assert nps_line['auto_calculated'] is False
        assert Decimal(item.employee_deductions) >= Decimal('2300.00')
        assert Decimal(item.employer_contributions) >= Decimal('2550.00')

    def test_calculate_pay_run_falls_back_when_attendance_service_errors(self):
        organisation = _create_active_organisation('Attendance Fallback Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'attendance-fallback-requester@test.com',
            employee_code='EMPAT1',
        )
        _employee_user, employee = _create_employee(
            organisation,
            'attendance-fallback-employee@test.com',
            role='EMPLOYEE',
            employee_code='EMPAT2',
        )
        _seed_ct_tax_master(requester_user)
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, monthly_amount='30000')
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
            use_attendance_inputs=True,
        )

        with patch('apps.attendance.services.get_payroll_attendance_summary', side_effect=RuntimeError('boom')):
            calculate_pay_run(pay_run, actor=requester_user)

        item = pay_run.items.get(employee=employee)
        assert item.snapshot['attendance']['attendance_source'] == 'unavailable'

    def test_finalize_pay_run_requires_ready_items_even_when_calculated(self):
        organisation = _create_active_organisation('Finalize Ready Guard Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'finalize-ready-guard@test.com',
            employee_code='EMPFIN1',
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )
        pay_run.status = PayrollRunStatus.CALCULATED
        pay_run.save(update_fields=['status'])

        with pytest.raises(ValueError):
            finalize_pay_run(pay_run, actor=requester_user, skip_approval=True)

    def test_calculate_pay_run_prorates_joining_and_exit_month(self):
        organisation = _create_active_organisation('Proration Org')
        requester_user, _requester_employee = _create_employee(
            organisation,
            'proration-requester@test.com',
            employee_code='EMPRC8',
        )
        _joiner_user, joiner = _create_employee(
            organisation,
            'joiner@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC9',
        )
        _exiter_user, exiter = _create_employee(
            organisation,
            'exiter@test.com',
            role='EMPLOYEE',
            employee_code='EMPRC10',
        )
        joiner.date_of_joining = date(2026, 4, 15)
        joiner.save(update_fields=['date_of_joining'])
        exiter.date_of_exit = date(2026, 4, 10)
        exiter.save(update_fields=['date_of_exit'])

        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='CT Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': None, 'rate_percent': '10'},
            ],
            organisation=None,
            actor=requester_user,
        )
        ensure_org_payroll_setup(organisation, actor=requester_user)
        template = _basic_template(organisation, requester_user, name='Proration Template')
        for employee in (joiner, exiter):
            assign_employee_compensation(
                employee,
                template,
                effective_from=date(2026, 4, 1),
                actor=requester_user,
                auto_approve=True,
            )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        calculate_pay_run(pay_run, actor=requester_user)

        joiner_item = pay_run.items.get(employee=joiner)
        exiter_item = pay_run.items.get(employee=exiter)
        assert joiner_item.snapshot['paid_days'] == 16
        assert joiner_item.gross_pay == Decimal('16000.00')
        assert exiter_item.snapshot['paid_days'] == 10
        assert exiter_item.gross_pay == Decimal('10000.00')
