from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from .models import (
    SECTION_LIMITS,
    Arrears,
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationTemplate,
    CompensationTemplateLine,
    FullAndFinalSettlement,
    InvestmentDeclaration,
    LabourWelfareFundContribution,
    LabourWelfareFundRule,
    PayrollComponent,
    PayrollRun,
    PayrollRunItem,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    PayrollTDSChallan,
    Payslip,
    ProfessionalTaxRule,
    ProfessionalTaxSlab,
    StatutoryFilingArtifactFormat,
    StatutoryFilingBatch,
    StatutoryFilingType,
    TaxCategory,
    TaxRegime,
)
from .statutory import normalize_fiscal_year_label


class PayrollTaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollTaxSlab
        fields = ['id', 'min_income', 'max_income', 'rate_percent']


class ProfessionalTaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalTaxSlab
        fields = ['id', 'gender', 'min_income', 'max_income', 'deduction_amount', 'applicable_months', 'notes']


class ProfessionalTaxRuleSerializer(serializers.ModelSerializer):
    slabs = ProfessionalTaxSlabSerializer(many=True, read_only=True)

    class Meta:
        model = ProfessionalTaxRule
        fields = [
            'id',
            'country_code',
            'state_code',
            'state_name',
            'income_basis',
            'deduction_frequency',
            'effective_from',
            'effective_to',
            'source_label',
            'source_url',
            'notes',
            'is_active',
            'slabs',
            'created_at',
            'modified_at',
        ]


class LabourWelfareFundContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabourWelfareFundContribution
        fields = ['id', 'min_wage', 'max_wage', 'employee_amount', 'employer_amount', 'applicable_months', 'notes']


class LabourWelfareFundRuleSerializer(serializers.ModelSerializer):
    contributions = LabourWelfareFundContributionSerializer(many=True, read_only=True)

    class Meta:
        model = LabourWelfareFundRule
        fields = [
            'id',
            'country_code',
            'state_code',
            'state_name',
            'wage_basis',
            'deduction_frequency',
            'effective_from',
            'effective_to',
            'source_label',
            'source_url',
            'notes',
            'is_active',
            'contributions',
            'created_at',
            'modified_at',
        ]


class PayrollTDSChallanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollTDSChallan
        fields = [
            'id',
            'fiscal_year',
            'quarter',
            'period_year',
            'period_month',
            'bsr_code',
            'challan_serial_number',
            'deposit_date',
            'tax_deposited',
            'interest_amount',
            'fee_amount',
            'statement_receipt_number',
            'notes',
            'created_at',
            'modified_at',
        ]


class PayrollTaxSlabWriteSerializer(serializers.Serializer):
    min_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    max_income = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    rate_percent = serializers.DecimalField(max_digits=5, decimal_places=2)

    def validate_min_income(self, value):
        if value < 0:
            raise serializers.ValidationError('Minimum income cannot be negative.')
        return value

    def validate_rate_percent(self, value):
        if value < 0:
            raise serializers.ValidationError('Tax rate cannot be negative.')
        if value > 100:
            raise serializers.ValidationError('Tax rate cannot exceed 100%.')
        return value


class PayrollTaxSlabSetSerializer(serializers.ModelSerializer):
    slabs = PayrollTaxSlabSerializer(many=True, read_only=True)
    source_set_id = serializers.UUIDField(source='source_set.id', read_only=True, allow_null=True)

    class Meta:
        model = PayrollTaxSlabSet
        fields = [
            'id',
            'name',
            'country_code',
            'fiscal_year',
            'is_active',
            'is_system_master',
            'is_old_regime',
            'tax_category',
            'source_set_id',
            'slabs',
            'created_at',
            'modified_at',
        ]


class PayrollTaxSlabSetWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    country_code = serializers.CharField(max_length=2, default='IN')
    fiscal_year = serializers.CharField(max_length=16)
    is_active = serializers.BooleanField(required=False, default=True)
    is_old_regime = serializers.BooleanField(required=False, default=False)
    tax_category = serializers.ChoiceField(
        choices=TaxCategory.choices,
        required=False,
        default=TaxCategory.INDIVIDUAL,
    )
    slabs = PayrollTaxSlabWriteSerializer(many=True)


class PayrollTDSChallanWriteSerializer(serializers.Serializer):
    fiscal_year = serializers.CharField(max_length=16)
    period_year = serializers.IntegerField(min_value=2000, max_value=3000)
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    bsr_code = serializers.RegexField(r'^\d{7}$')
    challan_serial_number = serializers.CharField(max_length=16)
    deposit_date = serializers.DateField()
    tax_deposited = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))
    fee_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))
    statement_receipt_number = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        fiscal_year = attrs.get('fiscal_year') or getattr(instance, 'fiscal_year', '')
        organisation = self.context['organisation']
        try:
            start_year_str, end_year_str = fiscal_year.split('-', 1)
            start_year = int(start_year_str)
            end_year = int(end_year_str)
        except (AttributeError, ValueError) as exc:
            raise serializers.ValidationError({'fiscal_year': 'Fiscal year must be in YYYY-YYYY format.'}) from exc

        period_year = attrs.get('period_year', getattr(instance, 'period_year', None))
        period_month = attrs.get('period_month', getattr(instance, 'period_month', None))
        period = (period_year, period_month)
        valid_periods = {
            (start_year, 4),
            (start_year, 5),
            (start_year, 6),
            (start_year, 7),
            (start_year, 8),
            (start_year, 9),
            (start_year, 10),
            (start_year, 11),
            (start_year, 12),
            (end_year, 1),
            (end_year, 2),
            (end_year, 3),
        }
        if period not in valid_periods:
            raise serializers.ValidationError({'period_year': 'Period must fall inside the selected fiscal year.'})

        tax_deposited = attrs.get('tax_deposited', getattr(instance, 'tax_deposited', Decimal('0.00')))
        interest_amount = attrs.get('interest_amount', getattr(instance, 'interest_amount', Decimal('0.00')))
        fee_amount = attrs.get('fee_amount', getattr(instance, 'fee_amount', Decimal('0.00')))
        if tax_deposited < 0 or interest_amount < 0 or fee_amount < 0:
            raise serializers.ValidationError('Tax, interest, and fee amounts cannot be negative.')

        queryset = PayrollTDSChallan.objects.filter(
            organisation=organisation,
            period_year=period_year,
            period_month=period_month,
        )
        if instance is not None:
            queryset = queryset.exclude(id=instance.id)
        if queryset.exists():
            raise serializers.ValidationError({'period_month': 'A TDS challan already exists for this payroll period.'})
        return attrs


class PayrollComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollComponent
        fields = ['id', 'code', 'name', 'component_type', 'is_taxable', 'is_system_default']


class CompensationTemplateLineSerializer(serializers.ModelSerializer):
    component = PayrollComponentSerializer(read_only=True)
    component_id = serializers.UUIDField(source='component.id', read_only=True)

    class Meta:
        model = CompensationTemplateLine
        fields = ['id', 'component_id', 'component', 'monthly_amount', 'sequence']


class CompensationTemplateLineWriteSerializer(serializers.Serializer):
    component_code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=255)
    component_type = serializers.CharField(max_length=32)
    monthly_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_taxable = serializers.BooleanField(required=False, default=True)

    def validate_monthly_amount(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Monthly amount cannot be negative. Use a deduction component type for amounts that reduce pay.'
            )
        return value


class CompensationTemplateSerializer(serializers.ModelSerializer):
    approval_run_id = serializers.UUIDField(source='approval_run.id', read_only=True, allow_null=True)
    lines = CompensationTemplateLineSerializer(many=True, read_only=True)

    class Meta:
        model = CompensationTemplate
        fields = ['id', 'name', 'description', 'status', 'approval_run_id', 'lines', 'created_at', 'modified_at']


class CompensationTemplateWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    lines = CompensationTemplateLineWriteSerializer(many=True)


class CompensationAssignmentLineSerializer(serializers.ModelSerializer):
    component_id = serializers.UUIDField(source='component.id', read_only=True)

    class Meta:
        model = CompensationAssignmentLine
        fields = [
            'id',
            'component_id',
            'component_name',
            'component_type',
            'monthly_amount',
            'is_taxable',
            'sequence',
        ]


class CompensationAssignmentSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    approval_run_id = serializers.UUIDField(source='approval_run.id', read_only=True, allow_null=True)
    lines = CompensationAssignmentLineSerializer(many=True, read_only=True)

    class Meta:
        model = CompensationAssignment
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'template',
            'template_name',
            'effective_from',
            'version',
            'tax_regime',
            'is_pf_opted_out',
            'is_epf_exempt',
            'vpf_rate_percent',
            'status',
            'approval_run_id',
            'lines',
            'created_at',
            'modified_at',
        ]


class CompensationAssignmentWriteSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    template_id = serializers.UUIDField()
    effective_from = serializers.DateField()
    tax_regime = serializers.ChoiceField(choices=TaxRegime.choices, required=False, default=TaxRegime.NEW)
    is_pf_opted_out = serializers.BooleanField(required=False, default=False)
    is_epf_exempt = serializers.BooleanField(required=False, default=False)
    vpf_rate_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=Decimal('12.00'))
    auto_approve = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        is_pf_opted_out = attrs.get('is_pf_opted_out', False)
        vpf_rate_percent = Decimal(str(attrs.get('vpf_rate_percent')))
        if is_pf_opted_out and vpf_rate_percent != Decimal('0.00'):
            attrs['vpf_rate_percent'] = Decimal('0.00')
            return attrs
        if vpf_rate_percent < Decimal('12.00'):
            raise serializers.ValidationError({'vpf_rate_percent': 'Employee PF/VPF rate cannot be below 12% unless PF is opted out.'})
        if vpf_rate_percent > Decimal('100.00'):
            raise serializers.ValidationError({'vpf_rate_percent': 'Employee PF/VPF rate cannot exceed 100% of PF wages.'})
        attrs['vpf_rate_percent'] = vpf_rate_percent.quantize(Decimal('0.01'))
        return attrs


class PayrollRunItemSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)

    class Meta:
        model = PayrollRunItem
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'status',
            'gross_pay',
            'employee_deductions',
            'employer_contributions',
            'income_tax',
            'total_deductions',
            'net_pay',
            'snapshot',
            'message',
        ]


class PayrollRunItemDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    employee_id = serializers.UUIDField()
    employee_name = serializers.CharField()
    employee_code = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    has_exception = serializers.BooleanField()
    gross_pay = serializers.DecimalField(max_digits=12, decimal_places=2)
    employee_deductions = serializers.DecimalField(max_digits=12, decimal_places=2)
    employer_contributions = serializers.DecimalField(max_digits=12, decimal_places=2)
    income_tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_pay = serializers.DecimalField(max_digits=12, decimal_places=2)
    snapshot = serializers.JSONField()
    message = serializers.CharField(allow_blank=True)
    arrears = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lop_days = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    esi_employee = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    esi_employer = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pf_employer = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lwf_employee = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lwf_employer = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pt_monthly = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_regime = serializers.CharField(allow_null=True)


class PayrollRunSerializer(serializers.ModelSerializer):
    approval_run_id = serializers.UUIDField(source='approval_run.id', read_only=True, allow_null=True)
    source_run_id = serializers.UUIDField(source='source_run.id', read_only=True, allow_null=True)
    total_gross = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, default=None)
    total_net = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, default=None)
    total_deductions = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, default=None)
    employee_count = serializers.IntegerField(read_only=True, default=0)
    exception_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = PayrollRun
        fields = [
            'id',
            'name',
            'period_year',
            'period_month',
            'run_type',
            'status',
            'use_attendance_inputs',
            'approval_run_id',
            'source_run_id',
            'attendance_snapshot',
            'calculated_at',
            'submitted_at',
            'finalized_at',
            'total_gross',
            'total_net',
            'total_deductions',
            'employee_count',
            'exception_count',
            'created_at',
            'modified_at',
        ]


