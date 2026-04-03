from rest_framework import serializers

from .models import (
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationTemplate,
    CompensationTemplateLine,
    FullAndFinalSettlement,
    InvestmentDeclaration,
    PayrollComponent,
    PayrollRun,
    PayrollRunItem,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    Payslip,
    TaxRegime,
)


class PayrollTaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollTaxSlab
        fields = ['id', 'min_income', 'max_income', 'rate_percent']


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
    slabs = PayrollTaxSlabWriteSerializer(many=True)


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
    auto_approve = serializers.BooleanField(required=False, default=False)


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


class PayrollRunSerializer(serializers.ModelSerializer):
    items = PayrollRunItemSerializer(many=True, read_only=True)
    approval_run_id = serializers.UUIDField(source='approval_run.id', read_only=True, allow_null=True)
    source_run_id = serializers.UUIDField(source='source_run.id', read_only=True, allow_null=True)

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
            'items',
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
            'snapshot',
            'rendered_text',
            'created_at',
        ]


class InvestmentDeclarationSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)

    class Meta:
        model = InvestmentDeclaration
        fields = [
            'id',
            'employee_id',
            'fiscal_year',
            'section',
            'description',
            'declared_amount',
            'proof_file_key',
            'is_verified',
            'created_at',
            'modified_at',
        ]


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


class InvestmentDeclarationWriteSerializer(serializers.Serializer):
    fiscal_year = serializers.CharField(max_length=16)
    section = serializers.ChoiceField(choices=InvestmentDeclaration._meta.get_field('section').choices)  # type: ignore[arg-type]
    description = serializers.CharField(max_length=200)
    declared_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    proof_file_key = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')
