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
from apps.payroll.models import Payslip
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
        # Org summary returns CT masters directly; verify the newly created master appears.
        slab_set_ids = [ss['id'] for ss in summary_response.data['tax_slab_sets']]
        assert response.data['id'] in slab_set_ids
        assert summary_response.data['professional_tax_rules']
        assert summary_response.data['labour_welfare_fund_rules']

    def test_ct_and_org_can_read_seeded_statutory_masters(self, payroll_setup):
        call_command('seed_statutory_masters')
        ct_client = payroll_setup['ct_client']
        org_admin_client = payroll_setup['org_admin_client']

        ct_response = ct_client.get('/api/ct/payroll/statutory-masters/?state_code=KA')
        org_response = org_admin_client.get('/api/org/payroll/statutory-masters/?state_code=MH')

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

        response = employee_client.get('/api/me/payroll/payslips/')

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['employee_id'] == str(employee.id)
        assert response.data[0]['pay_run_id'] == str(pay_run.id)

    def test_control_tower_cannot_access_org_payroll_summary_or_employee_payslips(self, payroll_setup):
        ct_client = payroll_setup['ct_client']
        employee = payroll_setup['employee']

        summary_response = ct_client.get('/api/org/payroll/summary/')
        payslip_response = ct_client.get('/api/me/payroll/payslips/')
        payslip_detail_response = ct_client.get(f'/api/me/payroll/payslips/{employee.id}/')

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

        response = employee_client.get(f'/api/me/payroll/payslips/{payslip.id}/download/')

        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/plain')
        assert payslip.slip_number.replace('/', '-') in response['Content-Disposition']
        assert payslip.rendered_text in response.content.decode('utf-8')

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

        response = employee_client.get(f'/api/me/payroll/payslips/{payslip.id}/download/')
        rendered = response.content.decode('utf-8')

        assert response.status_code == 200
        assert 'Labour Welfare Fund - Employee *' in rendered
        assert 'Labour Welfare Fund - Employer *' in rendered

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

        response = org_admin_client.get(f'/api/org/payroll/full-and-final-settlements/{settlement.id}/')

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

        response = employee_client.get(f'/api/me/payroll/payslips/{payslip.id}/download/')
        rendered = response.content.decode('utf-8')
        item = pay_run.items.get(employee=employee)

        assert response.status_code == 200
        assert Decimal(item.snapshot['pt_monthly']) == Decimal('200.00')
        assert Decimal(item.snapshot['auto_pf']) == Decimal('1800.00')
        assert Decimal(item.snapshot['esi_employee']) == Decimal('150.00')
        assert Decimal(item.snapshot['lwf_employee']) == Decimal('12.00')
        assert Decimal(item.snapshot['pf_employer']) == Decimal('1800.00')
        assert Decimal(item.snapshot['esi_employer']) == Decimal('650.00')
        assert Decimal(item.snapshot['lwf_employer']) == Decimal('36.00')
        assert 'Professional Tax *' in rendered
        assert 'Employee PF/VPF (12.00% of PF Wages) *' in rendered
        assert 'ESI - Employee (0.75%) *' in rendered
        assert 'Labour Welfare Fund - Employee *' in rendered

    def test_employee_can_create_and_list_investment_declarations(self, payroll_setup):
        employee_client = payroll_setup['employee_client']

        create_response = employee_client.post(
            '/api/me/payroll/investment-declarations/',
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

        list_response = employee_client.get('/api/me/payroll/investment-declarations/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['description'] == 'PPF'

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
            '/api/org/payroll/compensations/',
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
            f'/api/org/employees/{employee.id}/end-employment/',
            {
                'status': EmployeeStatus.RESIGNED,
                'date_of_exit': '2026-04-30',
                'exit_reason': 'Role closure',
            },
            format='json',
        )

        assert end_response.status_code == 200

        list_response = org_admin_client.get('/api/org/payroll/full-and-final-settlements/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['employee_id'] == str(employee.id)
        assert list_response.data[0]['status'] == 'DRAFT'

        detail_response = org_admin_client.get(f"/api/org/payroll/full-and-final-settlements/{list_response.data[0]['id']}/")

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

        response = org_admin_client.get(f'/api/org/payroll/runs/{pay_run.id}/form16/')

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
            '/api/org/payroll/filings/',
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
        download_response = payroll_setup['org_admin_client'].get(f'/api/org/payroll/filings/{batch_id}/download/')

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
            '/api/org/payroll/filings/',
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
            '/api/org/payroll/filings/',
            {
                'filing_type': 'FORM16',
                'fiscal_year': '2026-2027',
                'artifact_format': 'XML',
            },
            format='json',
        )
        assert create_response.status_code == 201

        batch_id = create_response.data['id']
        regenerate_response = payroll_setup['org_admin_client'].post(f'/api/org/payroll/filings/{batch_id}/regenerate/')

        assert regenerate_response.status_code == 201
        assert regenerate_response.data['status'] == 'GENERATED'

        cancel_response = payroll_setup['org_admin_client'].post(f'/api/org/payroll/filings/{batch_id}/cancel/')

        assert cancel_response.status_code == 200
        assert cancel_response.data['status'] == 'CANCELLED'

    def test_org_admin_can_create_and_update_tds_challan(self, payroll_setup):
        create_response = payroll_setup['org_admin_client'].post(
            '/api/org/payroll/tds-challans/',
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
            f'/api/org/payroll/tds-challans/{challan_id}/',
            {
                'tax_deposited': '3600.00',
                'notes': 'Adjusted for interest reversal',
            },
            format='json',
        )

        assert update_response.status_code == 200
        assert update_response.data['tax_deposited'] == '3600.00'
        assert update_response.data['notes'] == 'Adjusted for interest reversal'