class PayrollRunWriteSerializer(serializers.Serializer):
    period_year = serializers.IntegerField(min_value=2000, max_value=3000)
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    use_attendance_inputs = serializers.BooleanField(required=False, default=False)


class PayrollRunCalculationStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    state = serializers.CharField()
    result = serializers.JSONField(required=False, allow_null=True)
    error = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class StatutoryFilingBatchSerializer(serializers.ModelSerializer):
    source_pay_run_ids = serializers.SerializerMethodField()

    class Meta:
        model = StatutoryFilingBatch
        fields = [
            'id',
            'filing_type',
            'status',
            'artifact_format',
            'period_year',
            'period_month',
            'fiscal_year',
            'quarter',
            'checksum',
            'file_name',
            'content_type',
            'file_size_bytes',
            'artifact_storage_backend',
            'artifact_storage_key',
            'artifact_uploaded_at',
            'generated_at',
            'source_signature',
            'validation_errors',
            'metadata',
            'structured_payload',
            'source_pay_run_ids',
            'created_at',
            'modified_at',
        ]

    def get_source_pay_run_ids(self, obj):
        return [str(run_id) for run_id in obj.source_pay_runs.values_list('id', flat=True)]


class StatutoryFilingBatchWriteSerializer(serializers.Serializer):
    filing_type = serializers.ChoiceField(choices=StatutoryFilingType.choices)
    period_year = serializers.IntegerField(min_value=2000, max_value=3000, required=False)
    period_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    fiscal_year = serializers.CharField(max_length=16, required=False, allow_blank=True)
    quarter = serializers.ChoiceField(choices=['Q1', 'Q2', 'Q3', 'Q4'], required=False)
    artifact_format = serializers.ChoiceField(choices=StatutoryFilingArtifactFormat.choices, required=False)

    def validate(self, attrs):
        filing_type = attrs['filing_type']
        if filing_type in {
            StatutoryFilingType.PF_ECR,
            StatutoryFilingType.ESI_MONTHLY,
            StatutoryFilingType.PROFESSIONAL_TAX,
        }:
            if not attrs.get('period_year') or not attrs.get('period_month'):
                raise serializers.ValidationError({'period_year': 'period_year and period_month are required for monthly filing exports.'})

        if filing_type == StatutoryFilingType.FORM24Q:
            if not attrs.get('fiscal_year') or not attrs.get('quarter'):
                raise serializers.ValidationError({'quarter': 'fiscal_year and quarter are required for Form 24Q exports.'})
            attrs['artifact_format'] = StatutoryFilingArtifactFormat.JSON

        if filing_type == StatutoryFilingType.FORM16:
            if not attrs.get('fiscal_year'):
                raise serializers.ValidationError({'fiscal_year': 'fiscal_year is required for Form 16 exports.'})
            attrs['artifact_format'] = attrs.get('artifact_format') or StatutoryFilingArtifactFormat.PDF

        if filing_type != StatutoryFilingType.FORM16 and attrs.get('artifact_format') == StatutoryFilingArtifactFormat.PDF:
            raise serializers.ValidationError({'artifact_format': 'PDF export is only supported for Form 16.'})

        return attrs


class PayslipSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    pay_run_id = serializers.UUIDField(source='pay_run.id', read_only=True)

    class Meta:
        model = Payslip
        fields = [
            'id',
            'employee_id',
            'pay_run_id',
            'slip_number',
            'period_year',
            'period_month',
            'esi_contribution_period_start',
            'esi_contribution_period_end',
            'esi_eligibility_mode',
            'snapshot',
            'rendered_text',
            'created_at',
        ]


class InvestmentDeclarationSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    verified_by_id = serializers.UUIDField(source='verified_by.id', read_only=True, allow_null=True)
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True, allow_null=True)
    section_limit = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentDeclaration
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'fiscal_year',
            'section',
            'description',
            'declared_amount',
            'proof_file_key',
            'is_verified',
            'verified_by_id',
            'verified_by_name',
            'section_limit',
            'created_at',
            'modified_at',
        ]

    def get_section_limit(self, obj):
        limit = SECTION_LIMITS.get(obj.section)
        return str(limit) if limit is not None else None


class FullAndFinalSettlementSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    offboarding_process_id = serializers.UUIDField(source='offboarding_process.id', read_only=True, allow_null=True)

    class Meta:
        model = FullAndFinalSettlement
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'offboarding_process_id',
            'last_working_day',
            'status',
            'prorated_salary',
            'leave_encashment',
            'gratuity',
            'arrears',
            'other_credits',
            'tds_deduction',
            'pf_deduction',
            'loan_recovery',
            'other_deductions',
            'gross_payable',
            'net_payable',
            'notes',
            'approved_at',
            'paid_at',
            'created_at',
            'modified_at',
        ]


class ArrearsSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    pay_run_id = serializers.UUIDField(source='pay_run.id', read_only=True, allow_null=True)

    class Meta:
        model = Arrears
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'pay_run_id',
            'for_period_year',
            'for_period_month',
            'reason',
            'amount',
            'is_included_in_payslip',
            'created_at',
        ]


class InvestmentDeclarationWriteSerializer(serializers.Serializer):
    fiscal_year = serializers.CharField(max_length=16)
    section = serializers.ChoiceField(choices=InvestmentDeclaration._meta.get_field('section').choices)  # type: ignore[arg-type]
    description = serializers.CharField(max_length=200)
    declared_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    proof_file_key = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')

    def validate_fiscal_year(self, value):
        normalized = normalize_fiscal_year_label(value)
        if normalized.count('-') != 1 or len(normalized.split('-', 1)[0]) != 4:
            raise serializers.ValidationError('Fiscal year must be in YYYY-YYYY or YYYY-YY format.')
        return normalized

    def validate_declared_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError('Declared amount must be greater than zero.')
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        employee = self.context.get('employee') or getattr(instance, 'employee', None)

        fiscal_year = attrs.get('fiscal_year') or getattr(instance, 'fiscal_year', '')
        section = attrs.get('section') or getattr(instance, 'section', '')
        declared_amount = attrs.get('declared_amount', getattr(instance, 'declared_amount', Decimal('0.00')))

        attrs['fiscal_year'] = normalize_fiscal_year_label(fiscal_year)

        section_cap = SECTION_LIMITS.get(section)
        if employee is not None and section_cap is not None:
            queryset = InvestmentDeclaration.objects.filter(
                employee=employee,
                section=section,
                fiscal_year=attrs['fiscal_year'],
            )
            if instance is not None:
                queryset = queryset.exclude(id=instance.id)
            existing_total = queryset.aggregate(total=Sum('declared_amount'))['total'] or Decimal('0.00')
            if existing_total + declared_amount > section_cap:
                remaining = max(section_cap - existing_total, Decimal('0.00'))
                raise serializers.ValidationError(
                    {
                        'declared_amount': (
                            f'{section} declarations cannot exceed {section_cap:.2f} in '
                            f'{attrs["fiscal_year"]}. Remaining limit: {remaining:.2f}.'
                        )
                    }
                )

        return attrs


class InvestmentDeclarationReviewSerializer(serializers.Serializer):
    is_verified = serializers.BooleanField()


class ArrearsCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    for_period_year = serializers.IntegerField(min_value=2000, max_value=2099)
    for_period_month = serializers.IntegerField(min_value=1, max_value=12)
    reason = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
