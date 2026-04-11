from decimal import Decimal

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


class TaxRegime(models.TextChoices):
    NEW = 'NEW', 'New Regime'
    OLD = 'OLD', 'Old Regime'


class TaxCategory(models.TextChoices):
    INDIVIDUAL = 'INDIVIDUAL', 'Individual (age < 60)'
    SENIOR_CITIZEN = 'SENIOR_CITIZEN', 'Senior Citizen (age 60–79)'
    SUPER_SENIOR_CITIZEN = 'SUPER_SENIOR_CITIZEN', 'Super Senior Citizen (age ≥ 80)'


class StatutoryIncomeBasis(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    HALF_YEARLY = 'HALF_YEARLY', 'Half Yearly'
    ANNUAL = 'ANNUAL', 'Annual'


class StatutoryDeductionFrequency(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    HALF_YEARLY = 'HALF_YEARLY', 'Half Yearly'
    ANNUAL = 'ANNUAL', 'Annual'


class ProfessionalTaxGender(models.TextChoices):
    ANY = 'ANY', 'Any'
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'


class InvestmentSection(models.TextChoices):
    SECTION_80C = '80C', 'Section 80C'
    SECTION_80D = '80D', 'Section 80D'
    SECTION_80TTA = '80TTA', 'Section 80TTA'
    SECTION_80G = '80G', 'Section 80G'
    HRA = 'HRA', 'House Rent Allowance'
    LTA = 'LTA', 'Leave Travel Allowance'
    OTHER = 'OTHER', 'Other'


SECTION_LIMITS = {
    InvestmentSection.SECTION_80C: Decimal('150000.00'),
    InvestmentSection.SECTION_80D: Decimal('50000.00'),
    InvestmentSection.SECTION_80TTA: Decimal('10000.00'),
}


class PayrollRunType(models.TextChoices):
    REGULAR = 'REGULAR', 'Regular'
    RERUN = 'RERUN', 'Rerun'


class FNFStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    CALCULATED = 'CALCULATED', 'Calculated'
    APPROVED = 'APPROVED', 'Approved'
    PAID = 'PAID', 'Paid'
    CANCELLED = 'CANCELLED', 'Cancelled'


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


class ESIEligibilityMode(models.TextChoices):
    NONE = 'NONE', 'None'
    DIRECT = 'DIRECT', 'Direct Eligibility'
    CONTINUED = 'CONTINUED', 'Continued For Contribution Period'


class StatutoryFilingType(models.TextChoices):
    PF_ECR = 'PF_ECR', 'PF ECR'
    ESI_MONTHLY = 'ESI_MONTHLY', 'ESI Monthly'
    FORM24Q = 'FORM24Q', 'Form 24Q'
    PROFESSIONAL_TAX = 'PROFESSIONAL_TAX', 'Professional Tax'
    FORM16 = 'FORM16', 'Form 16'


class StatutoryFilingStatus(models.TextChoices):
    READY = 'READY', 'Ready'
    BLOCKED = 'BLOCKED', 'Blocked'
    GENERATED = 'GENERATED', 'Generated'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'
    CANCELLED = 'CANCELLED', 'Cancelled'


class StatutoryFilingArtifactFormat(models.TextChoices):
    CSV = 'CSV', 'CSV'
    JSON = 'JSON', 'JSON'
    XML = 'XML', 'XML'
    PDF = 'PDF', 'PDF'
    TEXT = 'TEXT', 'Text'


class TDSQuarter(models.TextChoices):
    Q1 = 'Q1', 'Q1'
    Q2 = 'Q2', 'Q2'
    Q3 = 'Q3', 'Q3'
    Q4 = 'Q4', 'Q4'


def tds_quarter_for_month(month: int) -> str:
    if month in {4, 5, 6}:
        return TDSQuarter.Q1
    if month in {7, 8, 9}:
        return TDSQuarter.Q2
    if month in {10, 11, 12}:
        return TDSQuarter.Q3
    return TDSQuarter.Q4


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
    is_old_regime = models.BooleanField(
        default=False,
        help_text=(
            'If True, this slab set represents the old tax regime. '
            'Old regime allows additional deductions such as HRA, 80C, and 80D.'
        ),
    )
    tax_category = models.CharField(
        max_length=24,
        choices=TaxCategory.choices,
        default=TaxCategory.INDIVIDUAL,
        help_text=(
            'Age-based taxpayer category. '
            'Determines different basic exemption thresholds in the old regime.'
        ),
    )

    class Meta:
        db_table = 'payroll_tax_slab_sets'
        ordering = ['organisation_id', 'fiscal_year', 'is_old_regime', 'tax_category']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'name', 'fiscal_year'],
                condition=Q(organisation__isnull=False),
                name='unique_payroll_tax_slab_set_per_org_and_year',
            ),
            models.UniqueConstraint(
                fields=['country_code', 'fiscal_year', 'is_old_regime', 'tax_category'],
                condition=Q(organisation__isnull=True),
                name='unique_ct_tax_slab_set_per_regime_category_year',
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


class ProfessionalTaxRule(AuditedBaseModel):
    country_code = models.CharField(max_length=2, default='IN')
    state_code = models.CharField(max_length=16)
    state_name = models.CharField(max_length=100)
    income_basis = models.CharField(
        max_length=16,
        choices=StatutoryIncomeBasis.choices,
        default=StatutoryIncomeBasis.MONTHLY,
    )
    deduction_frequency = models.CharField(
        max_length=16,
        choices=StatutoryDeductionFrequency.choices,
        default=StatutoryDeductionFrequency.MONTHLY,
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    source_label = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'professional_tax_rules'
        ordering = ['country_code', 'state_code', '-effective_from']
        constraints = [
            models.UniqueConstraint(
                fields=['country_code', 'state_code', 'effective_from'],
                name='unique_professional_tax_rule_version',
            ),
        ]

    def __str__(self):
        return f'{self.state_name} PT ({self.effective_from})'


class ProfessionalTaxSlab(AuditedBaseModel):
    rule = models.ForeignKey(
        ProfessionalTaxRule,
        on_delete=models.CASCADE,
        related_name='slabs',
    )
    gender = models.CharField(
        max_length=16,
        choices=ProfessionalTaxGender.choices,
        default=ProfessionalTaxGender.ANY,
    )
    min_income = models.DecimalField(max_digits=12, decimal_places=2)
    max_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    deduction_amount = models.DecimalField(max_digits=12, decimal_places=2)
    applicable_months = models.JSONField(default=list, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'professional_tax_slabs'
        ordering = ['gender', 'min_income', 'created_at']


class LabourWelfareFundRule(AuditedBaseModel):
    country_code = models.CharField(max_length=2, default='IN')
    state_code = models.CharField(max_length=16)
    state_name = models.CharField(max_length=100)
    wage_basis = models.CharField(
        max_length=16,
        choices=StatutoryIncomeBasis.choices,
        default=StatutoryIncomeBasis.MONTHLY,
    )
    deduction_frequency = models.CharField(
        max_length=16,
        choices=StatutoryDeductionFrequency.choices,
        default=StatutoryDeductionFrequency.HALF_YEARLY,
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    source_label = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'labour_welfare_fund_rules'
        ordering = ['country_code', 'state_code', '-effective_from']
        constraints = [
            models.UniqueConstraint(
                fields=['country_code', 'state_code', 'effective_from'],
                name='unique_labour_welfare_fund_rule_version',
            ),
        ]

    def __str__(self):
        return f'{self.state_name} LWF ({self.effective_from})'


class LabourWelfareFundContribution(AuditedBaseModel):
    rule = models.ForeignKey(
        LabourWelfareFundRule,
        on_delete=models.CASCADE,
        related_name='contributions',
    )
    min_wage = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_wage = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    employee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    employer_amount = models.DecimalField(max_digits=12, decimal_places=2)
    applicable_months = models.JSONField(default=list, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'labour_welfare_fund_contributions'
        ordering = ['min_wage', 'created_at']


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
    cost_centre = models.ForeignKey(
        'CostCentre',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='template_lines',
    )

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
    tax_regime = models.CharField(max_length=3, choices=TaxRegime.choices, default=TaxRegime.NEW)
    is_pf_opted_out = models.BooleanField(
        default=False,
        help_text='Use only for eligible higher-wage new joiners whose EPF membership can be lawfully opted out.',
    )
    is_epf_exempt = models.BooleanField(
        default=False,
        help_text='Explicitly mark employees who are not required to continue EPF membership despite a PF opt-out request.',
    )
    vpf_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        help_text='Employee-side PF deduction rate. Use values above 12% to represent VPF.',
    )
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
        indexes = [
            models.Index(
                fields=['employee', 'status', 'effective_from'],
                name='comp_assign_emp_status_eff_idx',
            ),
        ]


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
    cost_centre = models.ForeignKey(
        'CostCentre',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignment_lines',
    )

    class Meta:
        db_table = 'compensation_assignment_lines'
        ordering = ['sequence', 'created_at']


class InvestmentDeclaration(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='investment_declarations',
    )
    fiscal_year = models.CharField(max_length=16)
    section = models.CharField(max_length=10, choices=InvestmentSection.choices)
    description = models.CharField(max_length=200)
    declared_amount = models.DecimalField(max_digits=12, decimal_places=2)
    proof_file_key = models.CharField(max_length=500, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_investment_declarations',
    )

    class Meta:
        db_table = 'investment_declarations'
        ordering = ['section', 'created_at']
        indexes = [
            models.Index(fields=['employee', 'fiscal_year']),
        ]

    def __str__(self):
        return f'{self.employee} - {self.section} - ₹{self.declared_amount}'


class FullAndFinalSettlement(AuditedBaseModel):
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.PROTECT,
        related_name='full_and_final_settlement',
    )
    offboarding_process = models.OneToOneField(
        'employees.EmployeeOffboardingProcess',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fnf_settlement',
    )
    last_working_day = models.DateField()
    status = models.CharField(max_length=20, choices=FNFStatus.choices, default=FNFStatus.DRAFT)
    prorated_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    leave_encashment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gratuity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    arrears = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_credits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tds_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pf_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loan_recovery = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_fnf_settlements',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'full_and_final_settlements'
        ordering = ['-created_at']


class Arrears(AuditedBaseModel):
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='arrears',
    )
    pay_run = models.ForeignKey(
        'PayrollRun',
        on_delete=models.CASCADE,
        related_name='arrears_items',
        null=True,
        blank=True,
    )
    for_period_year = models.PositiveSmallIntegerField()
    for_period_month = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_included_in_payslip = models.BooleanField(default=False)

    class Meta:
        db_table = 'payroll_arrears'
        ordering = ['for_period_year', 'for_period_month', 'created_at']
        indexes = [
            models.Index(fields=['employee', 'pay_run']),
        ]


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
    use_attendance_inputs = models.BooleanField(default=False)
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
    attendance_snapshot = models.JSONField(default=dict, blank=True)
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
        indexes = [
            models.Index(fields=['pay_run', 'employee'], name='payrunitem_run_emp_idx'),
            models.Index(fields=['employee', 'pay_run'], name='payrunitem_emp_run_idx'),
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
    esi_contribution_period_start = models.DateField(null=True, blank=True)
    esi_contribution_period_end = models.DateField(null=True, blank=True)
    esi_eligibility_mode = models.CharField(
        max_length=16,
        choices=ESIEligibilityMode.choices,
        default=ESIEligibilityMode.NONE,
    )
    snapshot = models.JSONField(default=dict, blank=True)
    rendered_text = models.TextField(blank=True)

    class Meta:
        db_table = 'payslips'
        ordering = ['-period_year', '-period_month', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'pay_run'], name='unique_payslip_per_employee_per_run'),
        ]


class StatutoryFilingBatch(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='statutory_filing_batches',
    )
    filing_type = models.CharField(max_length=32, choices=StatutoryFilingType.choices)
    status = models.CharField(max_length=16, choices=StatutoryFilingStatus.choices, default=StatutoryFilingStatus.READY)
    artifact_format = models.CharField(
        max_length=16,
        choices=StatutoryFilingArtifactFormat.choices,
        default=StatutoryFilingArtifactFormat.CSV,
    )
    period_year = models.PositiveIntegerField(null=True, blank=True)
    period_month = models.PositiveIntegerField(null=True, blank=True)
    fiscal_year = models.CharField(max_length=16, blank=True)
    quarter = models.CharField(max_length=2, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    artifact_storage_backend = models.CharField(max_length=32, blank=True)
    artifact_storage_key = models.CharField(max_length=500, blank=True)
    artifact_uploaded_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    source_signature = models.CharField(max_length=64, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    structured_payload = models.JSONField(default=dict, blank=True)
    artifact_text = models.TextField(blank=True)
    source_pay_runs: models.ManyToManyField = models.ManyToManyField(
        'PayrollRun',
        related_name='statutory_filing_batches',
        blank=True,
    )

    class Meta:
        db_table = 'statutory_filing_batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'filing_type', 'status']),
            models.Index(fields=['organisation', 'period_year', 'period_month']),
            models.Index(fields=['organisation', 'fiscal_year', 'quarter']),
        ]


class PayrollTDSChallan(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='payroll_tds_challans',
    )
    fiscal_year = models.CharField(max_length=16)
    quarter = models.CharField(max_length=2, choices=TDSQuarter.choices)
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField()
    bsr_code = models.CharField(max_length=7)
    challan_serial_number = models.CharField(max_length=16)
    deposit_date = models.DateField()
    tax_deposited = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statement_receipt_number = models.CharField(max_length=32, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'payroll_tds_challans'
        ordering = ['fiscal_year', 'period_year', 'period_month', 'deposit_date']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'period_year', 'period_month'],
                name='unique_payroll_tds_challan_per_org_period',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'fiscal_year', 'quarter']),
            models.Index(fields=['organisation', 'period_year', 'period_month']),
        ]

    def __str__(self):
        return f'{self.organisation.name} TDS challan {self.period_month:02d}/{self.period_year}'

    def save(self, *args, **kwargs):
        self.quarter = tds_quarter_for_month(self.period_month)
        super().save(*args, **kwargs)


class SurchargeRule(models.Model):
    fiscal_year = models.CharField(max_length=9)
    tax_regime = models.CharField(max_length=10, choices=[("OLD", "Old"), ("NEW", "New")])
    income_threshold = models.DecimalField(max_digits=14, decimal_places=2)
    surcharge_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()

    class Meta:
        db_table = 'payroll_surcharge_rules'
        unique_together = [("fiscal_year", "tax_regime", "income_threshold")]
        ordering = ["fiscal_year", "tax_regime", "income_threshold"]

    def __str__(self):
        return f"{self.fiscal_year} {self.tax_regime} >{self.income_threshold}: {self.surcharge_rate_percent}%"


class CostCentre(models.Model):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='cost_centres',
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    gl_code = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_cost_centres'
        unique_together = [('organisation', 'code')]
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"
