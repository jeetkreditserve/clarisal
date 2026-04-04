from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalWorkflow, ApprovalWorkflowRule
from apps.employees.models import Employee, EmployeeOffboardingProcess, EmployeeProfile, EmployeeStatus
from apps.notifications.models import NotificationKind
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationAddress,
    OrganisationAddressType,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.payroll.models import (
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationTemplate,
    LabourWelfareFundContribution,
    LabourWelfareFundRule,
    PayrollComponent,
    PayrollComponentType,
    PayrollRun,
    PayrollRunItem,
    PayrollRunItemStatus,
    ProfessionalTaxGender,
    ProfessionalTaxRule,
    ProfessionalTaxSlab,
    StatutoryDeductionFrequency,
    StatutoryIncomeBasis,
)
from apps.payroll.services import (
    _build_rendered_payslip,
    _calculate_fnf_totals,
    _completed_service_years,
    _create_payroll_approval_run,
    _current_fiscal_year,
    _fiscal_year_for_period,
    _fmt_inr,
    _get_assignment_monthly_amounts,
    _get_or_create_component,
    _normalize_decimal,
    _notify_employees_payroll_finalized,
    _resolve_labour_welfare_fund_amount,
    _resolve_organisation_payroll_state_code,
    _resolve_professional_tax_amount,
    _summarize_pay_run_exceptions,
    assign_employee_compensation,
    calculate_fnf_salary_proration,
    calculate_leave_encashment_amount,
    create_compensation_template,
    create_full_and_final_settlement,
    create_payroll_run,
    ensure_non_negative_net_pay,
    submit_compensation_assignment_for_approval,
    submit_compensation_template_for_approval,
)
from apps.payroll.statutory import calculate_professional_tax_monthly

from .test_service_setup import _attach_registered_and_billing_addresses, _create_employee


