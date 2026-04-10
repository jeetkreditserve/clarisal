from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.approvals.models import ApprovalRequestKind
from apps.organisations.models import OrganisationMembership, OrganisationMembershipStatus
from apps.payroll.tests.test_service_setup import (
    _create_active_organisation,
    _create_employee,
    _create_user,
    _create_workflow,
)

from apps.expenses.models import ExpenseCategory, ExpensePolicy
from apps.expenses.services import create_expense_claim


@pytest.fixture
def expense_api_setup(db):
    organisation = _create_active_organisation('Expense API Org')
    org_admin_user = _create_user('expense-admin@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    OrganisationMembership.objects.create(
        user=org_admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    employee_user, employee = _create_employee(
        organisation,
        'expense-employee@test.com',
        employee_code='EXP001',
    )
    approver_user, approver_employee = _create_employee(
        organisation,
        'expense-approver@test.com',
        employee_code='EXP002',
    )
    _create_workflow(organisation, approver_employee, ApprovalRequestKind.EXPENSE_CLAIM)

    employee_client = APIClient()
    employee_client.force_authenticate(user=employee_user)
    employee_session = employee_client.session
    employee_session['active_workspace_kind'] = 'EMPLOYEE'
    employee_session['active_employee_org_id'] = str(organisation.id)
    employee_session.save()

    org_admin_client = APIClient()
    org_admin_client.force_authenticate(user=org_admin_user)
    org_session = org_admin_client.session
    org_session['active_workspace_kind'] = 'ADMIN'
    org_session['active_admin_org_id'] = str(organisation.id)
    org_session.save()

    return {
        'organisation': organisation,
        'org_admin_user': org_admin_user,
        'employee_user': employee_user,
        'employee': employee,
        'employee_client': employee_client,
        'org_admin_client': org_admin_client,
        'approver_user': approver_user,
    }


@pytest.mark.django_db
def test_employee_can_edit_claim_upload_receipt_and_submit(expense_api_setup, monkeypatch):
    employee_client = expense_api_setup['employee_client']
    employee = expense_api_setup['employee']
    monkeypatch.setattr('apps.expenses.services.upload_file', lambda file_obj, key, content_type: None)
    monkeypatch.setattr('apps.expenses.services.generate_presigned_url', lambda key, expiry=900: f'https://files.test/{key}')

    policy = ExpensePolicy.objects.create(
        organisation=employee.organisation,
        name='Default Travel Policy',
        currency='INR',
    )
    category = ExpenseCategory.objects.create(
        policy=policy,
        code='TRAVEL',
        name='Travel',
        per_claim_limit='5000.00',
        requires_receipt=True,
    )

    create_response = employee_client.post(
        '/api/v1/me/expenses/claims/',
        {
            'title': 'Client visit',
            'claim_date': '2026-04-09',
            'currency': 'INR',
            'policy': str(policy.id),
            'submit': False,
            'lines': [
                {
                    'category_id': str(category.id),
                    'expense_date': '2026-04-08',
                    'merchant': 'Metro Cabs',
                    'description': 'Airport ride',
                    'amount': '1250.00',
                    'currency': 'INR',
                }
            ],
        },
        format='json',
    )

    assert create_response.status_code == 201
    claim_id = create_response.data['id']
    update_response = employee_client.patch(
        f'/api/v1/me/expenses/claims/{claim_id}/',
        {
            'title': 'Client visit reimbursement',
            'claim_date': '2026-04-09',
            'currency': 'INR',
            'policy': str(policy.id),
            'submit': False,
            'lines': [
                {
                    'category_id': str(category.id),
                    'expense_date': '2026-04-08',
                    'merchant': 'Metro Cabs',
                    'description': 'Airport ride to client office',
                    'amount': '1250.00',
                    'currency': 'INR',
                }
            ],
        },
        format='json',
    )

    assert update_response.status_code == 200
    assert update_response.data['title'] == 'Client visit reimbursement'
    line_id = update_response.data['lines'][0]['id']

    upload_response = employee_client.post(
        f'/api/v1/me/expenses/claims/{claim_id}/receipts/',
        {
            'line_id': line_id,
            'file': SimpleUploadedFile('receipt.pdf', b'%PDF-1.7\nreceipt', content_type='application/pdf'),
        },
        format='multipart',
    )

    assert upload_response.status_code == 201
    assert upload_response.data['file_name'] == 'receipt.pdf'
    assert upload_response.data['download_url'].startswith('https://files.test/')

    submit_response = employee_client.post(f'/api/v1/me/expenses/claims/{claim_id}/submit/')

    assert submit_response.status_code == 200
    assert submit_response.data['status'] == 'SUBMITTED'
    assert submit_response.data['approval_run_id'] is not None


@pytest.mark.django_db
def test_org_admin_can_manage_policies_and_view_claim_summary(expense_api_setup):
    organisation = expense_api_setup['organisation']
    employee = expense_api_setup['employee']
    employee_user = expense_api_setup['employee_user']
    org_admin_client = expense_api_setup['org_admin_client']

    policy_response = org_admin_client.post(
        '/api/v1/org/expenses/policies/',
        {
            'name': 'Meals and Travel',
            'description': 'Client travel and food reimbursements',
            'currency': 'INR',
            'categories': [
                {
                    'code': 'MEALS',
                    'name': 'Meals',
                    'per_claim_limit': '1500.00',
                    'requires_receipt': True,
                },
                {
                    'code': 'TRAVEL',
                    'name': 'Travel',
                    'per_claim_limit': '10000.00',
                    'requires_receipt': False,
                },
            ],
        },
        format='json',
    )

    assert policy_response.status_code == 201
    assert len(policy_response.data['categories']) == 2

    policy = ExpensePolicy.objects.get(id=policy_response.data['id'])
    travel = policy.categories.get(code='TRAVEL')
    create_expense_claim(
        employee=employee,
        title='Field visit',
        claim_date=date(2026, 4, 10),
        policy=policy,
        currency='INR',
        lines=[
            {
                'category_id': travel.id,
                'expense_date': date(2026, 4, 10),
                'merchant': 'Railways',
                'description': 'Client visit train fare',
                'amount': '2200.00',
                'currency': 'INR',
            }
        ],
        actor=employee_user,
    )

    list_response = org_admin_client.get('/api/v1/org/expenses/policies/')
    summary_response = org_admin_client.get('/api/v1/org/expenses/claims/summary/')

    assert list_response.status_code == 200
    assert list_response.data[0]['name'] == 'Meals and Travel'
    assert summary_response.status_code == 200
    assert summary_response.data['total_claims'] == 1
    assert summary_response.data['total_amount'] == '2200.00'
    assert summary_response.data['by_status']['DRAFT']['count'] == 1
