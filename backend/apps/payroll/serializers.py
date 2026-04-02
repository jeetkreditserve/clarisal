from rest_framework import serializers

from .models import (
    CompensationAssignment,
    CompensationAssignmentLine,
    CompensationTemplate,
    CompensationTemplateLine,
    PayrollComponent,
    PayrollRun,
    PayrollRunItem,
    PayrollTaxSlab,
    PayrollTaxSlabSet,
    Payslip,
)


class PayrollTaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollTaxSlab
        fields = ['id', 'min_income', 'max_income', 'rate_percent']


class PayrollTaxSlabWriteSerializer(serializers.Serializer):
    min_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    max_income = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    rate_percent = serializers.DecimalField(max_digits=5, decimal_places=2)


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
            'approval_run_id',
            'source_run_id',
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
