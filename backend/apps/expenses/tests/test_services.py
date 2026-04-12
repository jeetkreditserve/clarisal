from datetime import date
from decimal import Decimal

import pytest

from apps.approvals.models import ApprovalRequestKind
from apps.approvals.services import approve_action
from apps.expenses.models import ExpenseClaimStatus, ExpenseReimbursementStatus
from apps.expenses.services import create_expense_claim, submit_expense_claim
from apps.payroll.models import PayrollComponentType, PayrollRunStatus, TaxRegime
from apps.payroll.services import (
    assign_employee_compensation,
    calculate_pay_run,
    create_compensation_template,
    create_payroll_run,
    create_tax_slab_set,
    ensure_org_payroll_setup,
    finalize_pay_run,
)
from apps.payroll.tests.test_service_setup import (
    _create_active_organisation,
    _create_employee,
    _create_workflow,
)


def _create_tax_master(organisation, actor):
    create_tax_slab_set(
        fiscal_year='2026-2027',
        name='Expense Payroll Slabs',
        country_code='IN',
        slabs=[
            {'min_income': '0', 'max_income': '300000', 'rate_percent': '0'},
            {'min_income': '300000', 'max_income': None, 'rate_percent': '5'},
        ],
        organisation=organisation,
        actor=actor,
    )


def _create_basic_compensation(organisation, actor, employee, *, template_name='Expense Payroll Template'):
    ensure_org_payroll_setup(organisation, actor=actor)
    template = create_compensation_template(
        organisation,
        name=template_name,
        actor=actor,
        lines=[
            {
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': PayrollComponentType.EARNING,
                'monthly_amount': '30000.00',
                'is_taxable': True,
            },
        ],
    )
    assign_employee_compensation(
        employee,
        template,
        effective_from=date(2026, 4, 1),
        actor=actor,
        auto_approve=True,
        tax_regime=TaxRegime.NEW,
    )


@pytest.mark.django_db
def test_submitting_expense_claim_creates_existing_approval_workflow_run():
    organisation = _create_active_organisation('Expense Approval Org')
    requester_user, requester_employee = _create_employee(
        organisation,
        'expense-requester@test.com',
        employee_code='EMPEXP1',
    )
    approver_user, approver_employee = _create_employee(
        organisation,
        'expense-approver@test.com',
        employee_code='EMPEXP2',
    )
    _create_workflow(organisation, approver_employee, ApprovalRequestKind.EXPENSE_CLAIM)
    claim = create_expense_claim(
        employee=requester_employee,
        title='Client visit reimbursement',
        claim_date=date(2026, 4, 9),
        lines=[
            {
                'category_name': 'Travel',
                'expense_date': date(2026, 4, 8),
                'merchant': 'Metro Cabs',
                'description': 'Airport cab',
                'amount': Decimal('1200.00'),
            },
        ],
        actor=requester_user,
    )

    submitted = submit_expense_claim(claim, requester=requester_employee, actor=requester_user)

    assert submitted.status == ExpenseClaimStatus.SUBMITTED
    assert submitted.reimbursement_status == ExpenseReimbursementStatus.NOT_READY
    assert submitted.approval_run.request_kind == ApprovalRequestKind.EXPENSE_CLAIM
    assert submitted.approval_run.actions.get().approver_user == approver_user


@pytest.mark.django_db
def test_approved_expense_claim_is_reimbursed_through_next_open_payroll_run():
    organisation = _create_active_organisation('Expense Payroll Org')
    requester_user, requester_employee = _create_employee(
        organisation,
        'expense-payroll-requester@test.com',
        employee_code='EMPEXP3',
    )
    approver_user, approver_employee = _create_employee(
        organisation,
        'expense-payroll-approver@test.com',
        employee_code='EMPEXP4',
    )
    _create_workflow(organisation, approver_employee, ApprovalRequestKind.EXPENSE_CLAIM)
    _create_tax_master(organisation, requester_user)
    _create_basic_compensation(organisation, requester_user, requester_employee)
    _create_basic_compensation(
        organisation,
        requester_user,
        approver_employee,
        template_name='Expense Payroll Approver Template',
    )
    claim = create_expense_claim(
        employee=requester_employee,
        title='Approved travel claim',
        claim_date=date(2026, 4, 10),
        lines=[
            {
                'category_name': 'Travel',
                'expense_date': date(2026, 4, 10),
                'merchant': 'Railways',
                'description': 'Client meeting train fare',
                'amount': Decimal('1500.00'),
            },
        ],
        actor=requester_user,
    )
    claim = submit_expense_claim(claim, requester=requester_employee, actor=requester_user)

    approve_action(claim.approval_run.actions.get(), approver_user)
    claim.refresh_from_db()

    assert claim.status == ExpenseClaimStatus.APPROVED
    assert claim.reimbursement_status == ExpenseReimbursementStatus.PENDING_PAYROLL

    pay_run = create_payroll_run(
        organisation,
        period_year=2026,
        period_month=4,
        requester_user=requester_user,
    )

    calculate_pay_run(pay_run, actor=requester_user)
    claim.refresh_from_db()
    item = pay_run.items.get(employee=requester_employee)
    reimbursement_line = next(line for line in item.snapshot['lines'] if line.get('source') == 'EXPENSE_CLAIM')

    assert claim.reimbursement_status == ExpenseReimbursementStatus.INCLUDED_IN_PAYROLL
    assert claim.reimbursement_pay_run == pay_run
    assert claim.reimbursement_pay_run_item == item
    assert reimbursement_line['component_type'] == PayrollComponentType.REIMBURSEMENT
    assert reimbursement_line['monthly_amount'] == '1500.00'
    assert reimbursement_line['is_taxable'] is False
    assert item.gross_pay == Decimal('31500.00')
    assert item.snapshot['expense_reimbursements'] == '1500.00'
    assert item.net_pay == item.gross_pay - item.total_deductions
    assert item.snapshot['annual_taxable_gross'] == '360000.00'

    pay_run.status = PayrollRunStatus.APPROVED
    pay_run.save(update_fields=['status'])
    finalize_pay_run(pay_run, actor=requester_user)
    claim.refresh_from_db()

    assert claim.reimbursement_status == ExpenseReimbursementStatus.PAID
    assert claim.reimbursed_at is not None
