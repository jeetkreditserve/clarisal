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


def _create_employee():
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
