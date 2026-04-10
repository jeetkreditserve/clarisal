import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeProfile, EmployeeStatus, GenderChoice, GovernmentIdType
from apps.employees.services import upsert_government_id
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.payroll.models import PayrollRunItemStatus, Payslip
from apps.payroll.services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_full_and_final_settlement,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
)

from .test_service_setup import _attach_registered_and_billing_addresses


def _finalize_basic_pay_run(*, organisation, org_admin_user, employee, monthly_amount, period_year=2026, period_month=4):
    create_tax_slab_set(
        fiscal_year='2026-2027',
        name=f'FY {period_year} Master',
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
        name=f'Payroll {period_year}-{period_month:02d}',
        description='Filing endpoint setup',
        lines=[
            {
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': 'EARNING',
                'monthly_amount': str(monthly_amount),
                'is_taxable': True,
            }
        ],
        actor=org_admin_user,
    )
    assign_employee_compensation(
        employee,
        template,
        effective_from=date(period_year, period_month, 1),
        actor=org_admin_user,
        auto_approve=True,
    )
    pay_run = create_payroll_run(
        organisation,
        period_year=period_year,
        period_month=period_month,
        actor=org_admin_user,
        requester_user=org_admin_user,
    )
    calculate_pay_run(pay_run, actor=org_admin_user)
    finalize_pay_run(pay_run, actor=org_admin_user, skip_approval=True)
    return pay_run


