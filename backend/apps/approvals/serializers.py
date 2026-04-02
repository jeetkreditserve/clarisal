from rest_framework import serializers

from .models import (
    ApprovalAction,
    ApprovalApproverType,
    ApprovalFallbackType,
    ApprovalRequestKind,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalStageMode,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)


class ApprovalStageApproverSerializer(serializers.ModelSerializer):
    approver_employee_id = serializers.UUIDField(source='approver_employee.id', read_only=True)
    approver_employee_name = serializers.CharField(source='approver_employee.user.full_name', read_only=True)

    class Meta:
        model = ApprovalStageApprover
        fields = [
            'id',
            'approver_type',
            'approver_employee_id',
            'approver_employee_name',
        ]


class ApprovalStageApproverWriteSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    approver_type = serializers.ChoiceField(choices=ApprovalApproverType.choices)
    approver_employee_id = serializers.UUIDField(required=False, allow_null=True)


class ApprovalStageSerializer(serializers.ModelSerializer):
    approvers = ApprovalStageApproverSerializer(many=True, read_only=True)
    fallback_employee_id = serializers.UUIDField(source='fallback_employee.id', read_only=True)
    fallback_employee_name = serializers.CharField(source='fallback_employee.user.full_name', read_only=True)

    class Meta:
        model = ApprovalStage
        fields = [
            'id',
            'name',
            'sequence',
            'mode',
            'fallback_type',
            'fallback_employee_id',
            'fallback_employee_name',
            'approvers',
        ]


class ApprovalStageWriteSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=255)
    sequence = serializers.IntegerField(min_value=1)
    mode = serializers.ChoiceField(choices=ApprovalStageMode.choices, default=ApprovalStageMode.ALL)
    fallback_type = serializers.ChoiceField(choices=ApprovalFallbackType.choices, default=ApprovalFallbackType.NONE)
    fallback_employee_id = serializers.UUIDField(required=False, allow_null=True)
    approvers = ApprovalStageApproverWriteSerializer(many=True)


class ApprovalWorkflowRuleSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    office_location_name = serializers.CharField(source='office_location.name', read_only=True)
    specific_employee_name = serializers.CharField(source='specific_employee.user.full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = ApprovalWorkflowRule
        fields = [
            'id',
            'name',
            'request_kind',
            'priority',
            'is_active',
            'department',
            'department_name',
            'office_location',
            'office_location_name',
            'specific_employee',
            'specific_employee_name',
            'employment_type',
            'designation',
            'leave_type',
            'leave_type_name',
        ]


class ApprovalWorkflowRuleWriteSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=255)
    request_kind = serializers.ChoiceField(choices=ApprovalRequestKind.choices)
    priority = serializers.IntegerField(min_value=0, default=100)
    is_active = serializers.BooleanField(required=False, default=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)
    specific_employee_id = serializers.UUIDField(required=False, allow_null=True)
    employment_type = serializers.CharField(required=False, allow_blank=True, default='')
    designation = serializers.CharField(required=False, allow_blank=True, default='')
    leave_type_id = serializers.UUIDField(required=False, allow_null=True)


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    rules = ApprovalWorkflowRuleSerializer(many=True, read_only=True)
    stages = ApprovalStageSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalWorkflow
        fields = [
            'id',
            'name',
            'description',
            'is_default',
            'default_request_kind',
            'is_active',
            'rules',
            'stages',
            'created_at',
            'modified_at',
        ]


class ApprovalWorkflowWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_default = serializers.BooleanField(required=False, default=False)
    default_request_kind = serializers.ChoiceField(
        choices=ApprovalRequestKind.choices,
        required=False,
        allow_null=True,
    )
    is_active = serializers.BooleanField(required=False, default=True)
    rules = ApprovalWorkflowRuleWriteSerializer(many=True, required=False, default=list)
    stages = ApprovalStageWriteSerializer(many=True)

    def validate(self, attrs):
        is_default = attrs.get('is_default', False)
        default_request_kind = attrs.get('default_request_kind')
        request_kinds = {
            rule.get('request_kind')
            for rule in attrs.get('rules', [])
            if rule.get('request_kind')
        }
        if is_default and not default_request_kind:
            if len(request_kinds) == 1:
                attrs['default_request_kind'] = request_kinds.pop()
            else:
                raise serializers.ValidationError({'default_request_kind': 'Default workflows must be tied to a single request kind.'})
        if is_default and request_kinds and attrs['default_request_kind'] not in request_kinds:
            raise serializers.ValidationError({'default_request_kind': 'Default workflow kind must match at least one workflow rule.'})
        if not is_default:
            attrs['default_request_kind'] = None
        return attrs


class ApprovalActionSerializer(serializers.ModelSerializer):
    request_kind = serializers.CharField(source='approval_run.request_kind', read_only=True)
    subject_label = serializers.CharField(source='approval_run.subject_label', read_only=True)
    requester_name = serializers.CharField(source='approval_run.requested_by.user.full_name', read_only=True)
    requester_employee_id = serializers.UUIDField(source='approval_run.requested_by.id', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    organisation_id = serializers.UUIDField(source='approval_run.organisation.id', read_only=True)

    class Meta:
        model = ApprovalAction
        fields = [
            'id',
            'status',
            'comment',
            'acted_at',
            'request_kind',
            'subject_label',
            'requester_name',
            'requester_employee_id',
            'stage_name',
            'organisation_id',
            'created_at',
            'modified_at',
        ]


class ApprovalActionDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_comment(self, value):
        if self.context.get('require_comment') and not value.strip():
            raise serializers.ValidationError('A rejection note is required.')
        return value
