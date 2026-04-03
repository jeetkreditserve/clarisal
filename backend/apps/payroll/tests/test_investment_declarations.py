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
        name='Investment Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='investment.employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code='INV001',
        designation='Analyst',
        status=EmployeeStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestInvestmentDeclarationModel:
    def test_investment_declaration_created_for_employee(self):
        from apps.payroll.models import InvestmentDeclaration, InvestmentSection

        employee = _create_employee()
        declaration = InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2024-25',
            section=InvestmentSection.SECTION_80C,
            description='PPF Contribution',
            declared_amount=Decimal('150000.00'),
        )

        assert declaration.employee == employee
        assert declaration.declared_amount == Decimal('150000.00')

    def test_80c_limit_enforced_at_1_50_000(self):
        from apps.payroll.models import InvestmentDeclaration, InvestmentSection
        from apps.payroll.services import get_total_80c_deduction

        employee = _create_employee()
        InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2024-25',
            section=InvestmentSection.SECTION_80C,
            description='LIC Premium',
            declared_amount=Decimal('100000.00'),
        )
        InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2024-25',
            section=InvestmentSection.SECTION_80C,
            description='ELSS',
            declared_amount=Decimal('100000.00'),
        )

        total = get_total_80c_deduction(employee, '2024-25')

        assert total == Decimal('150000.00')

    def test_investment_deduction_reduces_taxable_income_for_old_regime(self):
        from apps.payroll.models import InvestmentDeclaration, InvestmentSection, TaxRegime
        from apps.payroll.services import calculate_taxable_income_with_investments

        employee = _create_employee()
        InvestmentDeclaration.objects.create(
            employee=employee,
            fiscal_year='2024-25',
            section=InvestmentSection.SECTION_80C,
            description='PPF',
            declared_amount=Decimal('150000.00'),
        )

        taxable = calculate_taxable_income_with_investments(
            employee=employee,
            annual_gross=Decimal('1000000.00'),
            fiscal_year='2024-25',
            tax_regime=TaxRegime.OLD,
        )

        assert taxable == Decimal('775000.00')