@pytest.fixture
def payroll_setup(db):
    organisation = Organisation.objects.create(
        name='Acme Payroll',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    _attach_registered_and_billing_addresses(organisation)
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
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
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
        call_command('seed_statutory_masters')

        response = ct_client.post(
            '/api/v1/ct/payroll/tax-slab-sets/',
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

        summary_response = org_admin_client.get('/api/v1/org/payroll/summary/')
        assert summary_response.status_code == 200
        assert summary_response.data['tax_slab_sets']
        # Org summary returns CT masters directly; verify the newly created master appears.
        slab_set_ids = [ss['id'] for ss in summary_response.data['tax_slab_sets']]
        assert response.data['id'] in slab_set_ids
        assert summary_response.data['professional_tax_rules']
        assert summary_response.data['labour_welfare_fund_rules']

    def test_ct_and_org_can_read_seeded_statutory_masters(self, payroll_setup):
        call_command('seed_statutory_masters')
        ct_client = payroll_setup['ct_client']
        org_admin_client = payroll_setup['org_admin_client']

        ct_response = ct_client.get('/api/v1/ct/payroll/statutory-masters/?state_code=KA')
        org_response = org_admin_client.get('/api/v1/org/payroll/statutory-masters/?state_code=MH')

        assert ct_response.status_code == 200
        assert org_response.status_code == 200
        assert [rule['state_code'] for rule in ct_response.data['professional_tax_rules']] == ['KA']
        assert [rule['state_code'] for rule in org_response.data['labour_welfare_fund_rules']] == ['MH']

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
        assign_employee_compensation(
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

        response = employee_client.get('/api/v1/me/payroll/payslips/')

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['employee_id'] == str(employee.id)
        assert response.data[0]['pay_run_id'] == str(pay_run.id)

    def test_control_tower_cannot_access_org_payroll_summary_or_employee_payslips(self, payroll_setup):
        ct_client = payroll_setup['ct_client']
        employee = payroll_setup['employee']

        summary_response = ct_client.get('/api/v1/org/payroll/summary/')
        payslip_response = ct_client.get('/api/v1/me/payroll/payslips/')
        payslip_detail_response = ct_client.get(f'/api/v1/me/payroll/payslips/{employee.id}/')

        assert summary_response.status_code == 403
        assert payslip_response.status_code == 403
        assert payslip_detail_response.status_code == 403

    def test_employee_can_download_payslip_rendered_text(self, payroll_setup):
        employee_client = payroll_setup['employee_client']
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        employee = payroll_setup['employee']

        create_tax_slab_set(
            country_code='IN',
            fiscal_year='2026-27',
            name='FY 2026-27',
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
            name='Downloadable Template',
            description='Download flow',
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
        assign_employee_compensation(
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
        payslip = Payslip.objects.get(employee=employee, pay_run=pay_run)

        response = employee_client.get(f'/api/v1/me/payroll/payslips/{payslip.id}/download/')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert payslip.slip_number.replace('/', '-') in response['Content-Disposition']
        assert response.content[:4] == b'%PDF'

    def test_employee_can_download_payslip_rendered_text_with_labour_welfare_fund_lines(self, payroll_setup):
        employee_client = payroll_setup['employee_client']
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        employee = payroll_setup['employee']

        create_tax_slab_set(
            country_code='IN',
            fiscal_year='2026-27',
            name='FY 2026-27',
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
            name='LWF Template',
            description='Rendered LWF flow',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '4000',
                    'is_taxable': True,
                }
            ],
            actor=org_admin_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 6, 1),
            actor=org_admin_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=6,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        calculate_pay_run(pay_run, actor=org_admin_user)
        finalize_pay_run(pay_run, actor=org_admin_user, skip_approval=True)
        payslip = Payslip.objects.get(employee=employee, pay_run=pay_run)

        response = employee_client.get(f'/api/v1/me/payroll/payslips/{payslip.id}/download/')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content[:4] == b'%PDF'

    def test_org_admin_can_view_full_and_final_settlement_with_automated_gratuity(self, payroll_setup):
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']
        employee.date_of_joining = date(2021, 1, 1)
        employee.save(update_fields=['date_of_joining'])

        template = create_compensation_template(
            organisation,
            name='FNF View Template',
            description='FNF view flow',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '26000',
                    'is_taxable': True,
                }
            ],
            actor=org_admin_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 1, 1),
            actor=org_admin_user,
            auto_approve=True,
        )
        settlement = create_full_and_final_settlement(
            employee=employee,
            last_working_day=date(2026, 1, 31),
            initiated_by=org_admin_user,
        )

        response = org_admin_client.get(f'/api/v1/org/payroll/full-and-final-settlements/{settlement.id}/')

        assert response.status_code == 200
        assert response.data['gratuity'] == '75000.00'
        assert response.data['gross_payable'] == '101000.00'
        assert response.data['net_payable'] == '101000.00'

    def test_employee_can_download_payslip_with_pt_pf_esi_and_lwf_combined(self, payroll_setup):
        employee_client = payroll_setup['employee_client']
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        employee = payroll_setup['employee']

        EmployeeProfile.objects.update_or_create(
            employee=employee,
            defaults={'gender': GenderChoice.MALE},
        )
        create_tax_slab_set(
            country_code='IN',
            fiscal_year='2026-27',
            name='FY 2026-27',
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
            name='Combined Statutory Template',
            description='PT PF ESI LWF flow',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '20000',
                    'is_taxable': True,
                }
            ],
            actor=org_admin_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 6, 1),
            actor=org_admin_user,
            auto_approve=True,
        )
        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=6,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        calculate_pay_run(pay_run, actor=org_admin_user)
        finalize_pay_run(pay_run, actor=org_admin_user, skip_approval=True)
        payslip = Payslip.objects.get(employee=employee, pay_run=pay_run)

        response = employee_client.get(f'/api/v1/me/payroll/payslips/{payslip.id}/download/')
        item = pay_run.items.get(employee=employee)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content[:4] == b'%PDF'
        assert payslip.slip_number.replace('/', '-') in response['Content-Disposition']
        # Verify snapshot fields used in PDF
        assert Decimal(item.snapshot['pt_monthly']) == Decimal('200.00')
        assert Decimal(item.snapshot['auto_pf']) == Decimal('1800.00')
        assert Decimal(item.snapshot['esi_employee']) == Decimal('150.00')
        assert Decimal(item.snapshot['lwf_employee']) == Decimal('12.00')
        assert Decimal(item.snapshot['pf_employer']) == Decimal('1800.00')
        assert Decimal(item.snapshot['esi_employer']) == Decimal('650.00')
        assert Decimal(item.snapshot['lwf_employer']) == Decimal('36.00')

    def test_employee_can_create_and_list_investment_declarations(self, payroll_setup):
        employee_client = payroll_setup['employee_client']

        create_response = employee_client.post(
            '/api/v1/me/payroll/investment-declarations/',
            {
                'fiscal_year': '2024-25',
                'section': '80C',
                'description': 'PPF',
                'declared_amount': '150000.00',
            },
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['section'] == '80C'

        list_response = employee_client.get('/api/v1/me/payroll/investment-declarations/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['description'] == 'PPF'

    def test_employee_can_update_and_delete_own_investment_declaration(self, payroll_setup):
        employee_client = payroll_setup['employee_client']

        create_response = employee_client.post(
            '/api/v1/me/payroll/investment-declarations/',
            {
                'fiscal_year': '2026-2027',
                'section': '80C',
                'description': 'EPF contribution',
                'declared_amount': '100000.00',
            },
            format='json',
        )

        declaration_id = create_response.data['id']

        update_response = employee_client.patch(
            f'/api/v1/me/payroll/investment-declarations/{declaration_id}/',
            {
                'description': 'EPF + PPF contribution',
                'declared_amount': '120000.00',
            },
            format='json',
        )

        assert update_response.status_code == 200
        assert update_response.data['description'] == 'EPF + PPF contribution'
        assert update_response.data['declared_amount'] == '120000.00'

        detail_response = employee_client.get(f'/api/v1/me/payroll/investment-declarations/{declaration_id}/')

        assert detail_response.status_code == 200
        assert detail_response.data['id'] == declaration_id

        delete_response = employee_client.delete(f'/api/v1/me/payroll/investment-declarations/{declaration_id}/')

        assert delete_response.status_code == 204
        list_response = employee_client.get('/api/v1/me/payroll/investment-declarations/')
        assert list_response.status_code == 200
        assert list_response.data == []

    def test_employee_investment_declaration_validates_section_cap(self, payroll_setup):
        employee_client = payroll_setup['employee_client']

        first_response = employee_client.post(
            '/api/v1/me/payroll/investment-declarations/',
            {
                'fiscal_year': '2026-2027',
                'section': '80C',
                'description': 'PPF',
                'declared_amount': '100000.00',
            },
            format='json',
        )
        assert first_response.status_code == 201

        second_response = employee_client.post(
            '/api/v1/me/payroll/investment-declarations/',
            {
                'fiscal_year': '2026-2027',
                'section': '80C',
                'description': 'ELSS',
                'declared_amount': '60000.00',
            },
            format='json',
        )

        assert second_response.status_code == 400
        assert 'declared_amount' in second_response.data

    def test_org_admin_can_filter_and_verify_investment_declarations(self, payroll_setup):
        employee_client = payroll_setup['employee_client']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        create_response = employee_client.post(
            '/api/v1/me/payroll/investment-declarations/',
            {
                'fiscal_year': '2026-2027',
                'section': '80D',
                'description': 'Mediclaim',
                'declared_amount': '25000.00',
            },
            format='json',
        )
        declaration_id = create_response.data['id']

        list_response = org_admin_client.get(
            '/api/v1/org/payroll/investment-declarations/',
            {
                'employee_id': str(employee.id),
                'fiscal_year': '2026-2027',
                'section': '80D',
                'is_verified': 'false',
            },
        )

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['id'] == declaration_id

        verify_response = org_admin_client.patch(
            f'/api/v1/org/payroll/investment-declarations/{declaration_id}/',
            {'is_verified': True},
            format='json',
        )

        assert verify_response.status_code == 200
        assert verify_response.data['is_verified'] is True

        verified_list_response = org_admin_client.get(
            '/api/v1/org/payroll/investment-declarations/',
            {'is_verified': 'true'},
        )

        assert verified_list_response.status_code == 200
        assert [item['id'] for item in verified_list_response.data] == [declaration_id]

    def test_employee_form12bb_canonical_alias_returns_pdf(self, payroll_setup):
        employee_client = payroll_setup['employee_client']

        create_response = employee_client.post(
            '/api/v1/me/payroll/investment-declarations/',
            {
                'fiscal_year': '2026-2027',
                'section': '80C',
                'description': 'PPF',
                'declared_amount': '150000.00',
            },
            format='json',
        )
        assert create_response.status_code == 201

        response = employee_client.get('/api/v1/me/payroll/form-12bb/2026-2027/')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content[:4] == b'%PDF'

    def test_employee_can_download_payslips_for_fiscal_year_as_zip(self, payroll_setup):
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
            name='Annual Payroll Template',
            description='Payslip ZIP test',
            lines=[
                {
                    'component_code': 'BASIC',
                    'name': 'Basic Pay',
                    'component_type': 'EARNING',
                    'monthly_amount': '45000',
                    'is_taxable': True,
                }
            ],
            actor=org_admin_user,
        )
        assign_employee_compensation(
            employee,
            template,
            effective_from=date(2026, 4, 1),
            actor=org_admin_user,
            auto_approve=True,
        )

        april_2026_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        calculate_pay_run(april_2026_run, actor=org_admin_user)
        finalize_pay_run(april_2026_run, actor=org_admin_user, skip_approval=True)

        april_2027_run = create_payroll_run(
            organisation,
            period_year=2027,
            period_month=4,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        calculate_pay_run(april_2027_run, actor=org_admin_user)
        finalize_pay_run(april_2027_run, actor=org_admin_user, skip_approval=True)

        response = employee_client.get('/api/v1/me/payroll/payslips/fiscal-year/2026-2027/download/')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/zip'
        assert 'payslips-2026-2027.zip' in response['Content-Disposition']

        archive = zipfile.ZipFile(io.BytesIO(response.content))
        names = archive.namelist()
        assert len(names) == 1
        assert names[0].endswith('.pdf')
        assert archive.read(names[0])[:4] == b'%PDF'

    def test_org_admin_can_create_old_regime_compensation_assignment(self, payroll_setup):
        organisation = payroll_setup['organisation']
        org_admin_client = payroll_setup['org_admin_client']
        org_admin_user = payroll_setup['org_admin_user']
        employee = payroll_setup['employee']

        template = create_compensation_template(
            organisation,
            name='Assignment API Template',
            description='Assignment API test',
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

        response = org_admin_client.post(
            '/api/v1/org/payroll/compensations/',
            {
                'employee_id': str(employee.id),
                'template_id': str(template.id),
                'effective_from': '2026-04-01',
                'tax_regime': 'OLD',
                'auto_approve': True,
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.data['tax_regime'] == 'OLD'

    def test_org_admin_can_view_full_and_final_settlement(self, payroll_setup):
        employee = payroll_setup['employee']
        org_admin_client = payroll_setup['org_admin_client']

        end_response = org_admin_client.post(
            f'/api/v1/org/employees/{employee.id}/end-employment/',
            {
                'status': EmployeeStatus.RESIGNED,
                'date_of_exit': '2026-04-30',
                'exit_reason': 'Role closure',
            },
            format='json',
        )

        assert end_response.status_code == 200

        list_response = org_admin_client.get('/api/v1/org/payroll/full-and-final-settlements/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['employee_id'] == str(employee.id)
        assert list_response.data[0]['status'] == 'DRAFT'

        detail_response = org_admin_client.get(f"/api/v1/org/payroll/full-and-final-settlements/{list_response.data[0]['id']}/")

        assert detail_response.status_code == 200
        assert detail_response.data['last_working_day'] == '2026-04-30'

    def test_create_arrear(self, payroll_setup):
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        response = org_admin_client.post(
            '/api/v1/org/payroll/arrears/',
            {
                'employee_id': str(employee.id),
                'for_period_year': 2024,
                'for_period_month': 3,
                'reason': 'Missed allowance Q4',
                'amount': '5000.00',
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.json()['amount'] == '5000.00'
        assert response.json()['is_included_in_payslip'] is False

    def test_list_arrears(self, payroll_setup):
        org_admin_client = payroll_setup['org_admin_client']

        response = org_admin_client.get('/api/v1/org/payroll/arrears/')

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_form16_export_returns_structured_json(self, payroll_setup):
        organisation = payroll_setup['organisation']
        org_admin_client = payroll_setup['org_admin_client']
        org_admin_user = payroll_setup['org_admin_user']
        employee = payroll_setup['employee']

        organisation.pan_number = 'ABCDE1234F'
        organisation.save(update_fields=['pan_number', 'modified_at'])

        template = create_compensation_template(
            organisation,
            name='Form 16 Template',
            description='Form 16 export test',
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
        assign_employee_compensation(
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

        response = org_admin_client.get(f'/api/v1/org/payroll/runs/{pay_run.id}/form16/')

        assert response.status_code == 200
        assert response.data['pay_run_id'] == str(pay_run.id)
        assert response.data['organisation'] == organisation.name
        assert len(response.data['employees']) == 1
        first_employee = response.data['employees'][0]
        assert 'part_a' in first_employee
        assert 'part_b' in first_employee
        assert first_employee['part_a']['employer_pan'] == 'ABCDE1234F'
        assert 'gross_salary' in first_employee['part_b']
        assert 'rebate_87a' in first_employee['part_b']

    def test_org_admin_can_generate_and_download_statutory_filing_batch(self, payroll_setup):
        organisation = payroll_setup['organisation']
        organisation.tan_number = 'BLRN12345A'
        organisation.pan_number = 'AACCN1234F'
        organisation.save(update_fields=['tan_number', 'pan_number', 'modified_at'])

        employee = payroll_setup['employee']
        EmployeeProfile.objects.create(
            employee=employee,
            gender=GenderChoice.MALE,
            uan_number='100200300400',
            esic_ip_number='1234567890',
        )
        upsert_government_id(employee, GovernmentIdType.PAN, 'ABCDE1234F', actor=payroll_setup['org_admin_user'], name_on_id='Employee User')
        _finalize_basic_pay_run(
            organisation=organisation,
            org_admin_user=payroll_setup['org_admin_user'],
            employee=employee,
            monthly_amount='20000',
        )

        generate_response = payroll_setup['org_admin_client'].post(
            '/api/v1/org/payroll/filings/',
            {
                'filing_type': 'PF_ECR',
                'period_year': 2026,
                'period_month': 4,
            },
            format='json',
        )

        assert generate_response.status_code == 201
        assert generate_response.data['status'] == 'GENERATED'
        assert generate_response.data['file_name'].endswith('.csv')

        batch_id = generate_response.data['id']
        download_response = payroll_setup['org_admin_client'].get(f'/api/v1/org/payroll/filings/{batch_id}/download/')

        assert download_response.status_code == 200
        assert download_response['Content-Disposition'].endswith('.csv"')
        assert '100200300400' in download_response.content.decode('utf-8')

    def test_blocked_filing_batch_surfaces_validation_errors(self, payroll_setup):
        organisation = payroll_setup['organisation']
        employee = payroll_setup['employee']
        EmployeeProfile.objects.create(employee=employee, gender=GenderChoice.MALE)
        _finalize_basic_pay_run(
            organisation=organisation,
            org_admin_user=payroll_setup['org_admin_user'],
            employee=employee,
            monthly_amount='20000',
        )

        response = payroll_setup['org_admin_client'].post(
            '/api/v1/org/payroll/filings/',
            {
                'filing_type': 'PF_ECR',
                'period_year': 2026,
                'period_month': 4,
            },
            format='json',
        )

        assert response.status_code == 200
        assert response.data['status'] == 'BLOCKED'
        assert 'missing UAN number' in response.data['validation_errors'][0]

    def test_filing_batch_can_be_regenerated_and_cancelled(self, payroll_setup):
        organisation = payroll_setup['organisation']
        organisation.tan_number = 'BLRN12345A'
        organisation.pan_number = 'AACCN1234F'
        organisation.save(update_fields=['tan_number', 'pan_number', 'modified_at'])

        employee = payroll_setup['employee']
        EmployeeProfile.objects.create(
            employee=employee,
            gender=GenderChoice.MALE,
            uan_number='100200300400',
            esic_ip_number='1234567890',
        )
        upsert_government_id(employee, GovernmentIdType.PAN, 'ABCDE1234F', actor=payroll_setup['org_admin_user'], name_on_id='Employee User')
        _finalize_basic_pay_run(
            organisation=organisation,
            org_admin_user=payroll_setup['org_admin_user'],
            employee=employee,
            monthly_amount='20000',
        )

        create_response = payroll_setup['org_admin_client'].post(
            '/api/v1/org/payroll/filings/',
            {
                'filing_type': 'FORM16',
                'fiscal_year': '2026-2027',
                'artifact_format': 'XML',
            },
            format='json',
        )
        assert create_response.status_code == 201

        batch_id = create_response.data['id']
        regenerate_response = payroll_setup['org_admin_client'].post(f'/api/v1/org/payroll/filings/{batch_id}/regenerate/')

        assert regenerate_response.status_code == 201
        assert regenerate_response.data['status'] == 'GENERATED'

        cancel_response = payroll_setup['org_admin_client'].post(f'/api/v1/org/payroll/filings/{batch_id}/cancel/')

        assert cancel_response.status_code == 200
        assert cancel_response.data['status'] == 'CANCELLED'

    def test_org_admin_can_create_and_update_tds_challan(self, payroll_setup):
        create_response = payroll_setup['org_admin_client'].post(
            '/api/v1/org/payroll/tds-challans/',
            {
                'fiscal_year': '2026-2027',
                'period_year': 2026,
                'period_month': 4,
                'bsr_code': '0510032',
                'challan_serial_number': '00004',
                'deposit_date': '2026-04-07',
                'tax_deposited': '3500.00',
                'statement_receipt_number': '123456789012345',
            },
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['quarter'] == 'Q1'
        assert create_response.data['tax_deposited'] == '3500.00'

        challan_id = create_response.data['id']
        update_response = payroll_setup['org_admin_client'].patch(
            f'/api/v1/org/payroll/tds-challans/{challan_id}/',
            {
                'tax_deposited': '3600.00',
                'notes': 'Adjusted for interest reversal',
            },
            format='json',
        )

        assert update_response.status_code == 200
        assert update_response.data['tax_deposited'] == '3600.00'
        assert update_response.data['notes'] == 'Adjusted for interest reversal'

    # ------------------------------------------------------------------
    # P26 T5 — PayrollRun summary returns aggregated totals, no inline items
    # ------------------------------------------------------------------

    def test_pay_run_list_has_aggregated_totals_and_no_inline_items(self, payroll_setup):
        """PayrollRun list must expose aggregate fields and NOT include inline items."""
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        pay_run = _finalize_basic_pay_run(
            organisation=organisation,
            org_admin_user=org_admin_user,
            employee=employee,
            monthly_amount='60000',
        )

        response = org_admin_client.get('/api/v1/org/payroll/runs/')

        assert response.status_code == 200
        assert len(response.data) >= 1

        run_data = next(r for r in response.data if r['id'] == str(pay_run.id))

        # Must NOT contain inline items
        assert 'items' not in run_data

        # Must contain aggregate fields
        assert 'total_gross' in run_data
        assert 'total_net' in run_data
        assert 'total_deductions' in run_data
        assert 'employee_count' in run_data
        assert 'exception_count' in run_data

        # Values must match the single run item
        item = pay_run.items.get(employee=employee)
        from decimal import Decimal
        assert Decimal(str(run_data['total_gross'])) == item.gross_pay
        assert Decimal(str(run_data['total_net'])) == item.net_pay
        assert int(run_data['employee_count']) == 1
        assert int(run_data['exception_count']) == 0

    def test_pay_run_detail_has_aggregated_totals_and_no_inline_items(self, payroll_setup):
        """PayrollRun detail must expose aggregate fields and NOT include inline items."""
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        pay_run = _finalize_basic_pay_run(
            organisation=organisation,
            org_admin_user=org_admin_user,
            employee=employee,
            monthly_amount='50000',
        )

        response = org_admin_client.get(f'/api/v1/org/payroll/runs/{pay_run.id}/')

        assert response.status_code == 200
        assert 'items' not in response.data
        assert 'total_gross' in response.data
        assert 'total_net' in response.data
        assert 'employee_count' in response.data
        assert int(response.data['employee_count']) == 1

    def test_pay_run_aggregates_count_exception_items_by_status(self, payroll_setup):
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        pay_run.items.create(
            employee=employee,
            status=PayrollRunItemStatus.READY,
            gross_pay='60000.00',
            total_deductions='4200.00',
            net_pay='55800.00',
        )

        second_user = User.objects.create_user(
            email='employee-two@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=organisation,
            is_active=True,
        )
        second_employee = Employee.objects.create(
            organisation=organisation,
            user=second_user,
            employee_code='EMP101',
            designation='Analyst',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 4, 1),
        )
        pay_run.items.create(
            employee=second_employee,
            status=PayrollRunItemStatus.EXCEPTION,
            message='Missing approved compensation assignment.',
        )

        response = org_admin_client.get('/api/v1/org/payroll/runs/')

        assert response.status_code == 200
        run_data = next(r for r in response.data if r['id'] == str(pay_run.id))
        assert int(run_data['employee_count']) == 2
        assert int(run_data['exception_count']) == 1
        assert Decimal(str(run_data['total_gross'])) == Decimal('60000.00')
        assert Decimal(str(run_data['total_deductions'])) == Decimal('4200.00')

    def test_pay_run_items_endpoint_returns_paginated_rows_and_filters_exceptions(self, payroll_setup):
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        pay_run = create_payroll_run(
            organisation,
            period_year=2026,
            period_month=4,
            actor=org_admin_user,
            requester_user=org_admin_user,
        )
        ready_item = pay_run.items.create(
            employee=employee,
            status=PayrollRunItemStatus.READY,
            gross_pay='42000.00',
            total_deductions='2200.00',
            net_pay='39800.00',
        )

        second_user = User.objects.create_user(
            email='employee-three@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=organisation,
            is_active=True,
        )
        second_employee = Employee.objects.create(
            organisation=organisation,
            user=second_user,
            employee_code='EMP102',
            designation='Support',
            status=EmployeeStatus.ACTIVE,
            date_of_joining=date(2026, 4, 1),
        )
        exception_item = pay_run.items.create(
            employee=second_employee,
            status=PayrollRunItemStatus.EXCEPTION,
            message='PAN is missing from payroll profile.',
        )

        response = org_admin_client.get(f'/api/v1/org/payroll/runs/{pay_run.id}/items/?has_exception=true')

        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['next'] is None
        assert response.data['previous'] is None
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == str(exception_item.id)
        assert response.data['results'][0]['has_exception'] is True

        employee_response = org_admin_client.get(f'/api/v1/org/payroll/runs/{pay_run.id}/items/?employee={employee.id}')

        assert employee_response.status_code == 200
        assert employee_response.data['count'] == 1
        assert employee_response.data['results'][0]['id'] == str(ready_item.id)
        assert employee_response.data['results'][0]['has_exception'] is False

    # ------------------------------------------------------------------
    # P21 T6 — /api/health/ endpoint
    # ------------------------------------------------------------------

    def test_org_admin_can_download_payslip_as_pdf(self, payroll_setup):
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        org_admin_client = payroll_setup['org_admin_client']
        employee = payroll_setup['employee']

        create_tax_slab_set(
            country_code='IN',
            fiscal_year='2026-27',
            name='FY 2026-27',
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
            name='Org Payslip Test Template',
            description='Org admin payslip PDF test',
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
        assign_employee_compensation(
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
        payslip = Payslip.objects.get(employee=employee, pay_run=pay_run)

        response = org_admin_client.get(f'/api/v1/org/payroll/payslips/{payslip.id}/download/')

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content[:4] == b'%PDF'
        assert payslip.slip_number.replace('/', '-') in response['Content-Disposition']

    def test_org_admin_cannot_download_another_org_payslip(self, payroll_setup):
        """Cross-org payslip download should be forbidden — returns 404."""
        organisation = payroll_setup['organisation']
        org_admin_user = payroll_setup['org_admin_user']
        employee = payroll_setup['employee']

        create_tax_slab_set(
            country_code='IN', fiscal_year='2026-27', name='FY 2026-27',
            slabs=[{'min_income': '0', 'max_income': '300000', 'rate_percent': '0'}],
            actor=org_admin_user,
        )
        ensure_org_payroll_setup(organisation, actor=org_admin_user)
        template = create_compensation_template(
            organisation, name='Cross-Org Test', description='Cross-org test',
            lines=[{'component_code': 'BASIC', 'name': 'Basic Pay', 'component_type': 'EARNING', 'monthly_amount': '30000', 'is_taxable': True}],
            actor=org_admin_user,
        )
        assign_employee_compensation(employee, template, effective_from=date(2026, 4, 1), actor=org_admin_user, auto_approve=True)
        pay_run = create_payroll_run(organisation, period_year=2026, period_month=4, actor=org_admin_user, requester_user=org_admin_user)
        calculate_pay_run(pay_run, actor=org_admin_user)
        finalize_pay_run(pay_run, actor=org_admin_user, skip_approval=True)
        payslip = Payslip.objects.get(employee=employee, pay_run=pay_run)

        # Try to access with employee (non-admin) — should be forbidden
        employee_client = payroll_setup['employee_client']
        response = employee_client.get(f'/api/v1/org/payroll/payslips/{payslip.id}/download/')
        assert response.status_code == 403


@pytest.mark.django_db
def test_health_check_returns_ok(client):
    response = client.get('/api/health/')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
