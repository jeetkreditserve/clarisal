from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.notifications.models import NotificationKind
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.payroll.models import (
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationTemplate,
    PayrollComponent,
    PayrollComponentType,
    PayrollRun,
    PayrollRunItem,
)
from apps.payroll.services import (
    _build_rendered_payslip,
    _current_fiscal_year,
    _fiscal_year_for_period,
    _fmt_inr,
    _get_assignment_monthly_amounts,
    _get_or_create_component,
    _normalize_decimal,
    _notify_employees_payroll_finalized,
    _professional_tax_monthly,
    calculate_fnf_salary_proration,
    calculate_leave_encashment_amount,
    ensure_non_negative_net_pay,
)


def _create_active_organisation(name='Payroll Helpers Org'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
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
        assert _professional_tax_monthly(Decimal('9999.00'), 'MH') == Decimal('0.00')
        assert _professional_tax_monthly(Decimal('12000.00'), 'MH') == Decimal('150.00')
        assert _professional_tax_monthly(Decimal('18000.00'), 'MH') == Decimal('200.00')

    def test_professional_tax_non_maharashtra_is_zero(self):
        assert _professional_tax_monthly(Decimal('40000.00'), 'KA') == Decimal('0.00')

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
        assert 'NET PAY (Take-Home)' in rendered
        assert '* auto-calculated statutory component' in rendered

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

    def test_ensure_non_negative_net_pay_clamps_negative_values(self):
        assert ensure_non_negative_net_pay(Decimal('-25.00')) == Decimal('0.00')
        assert ensure_non_negative_net_pay(Decimal('725.50')) == Decimal('725.50')
