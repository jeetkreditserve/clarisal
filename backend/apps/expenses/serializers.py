from rest_framework import serializers

from .models import (
    ExpenseCategory,
    ExpenseClaim,
    ExpenseClaimLine,
    ExpenseClaimStatus,
    ExpensePolicy,
    ExpenseReceipt,
    ExpenseReimbursementStatus,
)
from .services import build_receipt_download_url


class ExpenseReceiptSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseReceipt
        fields = [
            'id',
            'file_name',
            'file_size',
            'mime_type',
            'download_url',
            'created_at',
        ]

    def get_download_url(self, obj):
        return build_receipt_download_url(obj)


class ExpenseClaimLineSerializer(serializers.ModelSerializer):
    receipts = ExpenseReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = ExpenseClaimLine
        fields = [
            'id',
            'category',
            'category_name',
            'expense_date',
            'merchant',
            'description',
            'amount',
            'currency',
            'receipts',
        ]
        read_only_fields = ['id']


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = [
            'id',
            'code',
            'name',
            'per_claim_limit',
            'requires_receipt',
            'is_active',
        ]


class ExpensePolicySerializer(serializers.ModelSerializer):
    categories = ExpenseCategorySerializer(many=True, read_only=True)

    class Meta:
        model = ExpensePolicy
        fields = [
            'id',
            'name',
            'description',
            'currency',
            'is_active',
            'categories',
            'created_at',
            'modified_at',
        ]


class ExpenseClaimSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    approval_run_id = serializers.UUIDField(source='approval_run.id', read_only=True, allow_null=True)
    reimbursement_pay_run_id = serializers.UUIDField(source='reimbursement_pay_run.id', read_only=True, allow_null=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    lines = ExpenseClaimLineSerializer(many=True, read_only=True)

    class Meta:
        model = ExpenseClaim
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'title',
            'claim_date',
            'currency',
            'status',
            'reimbursement_status',
            'approval_run_id',
            'reimbursement_pay_run_id',
            'submitted_at',
            'approved_at',
            'rejected_at',
            'reimbursed_at',
            'rejection_reason',
            'total_amount',
            'lines',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'employee',
            'status',
            'reimbursement_status',
            'submitted_at',
            'approved_at',
            'rejected_at',
            'reimbursed_at',
            'rejection_reason',
            'created_at',
        ]


class ExpenseClaimWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    claim_date = serializers.DateField()
    currency = serializers.CharField(max_length=3, required=False, default='INR')
    policy = serializers.PrimaryKeyRelatedField(
        queryset=ExpensePolicy.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    submit = serializers.BooleanField(required=False, default=True)
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_policy(self, policy):
        employee = self.context['employee']
        if policy and policy.organisation_id != employee.organisation_id:
            raise serializers.ValidationError('Policy does not belong to this organisation.')
        return policy

    def validate_lines(self, lines):
        normalized = []
        for line in lines:
            line_serializer = ExpenseClaimLineWriteSerializer(data=line)
            line_serializer.is_valid(raise_exception=True)
            normalized.append(line_serializer.validated_data)
        return normalized


class ExpenseClaimLineWriteSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(required=False)
    category_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    expense_date = serializers.DateField()
    merchant = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, required=False, default='INR')


class ExpenseCategoryWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=120)
    per_claim_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    requires_receipt = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)


class ExpensePolicyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    currency = serializers.CharField(max_length=3, required=False, default='INR')
    is_active = serializers.BooleanField(required=False, default=True)
    categories = ExpenseCategoryWriteSerializer(many=True, required=False)


class ExpenseReceiptUploadSerializer(serializers.Serializer):
    line_id = serializers.UUIDField()
    file = serializers.FileField()


class ExpenseClaimStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[ExpenseClaimStatus.CANCELLED])


class ExpenseReimbursementStatusSerializer(serializers.Serializer):
    reimbursement_status = serializers.ChoiceField(choices=ExpenseReimbursementStatus.choices)
