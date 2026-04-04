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
