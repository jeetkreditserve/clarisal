from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.payroll.services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
)


@pytest.fixture
def payroll_setup(db):
    organisation = Organisation.objects.create(
        name='Acme Payroll',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    ct_user = User.objects.create_user(
        email='ct-payroll@test.com',
        password='pass123!',
        account_type=AccountType.CONTROL_TOWER,
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )
    org_admin_user = User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=org_admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    employee_user = User.objects.create_user(
        email='employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP100',
        designation='Engineer',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 4, 1),
    )
    org_admin_client = APIClient()
    org_admin_client.force_authenticate(user=org_admin_user)
    session = org_admin_client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()

    employee_client = APIClient()
    employee_client.force_authenticate(user=employee_user)
    employee_session = employee_client.session
    employee_session['active_workspace_kind'] = 'EMPLOYEE'
    employee_session['active_employee_org_id'] = str(organisation.id)
    employee_session.save()

    ct_client = APIClient()
    ct_client.force_authenticate(user=ct_user)

    return {
        'organisation': organisation,
        'ct_user': ct_user,
        'org_admin_user': org_admin_user,
        'employee': employee,
        'org_admin_client': org_admin_client,
        'employee_client': employee_client,
        'ct_client': ct_client,
    }


@pytest.mark.django_db
class TestPayrollViews:
    def test_ct_can_create_master_and_org_summary_sees_seeded_copy(self, payroll_setup):
        ct_client = payroll_setup['ct_client']
        org_admin_client = payroll_setup['org_admin_client']

        response = ct_client.post(
            '/api/ct/payroll/tax-slab-sets/',
            {
                'name': 'FY 2026 Master',
                'country_code': 'IN',
                'fiscal_year': '2026-2027',
                'is_active': True,
                'slabs': [
                    {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                    {'min_income': '300000', 'max_income': '700000', 'rate_percent': '10'},
                    {'min_income': '700000', 'max_income': None, 'rate_percent': '20'},
                ],
            },
            format='json',
        )

        assert response.status_code == 201

        summary_response = org_admin_client.get('/api/org/payroll/summary/')
        assert summary_response.status_code == 200
        assert summary_response.data['tax_slab_sets']
        assert summary_response.data['tax_slab_sets'][0]['source_set_id'] == response.data['id']

    def test_employee_can_list_own_payslips(self, payroll_setup):
        organisation = payroll_setup['organisation']
        employee = payroll_setup['employee']
        employee_client = payroll_setup['employee_client']
        org_admin_user = payroll_setup['org_admin_user']

        create_tax_slab_set(
            fiscal_year='2026-2027',
            name='FY 2026 Master',
            country_code='IN',
            slabs=[
                {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
                {'min_income': '300000', 'max_income': '700000', 'rate_percent': '10'},
                {'min_income': '700000', 'max_income': None, 'rate_percent': '20'},
            ],
            actor=org_admin_user,
        )
        ensure_org_payroll_setup(organisation, actor=org_admin_user)
        template = create_compensation_template(
            organisation,
            name='Standard Monthly',
            description='Core salaried template',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '40000',
                    'is_taxable': True,
                }
            ],
            actor=org_admin_user,
        )
        assignment = assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=org_admin_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        calculate_pay_run(pay_run, actor=org_admin_user)
        finalize_pay_run(pay_run, actor=org_admin_user, skip_approval=True)

        response = employee_client.get('/api/me/payroll/payslips/')

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['employee_id'] == str(employee.id)
        assert response.data[0]['pay_run_id'] == str(pay_run.id)
