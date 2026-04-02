from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel


class PayrollComponentType(models.TextChoices):
    EARNING = 'EARNING', 'Earning'
    EMPLOYEE_DEDUCTION = 'EMPLOYEE_DEDUCTION', 'Employee Deduction'
    EMPLOYER_CONTRIBUTION = 'EMPLOYER_CONTRIBUTION', 'Employer Contribution'
    REIMBURSEMENT = 'REIMBURSEMENT', 'Reimbursement'


class CompensationTemplateStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class CompensationAssignmentStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class PayrollRunType(models.TextChoices):
    REGULAR = 'REGULAR', 'Regular'
    RERUN = 'RERUN', 'Rerun'


class PayrollRunStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    CALCULATED = 'CALCULATED', 'Calculated'
    APPROVAL_PENDING = 'APPROVAL_PENDING', 'Approval Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    FINALIZED = 'FINALIZED', 'Finalized'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PayrollRunItemStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    EXCEPTION = 'EXCEPTION', 'Exception'


class PayrollTaxSlabSet(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='payroll_tax_slab_sets',
    )
    source_set = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='derived_sets',
    )
    name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=2, default='IN')
    fiscal_year = models.CharField(max_length=16)
    is_active = models.BooleanField(default=True)
    is_system_master = models.BooleanField(default=False)

    class Meta:
        db_table = 'payroll_tax_slab_sets'
        ordering = ['organisation_id', 'fiscal_year', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'name', 'fiscal_year'],
                condition=Q(organisation__isnull=False),
                name='unique_payroll_tax_slab_set_per_org_and_year',
            ),
        ]

    def __str__(self):
        scope = self.organisation.name if self.organisation_id else 'Control Tower'
        return f'{scope} - {self.name}'


class PayrollTaxSlab(AuditedBaseModel):
    slab_set = models.ForeignKey(
        PayrollTaxSlabSet,
        on_delete=models.CASCADE,
        related_name='slabs',
    )
    min_income = models.DecimalField(max_digits=12, decimal_places=2)
    max_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'payroll_tax_slabs'
        ordering = ['min_income', 'created_at']


class PayrollComponent(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='payroll_components',
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    component_type = models.CharField(max_length=32, choices=PayrollComponentType.choices)
    is_taxable = models.BooleanField(default=True)
    is_system_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'payroll_components'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organisation', 'code'], name='unique_payroll_component_code_per_org'),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.code}'


class CompensationTemplate(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='compensation_templates',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=CompensationTemplateStatus.choices, default=CompensationTemplateStatus.DRAFT)
    approval_run = models.ForeignKey(
        'approvals.ApprovalRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='compensation_templates',
    )

    class Meta:
        db_table = 'compensation_templates'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organisation', 'name'], name='unique_compensation_template_name_per_org'),
        ]


class CompensationTemplateLine(AuditedBaseModel):
    template = models.ForeignKey(
        CompensationTemplate,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    component = models.ForeignKey(
        PayrollComponent,
        on_delete=models.PROTECT,
        related_name='template_lines',
    )
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'compensation_template_lines'
        ordering = ['sequence', 'created_at']


class CompensationAssignment(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='compensation_assignments',
    )
    template = models.ForeignKey(
        CompensationTemplate,
        on_delete=models.PROTECT,
        related_name='assignments',
    )
    effective_from = models.DateField()
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=24, choices=CompensationAssignmentStatus.choices, default=CompensationAssignmentStatus.DRAFT)
    approval_run = models.ForeignKey(
        'approvals.ApprovalRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='compensation_assignments',
    )

    class Meta:
        db_table = 'compensation_assignments'
        ordering = ['-effective_from', '-version', '-created_at']


class CompensationAssignmentLine(AuditedBaseModel):
    assignment = models.ForeignKey(
        CompensationAssignment,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    component = models.ForeignKey(
        PayrollComponent,
        on_delete=models.PROTECT,
        related_name='assignment_lines',
    )
    component_name = models.CharField(max_length=255)
    component_type = models.CharField(max_length=32, choices=PayrollComponentType.choices)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_taxable = models.BooleanField(default=True)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'compensation_assignment_lines'
        ordering = ['sequence', 'created_at']


class PayrollRun(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='payroll_runs',
    )
    name = models.CharField(max_length=255)
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField()
    run_type = models.CharField(max_length=16, choices=PayrollRunType.choices, default=PayrollRunType.REGULAR)
    status = models.CharField(max_length=24, choices=PayrollRunStatus.choices, default=PayrollRunStatus.DRAFT)
    source_run = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reruns',
    )
    approval_run = models.ForeignKey(
        'approvals.ApprovalRun',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payroll_runs',
    )
    calculated_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payroll_runs'
        ordering = ['-period_year', '-period_month', '-created_at']


class PayrollRunItem(AuditedBaseModel):
    pay_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='items',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_run_items',
    )
    status = models.CharField(max_length=16, choices=PayrollRunItemStatus.choices, default=PayrollRunItemStatus.READY)
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employee_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employer_contributions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    snapshot = models.JSONField(default=dict, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        db_table = 'payroll_run_items'
        ordering = ['employee__employee_code', 'created_at']
        constraints = [
            models.UniqueConstraint(fields=['pay_run', 'employee'], name='unique_payroll_run_item_per_employee'),
        ]


class Payslip(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='payslips',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='payslips',
    )
    pay_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='payslips',
    )
    pay_run_item = models.OneToOneField(
        PayrollRunItem,
        on_delete=models.CASCADE,
        related_name='payslip',
    )
    slip_number = models.CharField(max_length=64)
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict, blank=True)
    rendered_text = models.TextField(blank=True)

    class Meta:
        db_table = 'payslips'
        ordering = ['-period_year', '-period_month', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'pay_run'], name='unique_payslip_per_employee_per_run'),
        ]

