from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.payroll.services import assign_employee_compensation, create_compensation_template
from apps.timeoff.models import LeaveBalance, LeaveCycle, LeaveCycleType, LeavePlan, LeaveType
from apps.timeoff.services import get_cycle_window


def _create_employee(*, date_of_joining=None):
    organisation = Organisation.objects.create(
        name='FNF Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='fnf.employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code='FNF001',
        designation='Manager',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date_of_joining,
    )


def _assign_basic_compensation(employee, *, monthly_amount='26000.00', effective_from=date(2026, 1, 1), name='FNF Basic'):
    template = create_compensation_template(
        employee.organisation,
        name=name,
        actor=employee.user,
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
    assign_employee_compensation(
        employee,
        template,
        effective_from=effective_from,
        actor=employee.user,
        auto_approve=True,
    )


@pytest.mark.django_db
class TestFullAndFinalSettlement:
    def test_fnf_created_on_offboarding_initiation(self):
        from apps.payroll.models import FNFStatus
        from apps.payroll.services import create_full_and_final_settlement

        employee = _create_employee()
        fnf = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2025, 3, 31),
            initiated_by=employee.user,
        )

        assert fnf.employee == employee
        assert fnf.status == FNFStatus.DRAFT
        assert fnf.last_working_day == date(2025, 3, 31)

    def test_salary_proration_for_exit_month(self):
        from apps.payroll.services import calculate_fnf_salary_proration

        result = calculate_fnf_salary_proration(
            gross_monthly_salary=Decimal('100000.00'),
            last_working_day=date(2025, 3, 15),
            period_year=2025,
            period_month=3,
        )

        assert result == Decimal('48387.10')

    def test_leave_encashment_in_fnf(self):
        from apps.payroll.services import calculate_leave_encashment_amount

        amount = calculate_leave_encashment_amount(
            leave_days=Decimal('10.00'),
            monthly_basic_salary=Decimal('50000.00'),
        )

        assert amount == Decimal('19230.80')

    def test_fnf_automatically_adds_gratuity_from_final_effective_assignment(self):
        from apps.payroll.services import create_full_and_final_settlement

        employee = _create_employee(date_of_joining=date(2021, 1, 1))
        first_template = create_compensation_template(
            employee.organisation,
            name='Legacy Basic',
            actor=employee.user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '20000.00',
                    'is_taxable': True,
                },
            ],
        )
        assign_employee_compensation(
            employee,
            first_template,
            effective_from=date(2025, 1, 1),
            actor=employee.user,
            auto_approve=True,
        )
        latest_template = create_compensation_template(
            employee.organisation,
            name='Current Basic',
            actor=employee.user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '26000.00',
                    'is_taxable': True,
                },
            ],
        )
        assign_employee_compensation(
            employee,
            latest_template,
            effective_from=date(2026, 1, 1),
            actor=employee.user,
            auto_approve=True,
        )

        fnf = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=employee.user,
        )

        assert fnf.prorated_salary == Decimal('26000.00')
        assert fnf.gratuity == Decimal('75000.00')
        assert fnf.gross_payable == Decimal('101000.00')
        assert fnf.net_payable == Decimal('101000.00')

    @pytest.mark.parametrize(
        ('date_of_joining', 'expected_gratuity'),
        [
            (date(2021, 6, 30), Decimal('75000.00')),
            (date(2021, 8, 31), Decimal('0.00')),
            (date(2021, 1, 31), Decimal('75000.00')),
            (date(2021, 7, 30), Decimal('75000.00')),
            (date(2023, 1, 31), Decimal('0.00')),
        ],
    )
    def test_fnf_gratuity_gate_uses_gratuity_service_years_rounding(self, date_of_joining, expected_gratuity):
        from apps.payroll.services import create_full_and_final_settlement

        employee = _create_employee(date_of_joining=date_of_joining)
        _assign_basic_compensation(
            employee,
            monthly_amount='26000.00',
            effective_from=date(2026, 1, 1),
            name=f'Eligibility Basic {date_of_joining.isoformat()}',
        )

        fnf = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=employee.user,
        )

        assert fnf.gratuity == expected_gratuity

    def test_fnf_uses_encashable_leave_balance_and_respects_cap(self):
        from apps.payroll.services import create_full_and_final_settlement

        employee = _create_employee(date_of_joining=date(2021, 1, 1))
        template = create_compensation_template(
            employee.organisation,
            name='Encashment Basic',
            actor=employee.user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '50000.00',
                    'is_taxable': True,
                },
            ],
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 1, 1),
            actor=employee.user,
            auto_approve=True,
        )
        cycle = LeaveCycle.objects.create(
            organisation=employee.organisation,
            name='Calendar Year',
            cycle_type=LeaveCycleType.CALENDAR_YEAR,
            is_default=True,
        )
        plan = LeavePlan.objects.create(
            organisation=employee.organisation,
            leave_cycle=cycle,
            name='Default Leave Plan',
            is_default=True,
            is_active=True,
        )
        encashable_leave = LeaveType.objects.create(
            leave_plan=plan,
            code='PL',
            name='Privilege Leave',
            annual_entitlement=Decimal('0.00'),
            allows_encashment=True,
            max_encashment_days_per_year=Decimal('7.00'),
        )
        non_encashable_leave = LeaveType.objects.create(
            leave_plan=plan,
            code='SL',
            name='Sick Leave',
            annual_entitlement=Decimal('0.00'),
            allows_encashment=False,
        )
        cycle_start, cycle_end = get_cycle_window(cycle, employee, as_of=date(2026, 1, 31))
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=encashable_leave,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            opening_balance=Decimal('10.00'),
            credited_amount=Decimal('0.00'),
            used_amount=Decimal('0.00'),
            pending_amount=Decimal('0.00'),
            carried_forward_amount=Decimal('0.00'),
        )
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=non_encashable_leave,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            opening_balance=Decimal('5.00'),
            credited_amount=Decimal('0.00'),
            used_amount=Decimal('0.00'),
            pending_amount=Decimal('0.00'),
            carried_forward_amount=Decimal('0.00'),
        )

        fnf = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=employee.user,
        )

        assert fnf.leave_encashment == Decimal('13461.56')

    def test_fnf_keeps_leave_encashment_zero_without_encashable_balance(self):
        from apps.payroll.services import create_full_and_final_settlement

        employee = _create_employee(date_of_joining=date(2021, 1, 1))
        template = create_compensation_template(
            employee.organisation,
            name='No Encashment Basic',
            actor=employee.user,
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '50000.00',
                    'is_taxable': True,
                },
            ],
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 1, 1),
            actor=employee.user,
            auto_approve=True,
        )

        fnf = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=employee.user,
        )

        assert fnf.leave_encashment == Decimal('0.00')

    def test_fnf_exemption_breakdown_caps_non_government_components(self):
        from apps.payroll.services import _calculate_fnf_exemption_breakdown

        employee = _create_employee(date_of_joining=date(2021, 1, 1))

        breakdown = _calculate_fnf_exemption_breakdown(
            employee=employee,
            gratuity=Decimal('2500000.00'),
            leave_encashment=Decimal('3000000.00'),
        )

        assert breakdown['gratuity_exemption'] == Decimal('2000000.00')
        assert breakdown['gratuity_taxable'] == Decimal('500000.00')
        assert breakdown['leave_encashment_exemption'] == Decimal('2500000.00')
        assert breakdown['leave_encashment_taxable'] == Decimal('500000.00')

    def test_fnf_exemption_breakdown_fully_exempts_government_body_employee(self):
        from apps.payroll.services import _calculate_fnf_exemption_breakdown

        employee = _create_employee(date_of_joining=date(2021, 1, 1))
        employee.organisation.entity_type = 'GOVERNMENT_BODY'
        employee.organisation.save(update_fields=['entity_type', 'modified_at'])

        breakdown = _calculate_fnf_exemption_breakdown(
            employee=employee,
            gratuity=Decimal('2500000.00'),
            leave_encashment=Decimal('3000000.00'),
        )

        assert breakdown['gratuity_exemption'] == Decimal('2500000.00')
        assert breakdown['gratuity_taxable'] == Decimal('0.00')
        assert breakdown['leave_encashment_exemption'] == Decimal('3000000.00')
        assert breakdown['leave_encashment_taxable'] == Decimal('0.00')

    def test_fnf_recalculates_tds_for_taxable_other_credits(self):
        from apps.payroll.services import create_full_and_final_settlement

        employee = _create_employee(date_of_joining=date(2021, 1, 1))
        _assign_basic_compensation(
            employee,
            monthly_amount='26000.00',
            effective_from=date(2026, 1, 1),
            name='FNF TDS Basic',
        )

        settlement = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=employee.user,
        )
        settlement.other_credits = Decimal('1500000.00')
        settlement.save(update_fields=['other_credits', 'modified_at'])

        settlement = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=employee.user,
        )

        assert settlement.tds_deduction == Decimal('101556.00')
        assert settlement.net_payable == Decimal('1499444.00')
