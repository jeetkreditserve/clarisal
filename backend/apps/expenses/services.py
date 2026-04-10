from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.approvals.models import ApprovalRequestKind
from apps.approvals.services import create_approval_run
from apps.audit.services import log_audit_event
from apps.payroll.models import PayrollComponentType, PayrollRunType

from .models import (
    ExpenseCategory,
    ExpenseClaim,
    ExpenseClaimLine,
    ExpenseClaimStatus,
    ExpenseReimbursementStatus,
)


def _normalize_amount(value):
    return Decimal(str(value)).quantize(Decimal('0.01'))


def create_expense_claim(*, employee, title, claim_date, lines, actor=None, policy=None, currency='INR'):
    if not lines:
        raise ValueError('At least one expense line is required.')

    with transaction.atomic():
        claim = ExpenseClaim.objects.create(
            organisation=employee.organisation,
            employee=employee,
            policy=policy,
            title=title,
            claim_date=claim_date,
            currency=currency,
            status=ExpenseClaimStatus.DRAFT,
            reimbursement_status=ExpenseReimbursementStatus.NOT_READY,
        )
        for payload in lines:
            category = None
            if payload.get('category_id'):
                category = ExpenseCategory.objects.get(
                    id=payload['category_id'],
                    policy__organisation=employee.organisation,
                )
            amount = _normalize_amount(payload['amount'])
            if amount <= Decimal('0.00'):
                raise ValueError('Expense line amount must be greater than zero.')
            ExpenseClaimLine.objects.create(
                claim=claim,
                category=category,
                category_name=payload.get('category_name') or (category.name if category else 'Uncategorised'),
                expense_date=payload['expense_date'],
                merchant=payload.get('merchant', ''),
                description=payload.get('description', ''),
                amount=amount,
                currency=payload.get('currency', currency),
            )

    log_audit_event(actor, 'expense.claim.created', organisation=employee.organisation, target=claim)
    return claim


def submit_expense_claim(claim, *, requester, actor=None):
    if claim.employee_id != requester.id:
        raise ValueError('Only the claim owner can submit this expense claim.')
    if claim.status not in [ExpenseClaimStatus.DRAFT, ExpenseClaimStatus.REJECTED]:
        raise ValueError('Only draft or rejected expense claims can be submitted.')
    if not claim.lines.exists():
        raise ValueError('At least one expense line is required.')

    with transaction.atomic():
        approval_run = create_approval_run(
            claim,
            ApprovalRequestKind.EXPENSE_CLAIM,
            requester,
            actor=actor,
            subject_label=claim.title,
        )
        claim.approval_run = approval_run
        claim.status = ExpenseClaimStatus.SUBMITTED
        claim.reimbursement_status = ExpenseReimbursementStatus.NOT_READY
        claim.submitted_at = timezone.now()
        claim.save(update_fields=['approval_run', 'status', 'reimbursement_status', 'submitted_at', 'modified_at'])

    log_audit_event(actor or requester.user, 'expense.claim.submitted', organisation=claim.organisation, target=claim)
    return claim


def reset_expense_claims_for_pay_run(pay_run):
    ExpenseClaim.objects.filter(
        reimbursement_pay_run=pay_run,
        reimbursement_status=ExpenseReimbursementStatus.INCLUDED_IN_PAYROLL,
    ).update(
        reimbursement_status=ExpenseReimbursementStatus.PENDING_PAYROLL,
        reimbursement_pay_run=None,
        reimbursement_pay_run_item=None,
        modified_at=timezone.now(),
    )


def get_pending_expense_claims_by_employee_for_pay_run(pay_run):
    if pay_run.run_type != PayrollRunType.REGULAR:
        return {}

    claims = (
        ExpenseClaim.objects.filter(
            organisation=pay_run.organisation,
            status=ExpenseClaimStatus.APPROVED,
            reimbursement_status=ExpenseReimbursementStatus.PENDING_PAYROLL,
        )
        .select_related('employee__user')
        .prefetch_related('lines')
        .order_by('approved_at', 'created_at')
    )
    grouped = defaultdict(list)
    for claim in claims:
        grouped[claim.employee_id].append(claim)
    return grouped


def build_payroll_reimbursement_lines(claims):
    lines = []
    total = Decimal('0.00')
    for claim in claims:
        amount = claim.total_amount
        if amount <= Decimal('0.00'):
            continue
        lines.append(
            {
                'component_code': f'EXPENSE_{str(claim.id)[:8].upper()}',
                'component_name': claim.title,
                'component_type': PayrollComponentType.REIMBURSEMENT,
                'monthly_amount': str(amount),
                'is_taxable': False,
                'auto_calculated': True,
                'source': 'EXPENSE_CLAIM',
                'source_id': str(claim.id),
            }
        )
        total += amount
    return lines, total.quantize(Decimal('0.01'))


def mark_expense_claims_included_in_payroll(pay_run_item, claims):
    now = timezone.now()
    for claim in claims:
        claim.reimbursement_status = ExpenseReimbursementStatus.INCLUDED_IN_PAYROLL
        claim.reimbursement_pay_run = pay_run_item.pay_run
        claim.reimbursement_pay_run_item = pay_run_item
        claim.reimbursed_at = None
        claim.save(
            update_fields=[
                'reimbursement_status',
                'reimbursement_pay_run',
                'reimbursement_pay_run_item',
                'reimbursed_at',
                'modified_at',
            ]
        )
    if claims:
        log_audit_event(
            None,
            'expense.claims.included_in_payroll',
            organisation=pay_run_item.pay_run.organisation,
            target=pay_run_item.pay_run,
            payload={'pay_run_item_id': str(pay_run_item.id), 'claim_count': len(claims), 'included_at': now.isoformat()},
        )


def mark_expense_claims_paid_for_pay_run_item(pay_run_item):
    ExpenseClaim.objects.filter(
        reimbursement_pay_run_item=pay_run_item,
        reimbursement_status=ExpenseReimbursementStatus.INCLUDED_IN_PAYROLL,
    ).update(
        reimbursement_status=ExpenseReimbursementStatus.PAID,
        reimbursed_at=timezone.now(),
        modified_at=timezone.now(),
    )