def _create_active_organisation(name='Payroll Helpers Org'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    _attach_registered_and_billing_addresses(organisation)
    batch = create_licence_batch(
        organisation,
        quantity=5,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    return organisation


def _create_user(email, *, organisation=None, role=UserRole.EMPLOYEE):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=role,
        organisation=organisation,
        is_active=True,
    )


@pytest.mark.django_db
class TestPayrollServiceHelpers:
    def test_professional_tax_for_maharashtra_thresholds(self):
        slabs_by_state = {
            'MH': [
                (Decimal('10000.00'), Decimal('0.00')),
                (Decimal('15000.00'), Decimal('150.00')),
                (None, Decimal('200.00')),
            ]
        }
        assert calculate_professional_tax_monthly(Decimal('9999.00'), 'MH', slabs_by_state=slabs_by_state) == Decimal('0.00')
        assert calculate_professional_tax_monthly(Decimal('12000.00'), 'MH', slabs_by_state=slabs_by_state) == Decimal('150.00')
        assert calculate_professional_tax_monthly(Decimal('18000.00'), 'MH', slabs_by_state=slabs_by_state) == Decimal('200.00')

    def test_professional_tax_non_maharashtra_is_zero(self):
        assert calculate_professional_tax_monthly(Decimal('40000.00'), 'KA', slabs_by_state={}) == Decimal('0.00')

    def test_current_fiscal_year_switches_in_april(self):
        class AprilDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 4, 2)

        class FebruaryDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 2, 2)

        with patch('apps.payroll.services.date', AprilDate):
            assert _current_fiscal_year() == '2026-2027'
        with patch('apps.payroll.services.date', FebruaryDate):
            assert _current_fiscal_year() == '2025-2026'

    def test_normalize_decimal_handles_none_decimal_and_string(self):
        assert _normalize_decimal(None) is None
        assert _normalize_decimal(Decimal('10')) == Decimal('10.00')
        assert _normalize_decimal('12.345') == Decimal('12.34')

    def test_fiscal_year_for_period_handles_april_and_january(self):
        assert _fiscal_year_for_period(2026, 4) == '2026-2027'
        assert _fiscal_year_for_period(2026, 1) == '2025-2026'

    def test_get_or_create_component_updates_existing_component(self):
        organisation = _create_active_organisation()
        component = PayrollComponent.objects.create(
            organisation=organisation,
            code='HRA',
            name='Old HRA',
            component_type=PayrollComponentType.EMPLOYEE_DEDUCTION,
            is_taxable=False,
        )

        result = _get_or_create_component(
            organisation,
            {
                'component_code': 'HRA',
                'name': 'House Rent Allowance',
                'component_type': PayrollComponentType.EARNING,
                'is_taxable': True,
            },
        )

        component.refresh_from_db()
        assert result.id == component.id
        assert component.name == 'House Rent Allowance'
        assert component.component_type == PayrollComponentType.EARNING
        assert component.is_taxable is True

    def test_fmt_inr_formats_positive_negative_and_invalid_values(self):
        assert _fmt_inr(Decimal('1234567.89')) == '₹12,34,567.89'
        assert _fmt_inr(Decimal('-1200')) == '-₹1,200.00'
        assert _fmt_inr('not-a-number') == 'not-a-number'

    def test_build_rendered_payslip_includes_key_sections(self):
        rendered = _build_rendered_payslip(
            {
                'period_label': 'April 2026',
                'employee_name': 'Ada Lovelace',
                'paid_days': '20',
                'total_days_in_period': '30',
                'gross_pay': '50000.00',
                'arrears': '1250.00',
                'income_tax': '2000.00',
                'total_deductions': '5000.00',
                'net_pay': '45000.00',
                'lop_days': '2.00',
                'lop_deduction': '3000.00',
                'annual_taxable_gross': '600000.00',
                'annual_standard_deduction': '75000.00',
                'annual_taxable_after_sd': '525000.00',
                'annual_tax_before_rebate': '10000.00',
                'annual_surcharge': '1000.00',
                'annual_tax_before_cess': '10000.00',
                'annual_cess': '400.00',
                'annual_tax_total': '10400.00',
                'lines': [
                    {
                        'component_name': 'Basic Pay',
                        'component_type': PayrollComponentType.EARNING,
                        'monthly_amount': '30000.00',
                    },
                    {
                        'component_name': 'Employee PF',
                        'component_type': PayrollComponentType.EMPLOYEE_DEDUCTION,
                        'component_code': 'PF_EMPLOYEE',
                        'monthly_amount': '3600.00',
                        'auto_calculated': True,
                    },
                    {
                        'component_name': 'Employer PF',
                        'component_type': PayrollComponentType.EMPLOYER_CONTRIBUTION,
                        'component_code': 'PF_EMPLOYER',
                        'monthly_amount': '3600.00',
                        'auto_calculated': True,
                    },
                ],
            }
        )

        assert 'PAYSLIP' in rendered
        assert 'Ada Lovelace' in rendered
        assert 'Arrears' in rendered
        assert 'Loss of Pay (2.00 day(s))' in rendered
        assert 'Surcharge' in rendered
        assert 'NET PAY (Take-Home)' in rendered
        assert '* auto-calculated statutory component' in rendered

    def test_build_rendered_payslip_tolerates_invalid_arrears_and_lop_values(self):
        rendered = _build_rendered_payslip(
            {
                'period_label': 'April 2026',
                'employee_name': 'Ada Lovelace',
                'gross_pay': '50000.00',
                'arrears': object(),
                'income_tax': '2000.00',
                'total_deductions': '5000.00',
                'net_pay': '45000.00',
                'lop_days': 'bad',
                'lop_deduction': object(),
                'lines': [],
            }
        )

        assert 'Arrears' not in rendered
        assert 'Loss of Pay' not in rendered

    def test_get_assignment_monthly_amounts_sums_only_earnings_and_tracks_basic(self):
        organisation = _create_active_organisation('Assignment Amount Org')
        user = _create_user('assignment@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=user,
            employee_code='EMPH01',
            designation='Engineer',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 4, 1),
        )
        template = CompensationTemplate.objects.create(
            organisation=organisation,
            name='Helpers Template',
        )
        assignment = CompensationAssignment.objects.create(
            employee=employee,
            template=template,
            effective_from=date(2026, 4, 1),
        )
        basic = PayrollComponent.objects.create(
            organisation=organisation,
            code='BASIC',
            name='Basic',
            component_type=PayrollComponentType.EARNING,
        )
        hra = PayrollComponent.objects.create(
            organisation=organisation,
            code='HRA',
            name='HRA',
            component_type=PayrollComponentType.EARNING,
        )
        deduction = PayrollComponent.objects.create(
            organisation=organisation,
            code='PF_EMPLOYEE',
            name='Employee PF',
            component_type=PayrollComponentType.EMPLOYEE_DEDUCTION,
            is_taxable=False,
        )
        CompensationAssignmentLine.objects.create(
            assignment=assignment,
            component=basic,
            component_name='Basic',
            component_type=PayrollComponentType.EARNING,
            monthly_amount=Decimal('30000.00'),
            is_taxable=True,
            sequence=1,
        )
        CompensationAssignmentLine.objects.create(
            assignment=assignment,
            component=hra,
            component_name='HRA',
            component_type=PayrollComponentType.EARNING,
            monthly_amount=Decimal('12000.00'),
            is_taxable=True,
            sequence=2,
        )
        CompensationAssignmentLine.objects.create(
            assignment=assignment,
            component=deduction,
            component_name='Employee PF',
            component_type=PayrollComponentType.EMPLOYEE_DEDUCTION,
            monthly_amount=Decimal('3600.00'),
            is_taxable=False,
            sequence=3,
        )

        gross, basic_amount = _get_assignment_monthly_amounts(assignment)

        assert gross == Decimal('42000.00')
        assert basic_amount == Decimal('30000.00')

    def test_fnf_salary_proration_and_leave_encashment_helpers(self):
        assert calculate_fnf_salary_proration(
            gross_monthly_salary=Decimal('62000.00'),
            last_working_day=date(2026, 4, 15),
            period_year=2026,
            period_month=4,
        ) == Decimal('31000.00')
        assert calculate_leave_encashment_amount(
            leave_days=Decimal('5.00'),
            monthly_basic_salary=Decimal('26000.00'),
        ) == Decimal('5000.00')

    def test_notify_employees_payroll_finalized_creates_notifications_and_queues_email(self):
        organisation = _create_active_organisation('Notify Org')
        actor = _create_user('payroll.actor@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        employee_user = _create_user('payroll.employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMPNOT1',
            designation='Engineer',
            status=EmployeeStatus.ACTIVE,
        )
        pay_run = PayrollRun.objects.create(
            organisation=organisation,
            name='April Payroll',
            period_year=2026,
            period_month=4,
        )
        pay_run_item = PayrollRunItem.objects.create(
            pay_run=pay_run,
            employee=employee,
            gross_pay=Decimal('50000.00'),
            net_pay=Decimal('45000.00'),
        )
        payslip = pay_run.payslips.model.objects.create(
            organisation=organisation,
            employee=employee,
            pay_run=pay_run,
            pay_run_item=pay_run_item,
            slip_number='202604-EMPNOT1',
            period_year=2026,
            period_month=4,
            snapshot={},
            rendered_text='Rendered slip',
        )
        assert payslip.employee == employee

        with patch('apps.payroll.services.create_notification') as mock_notification, patch(
            'apps.notifications.tasks.send_payroll_ready_email.delay'
        ) as mock_delay, patch('apps.payroll.services.transaction.on_commit', side_effect=lambda fn: fn()):
            _notify_employees_payroll_finalized(pay_run, actor=actor)

        mock_notification.assert_called_once()
        assert mock_notification.call_args.kwargs['recipient'] == employee_user
        assert mock_notification.call_args.kwargs['kind'] == NotificationKind.PAYROLL_FINALIZED
        mock_delay.assert_called_once_with(str(employee_user.id), pay_period='April 2026')

    def test_summarize_pay_run_exceptions_limits_to_first_three_and_counts_more(self):
        organisation = _create_active_organisation('Exception Summary Org')
        pay_run = PayrollRun.objects.create(
            organisation=organisation,
            name='April Payroll',
            period_year=2026,
            period_month=4,
        )
        for idx in range(4):
            user = _create_user(f'exception-{idx}@test.com', organisation=organisation)
            employee = Employee.objects.create(
                organisation=organisation,
                user=user,
                employee_code=f'EXC{idx}',
                designation='Engineer',
                status=EmployeeStatus.ACTIVE,
            )
            PayrollRunItem.objects.create(
                pay_run=pay_run,
                employee=employee,
                status=PayrollRunItemStatus.EXCEPTION,
                message=f'Problem {idx}',
            )

        summary = _summarize_pay_run_exceptions(pay_run)

        assert 'Problem 0' in summary
        assert 'Problem 1' in summary
        assert 'Problem 2' in summary
        assert '+1 more' in summary

    def test_completed_service_years_handles_missing_and_pre_anniversary_dates(self):
        assert _completed_service_years(None, date(2026, 4, 1)) == 0
        assert _completed_service_years(date(2026, 4, 2), date(2026, 4, 1)) == 0
        assert _completed_service_years(date(2021, 5, 1), date(2026, 4, 30)) == 4

    def test_calculate_fnf_totals_includes_existing_deductions_when_assignment_missing(self):
        organisation = _create_active_organisation('FNF Missing Assignment Org')
        user = _create_user('fnf-missing@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=user,
            employee_code='FNFMISS1',
            designation='Engineer',
            status=EmployeeStatus.ACTIVE,
        )
        settlement = type(
            'Settlement',
            (),
            {
                'arrears': Decimal('1000.00'),
                'other_credits': Decimal('500.00'),
                'tds_deduction': Decimal('200.00'),
                'pf_deduction': Decimal('100.00'),
                'loan_recovery': Decimal('50.00'),
                'other_deductions': Decimal('25.00'),
            },
        )()

        totals = _calculate_fnf_totals(employee, date(2026, 4, 30), settlement=settlement)

        assert totals['gross_payable'] == Decimal('1500.00')
        assert totals['net_payable'] == Decimal('1125.00')

    def test_create_full_and_final_settlement_updates_last_working_day_and_offboarding_process(self):
        organisation = _create_active_organisation('FNF Update Org')
        user = _create_user('fnf-update@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=user,
            employee_code='FNFUP1',
            designation='Engineer',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2021, 1, 1),
        )
        template = create_compensation_template(
            organisation,
            name='FNF Update Template',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '26000.00',
                    'is_taxable': True,
                }
            ],
            actor=user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 1, 1),
            actor=user,
            auto_approve=True,
        )
        create_full_and_final_settlement(employee, date(2026, 1, 31), initiated_by=user)
        process = EmployeeOffboardingProcess.objects.create(
            organisation=organisation,
            employee=employee,
            status='IN_PROGRESS',
            initiated_by=user,
            exit_status=EmployeeStatus.RESIGNED,
            date_of_exit=date(2026, 2, 15),
        )

        updated = create_full_and_final_settlement(
            employee,
            date(2026, 2, 15),
            initiated_by=user,
            offboarding_process=process,
        )

        assert updated.last_working_day == date(2026, 2, 15)
        assert updated.offboarding_process == process

    def test_create_payroll_approval_run_rejects_workflow_without_stages(self):
        organisation = _create_active_organisation('Workflow Stage Guard Org')
        requester_user, requester_employee = _create_employee(
            organisation,
            'stage-guard@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='WF001',
        )
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Empty payroll workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.PAYROLL_PROCESSING,
            is_active=True,
        )
        ApprovalWorkflowRule.objects.create(
            workflow=workflow,
            name='Empty stage rule',
            request_kind=ApprovalRequestKind.PAYROLL_PROCESSING,
            priority=100,
            is_active=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            requester_user=requester_user,
        )

        with pytest.raises(ValueError):
            _create_payroll_approval_run(
                pay_run,
                ApprovalRequestKind.PAYROLL_PROCESSING,
                organisation,
                requester_user,
                requester_employee=requester_employee,
            )

    def test_submitters_reject_non_draft_template_and_assignment(self):
        organisation = _create_active_organisation('Submitter Guard Org')
        requester_user, employee = _create_employee(
            organisation,
            'submitter-guard@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='SUB001',
        )
        template = create_compensation_template(
            organisation,
            name='Guard Template',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '30000.00',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )
        template.status = 'PENDING_APPROVAL'
        template.save(update_fields=['status'])
        assignment = assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=requester_user,
            auto_approve=True,
        )

        with pytest.raises(ValueError):
            submit_compensation_template_for_approval(template, requester_user=requester_user)
        with pytest.raises(ValueError):
            submit_compensation_assignment_for_approval(assignment, requester_user=requester_user)

    def test_assign_employee_compensation_rejects_invalid_vpf_rates(self):
        organisation = _create_active_organisation('VPF Guard Org')
        requester_user, employee = _create_employee(
            organisation,
            'vpf-guard@test.com',
            role=UserRole.ORG_ADMIN,
            employee_code='VPF001',
        )
        template = create_compensation_template(
            organisation,
            name='VPF Guard Template',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '30000.00',
                    'is_taxable': True,
                }
            ],
            actor=requester_user,
        )

        with pytest.raises(ValueError):
            assign_employee_compensation(
                employee,
                template,
                effective_from=date(2026, 4, 1),
                actor=requester_user,
                vpf_rate_percent=Decimal('10.00'),
            )
        with pytest.raises(ValueError):
            assign_employee_compensation(
                employee,
                template,
                effective_from=date(2026, 4, 1),
                actor=requester_user,
                vpf_rate_percent=Decimal('120.00'),
            )

    def test_resolve_organisation_payroll_state_code_raises_without_active_stateful_address(self):
        organisation = _create_active_organisation('State Guard Org')
        organisation.addresses.all().delete()
        OrganisationAddress.objects.create(
            organisation=organisation,
            address_type=OrganisationAddressType.REGISTERED,
            label='Broken',
            line1='1 Broken St',
            city='Nowhere',
            state='',
            state_code='',
            country='India',
            country_code='IN',
            pincode='400001',
            is_active=True,
        )

        with pytest.raises(ValueError):
            _resolve_organisation_payroll_state_code(organisation)

    def test_resolve_professional_tax_amount_raises_without_active_rule(self):
        organisation = _create_active_organisation('PT Missing Rule Org')
        _user, employee = _create_employee(organisation, 'pt-missing@test.com', employee_code='PT001')

        with pytest.raises(ValueError):
            _resolve_professional_tax_amount(
                employee=employee,
                state_code='KA',
                gross_pay=Decimal('25000.00'),
                period_year=2026,
                period_month=4,
            )

    def test_resolve_professional_tax_amount_prefers_female_specific_slab(self):
        organisation = _create_active_organisation('PT Female Org')
        _user, employee = _create_employee(organisation, 'pt-female@test.com', employee_code='PT002')
        EmployeeProfile.objects.create(employee=employee, gender='FEMALE')
        rule = ProfessionalTaxRule.objects.create(
            country_code='IN',
            state_code='MH',
            state_name='Maharashtra',
            income_basis=StatutoryIncomeBasis.MONTHLY,
            deduction_frequency=StatutoryDeductionFrequency.MONTHLY,
            effective_from=date(2020, 1, 1),
            is_active=True,
        )
        ProfessionalTaxSlab.objects.create(
            rule=rule,
            gender=ProfessionalTaxGender.FEMALE,
            min_income=Decimal('0.00'),
            max_income=Decimal('30000.00'),
            deduction_amount=Decimal('50.00'),
        )
        ProfessionalTaxSlab.objects.create(
            rule=rule,
            gender=ProfessionalTaxGender.ANY,
            min_income=Decimal('0.00'),
            max_income=None,
            deduction_amount=Decimal('200.00'),
        )

        amount, _rule, basis = _resolve_professional_tax_amount(
            employee=employee,
            state_code='MH',
            gross_pay=Decimal('25000.00'),
            period_year=2026,
            period_month=4,
        )

        assert amount == Decimal('50.00')
        assert basis == Decimal('25000.00')

    def test_resolve_professional_tax_amount_skips_non_matching_max_income_slab(self):
        organisation = _create_active_organisation('PT Slab Continue Org')
        _user, employee = _create_employee(organisation, 'pt-continue@test.com', employee_code='PT003')
        rule = ProfessionalTaxRule.objects.create(
            country_code='IN',
            state_code='WB',
            state_name='West Bengal',
            income_basis=StatutoryIncomeBasis.MONTHLY,
            deduction_frequency=StatutoryDeductionFrequency.MONTHLY,
            effective_from=date(2020, 1, 1),
            is_active=True,
        )
        ProfessionalTaxSlab.objects.create(
            rule=rule,
            gender=ProfessionalTaxGender.ANY,
            min_income=Decimal('0.00'),
            max_income=Decimal('10000.00'),
            deduction_amount=Decimal('0.00'),
        )
        ProfessionalTaxSlab.objects.create(
            rule=rule,
            gender=ProfessionalTaxGender.ANY,
            min_income=Decimal('10000.01'),
            max_income=Decimal('20000.00'),
            deduction_amount=Decimal('110.00'),
        )

        amount, _rule, basis = _resolve_professional_tax_amount(
            employee=employee,
            state_code='WB',
            gross_pay=Decimal('15000.00'),
            period_year=2026,
            period_month=4,
        )

        assert amount == Decimal('110.00')
        assert basis == Decimal('15000.00')

    def test_resolve_professional_tax_amount_skips_gender_slab_with_higher_min_income(self):
        organisation = _create_active_organisation('PT Min Income Continue Org')
        _user, employee = _create_employee(organisation, 'pt-min-continue@test.com', employee_code='PT004')
        EmployeeProfile.objects.create(employee=employee, gender='FEMALE')
        rule = ProfessionalTaxRule.objects.create(
            country_code='IN',
            state_code='MH',
            state_name='Maharashtra',
            income_basis=StatutoryIncomeBasis.MONTHLY,
            deduction_frequency=StatutoryDeductionFrequency.MONTHLY,
            effective_from=date(2020, 1, 1),
            is_active=True,
        )
        ProfessionalTaxSlab.objects.create(
            rule=rule,
            gender=ProfessionalTaxGender.FEMALE,
            min_income=Decimal('30000.00'),
            max_income=None,
            deduction_amount=Decimal('200.00'),
        )
        ProfessionalTaxSlab.objects.create(
            rule=rule,
            gender=ProfessionalTaxGender.ANY,
            min_income=Decimal('0.00'),
            max_income=None,
            deduction_amount=Decimal('75.00'),
        )

        amount, _rule, basis = _resolve_professional_tax_amount(
            employee=employee,
            state_code='MH',
            gross_pay=Decimal('25000.00'),
            period_year=2026,
            period_month=4,
        )

        assert amount == Decimal('75.00')
        assert basis == Decimal('25000.00')

    def test_resolve_labour_welfare_fund_amount_handles_missing_rule_and_annual_basis(self):
        result, rule, basis = _resolve_labour_welfare_fund_amount(
            state_code='ZZ',
            gross_pay=Decimal('1000.00'),
            period_year=2026,
            period_month=4,
        )
        assert result['is_applicable'] is False
        assert rule is None
        assert basis == Decimal('1000.00')

        annual_rule = LabourWelfareFundRule.objects.create(
            country_code='IN',
            state_code='KA',
            state_name='Karnataka',
            wage_basis=StatutoryIncomeBasis.ANNUAL,
            deduction_frequency=StatutoryDeductionFrequency.ANNUAL,
            effective_from=date(2020, 1, 1),
            is_active=True,
        )
        LabourWelfareFundContribution.objects.create(
            rule=annual_rule,
            min_wage=Decimal('10000.00'),
            max_wage=None,
            employee_amount=Decimal('20.00'),
            employer_amount=Decimal('40.00'),
            applicable_months=[12],
        )

        result, rule, basis = _resolve_labour_welfare_fund_amount(
            state_code='KA',
            gross_pay=Decimal('1000.00'),
            period_year=2026,
            period_month=12,
        )

        assert rule == annual_rule
        assert basis == Decimal('12000.00')
        assert result['employee'] == Decimal('20.00')

    def test_resolve_labour_welfare_fund_amount_handles_half_yearly_basis(self):
        rule = LabourWelfareFundRule.objects.create(
            country_code='IN',
            state_code='TN',
            state_name='Tamil Nadu',
            wage_basis=StatutoryIncomeBasis.HALF_YEARLY,
            deduction_frequency=StatutoryDeductionFrequency.HALF_YEARLY,
            effective_from=date(2020, 1, 1),
            is_active=True,
        )
        LabourWelfareFundContribution.objects.create(
            rule=rule,
            min_wage=Decimal('30000.00'),
            max_wage=None,
            employee_amount=Decimal('10.00'),
            employer_amount=Decimal('20.00'),
            applicable_months=[6, 12],
        )

        result, resolved_rule, basis = _resolve_labour_welfare_fund_amount(
            state_code='TN',
            gross_pay=Decimal('5000.00'),
            period_year=2026,
            period_month=6,
        )

        assert resolved_rule == rule
        assert basis == Decimal('30000.00')
        assert result['employee'] == Decimal('10.00')

    def test_ensure_non_negative_net_pay_clamps_negative_values(self):
        assert ensure_non_negative_net_pay(Decimal('-25.00')) == Decimal('0.00')
        assert ensure_non_negative_net_pay(Decimal('725.50')) == Decimal('725.50')
