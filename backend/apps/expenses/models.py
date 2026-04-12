from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import AuditedBaseModel


class ExpenseClaimStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ExpenseReimbursementStatus(models.TextChoices):
    NOT_READY = 'NOT_READY', 'Not Ready'
    PENDING_PAYROLL = 'PENDING_PAYROLL', 'Pending Payroll'
    INCLUDED_IN_PAYROLL = 'INCLUDED_IN_PAYROLL', 'Included In Payroll'
    PAID = 'PAID', 'Paid'


class ExpensePolicy(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='expense_policies',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default='INR')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'expense_policies'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'name'],
                name='unique_expense_policy_per_org',
            ),
        ]

    def __str__(self):
        return self.name


class ExpenseCategory(AuditedBaseModel):
    policy = models.ForeignKey(
        ExpensePolicy,
        on_delete=models.CASCADE,
        related_name='categories',
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=120)
    per_claim_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    requires_receipt = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'expense_categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['policy', 'code'],
                name='unique_expense_category_code_per_policy',
            ),
        ]

    def __str__(self):
        return self.name


class ExpenseClaim(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='expense_claims',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='expense_claims',
    )
    policy = models.ForeignKey(
        ExpensePolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claims',
    )
    title = models.CharField(max_length=200)
    claim_date = models.DateField()
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(
        max_length=20,
        choices=ExpenseClaimStatus.choices,
        default=ExpenseClaimStatus.DRAFT,
    )
    reimbursement_status = models.CharField(
        max_length=24,
        choices=ExpenseReimbursementStatus.choices,
        default=ExpenseReimbursementStatus.NOT_READY,
    )
    approval_run = models.ForeignKey(
        'approvals.ApprovalRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='expense_claims',
    )
    reimbursement_pay_run = models.ForeignKey(
        'payroll.PayrollRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='expense_claims',
    )
    reimbursement_pay_run_item = models.ForeignKey(
        'payroll.PayrollRunItem',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='expense_claims',
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    reimbursed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'expense_claims'
        ordering = ['-claim_date', '-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status'], name='expense_claim_org_status_idx'),
            models.Index(fields=['employee', 'reimbursement_status'], name='expense_claim_emp_reimb_idx'),
            models.Index(fields=['reimbursement_pay_run'], name='expense_claim_pay_run_idx'),
        ]

    def __str__(self):
        return f'{self.employee} - {self.title}'

    @property
    def total_amount(self):
        return sum((line.amount for line in self.lines.all()), Decimal('0.00')).quantize(Decimal('0.01'))

    def handle_approval_status_change(self, new_status, rejection_reason=''):
        now = timezone.now()
        update_fields = ['status', 'reimbursement_status', 'modified_at']
        if new_status == 'APPROVED':
            self.status = ExpenseClaimStatus.APPROVED
            self.reimbursement_status = ExpenseReimbursementStatus.PENDING_PAYROLL
            self.approved_at = now
            self.rejection_reason = ''
            update_fields.extend(['approved_at', 'rejection_reason'])
        elif new_status == 'REJECTED':
            self.status = ExpenseClaimStatus.REJECTED
            self.reimbursement_status = ExpenseReimbursementStatus.NOT_READY
            self.rejected_at = now
            self.rejection_reason = rejection_reason or ''
            update_fields.extend(['rejected_at', 'rejection_reason'])
        elif new_status == 'CANCELLED':
            self.status = ExpenseClaimStatus.CANCELLED
            self.reimbursement_status = ExpenseReimbursementStatus.NOT_READY
        else:
            return
        self.save(update_fields=update_fields)


class ExpenseClaimLine(AuditedBaseModel):
    claim = models.ForeignKey(
        ExpenseClaim,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    category = models.ForeignKey(
        ExpenseCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claim_lines',
    )
    category_name = models.CharField(max_length=120)
    expense_date = models.DateField()
    merchant = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')

    class Meta:
        db_table = 'expense_claim_lines'
        ordering = ['expense_date', 'created_at']

    def __str__(self):
        return f'{self.category_name}: {self.amount}'


class ExpenseReceipt(AuditedBaseModel):
    line = models.ForeignKey(
        ExpenseClaimLine,
        on_delete=models.CASCADE,
        related_name='receipts',
    )
    file_key = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='expense_receipts_uploaded',
    )

    class Meta:
        db_table = 'expense_receipts'
        ordering = ['created_at']

    def __str__(self):
        return self.file_name
