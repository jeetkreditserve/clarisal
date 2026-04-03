from rest_framework import serializers

from .models import (
    Holiday,
    HolidayCalendar,
    HolidayClassification,
    LeaveCycle,
    LeaveCycleType,
    LeaveCreditFrequency,
    LeavePlan,
    LeavePlanRule,
    LeaveRequest,
    LeaveType,
    OnDutyPolicy,
    OnDutyRequest,
)


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = [
            'id',
            'name',
            'holiday_date',
            'classification',
            'session',
            'description',
        ]


class HolidayWriteSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=255)
    holiday_date = serializers.DateField()
    classification = serializers.ChoiceField(choices=HolidayClassification.choices, default=HolidayClassification.PUBLIC)
    session = serializers.ChoiceField(choices=Holiday._meta.get_field('session').choices, default='FULL_DAY')
    description = serializers.CharField(required=False, allow_blank=True, default='')


class HolidayCalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)
    location_ids = serializers.SerializerMethodField()

    class Meta:
        model = HolidayCalendar
        fields = [
            'id',
            'name',
            'year',
            'description',
            'status',
            'is_default',
            'location_ids',
            'holidays',
            'published_at',
            'created_at',
            'modified_at',
        ]

    def get_location_ids(self, obj):
        return [str(item.office_location_id) for item in obj.location_assignments.all()]


class HolidayCalendarWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_default = serializers.BooleanField(required=False, default=False)
    holidays = HolidayWriteSerializer(many=True, required=False, default=list)
    location_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)


class LeaveCycleSerializer(serializers.ModelSerializer):
    leave_plan_count = serializers.SerializerMethodField()
    active_leave_plan_count = serializers.SerializerMethodField()

    class Meta:
        model = LeaveCycle
        fields = [
            'id',
            'name',
            'cycle_type',
            'start_month',
            'start_day',
            'is_default',
            'is_active',
            'leave_plan_count',
            'active_leave_plan_count',
            'created_at',
            'modified_at',
        ]

    def get_leave_plan_count(self, obj):
        return obj.leave_plans.count()

    def get_active_leave_plan_count(self, obj):
        return obj.leave_plans.filter(is_active=True).count()


class LeaveCycleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    cycle_type = serializers.ChoiceField(choices=LeaveCycleType.choices, default=LeaveCycleType.CALENDAR_YEAR)
    start_month = serializers.IntegerField(min_value=1, max_value=12, required=False, default=1)
    start_day = serializers.IntegerField(min_value=1, max_value=31, required=False, default=1)
    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            'id',
            'code',
            'name',
            'description',
            'color',
            'is_paid',
            'is_loss_of_pay',
            'annual_entitlement',
            'credit_frequency',
            'credit_day_of_period',
            'prorate_on_join',
            'carry_forward_mode',
            'carry_forward_cap',
            'max_balance',
            'allows_half_day',
            'requires_attachment',
            'attachment_after_days',
            'min_notice_days',
            'max_consecutive_days',
            'allow_past_request',
            'allow_future_request',
            'is_active',
        ]


class LeaveTypeWriteSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    color = serializers.CharField(required=False, allow_blank=True, default='#2563eb')
    is_paid = serializers.BooleanField(required=False, default=True)
    is_loss_of_pay = serializers.BooleanField(required=False, default=False)
    annual_entitlement = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default='0.00')
    credit_frequency = serializers.ChoiceField(choices=LeaveCreditFrequency.choices, default=LeaveCreditFrequency.YEARLY)
    credit_day_of_period = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    prorate_on_join = serializers.BooleanField(required=False, default=True)
    carry_forward_mode = serializers.ChoiceField(choices=LeaveType._meta.get_field('carry_forward_mode').choices, default='NONE')
    carry_forward_cap = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    max_balance = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    allows_half_day = serializers.BooleanField(required=False, default=True)
    requires_attachment = serializers.BooleanField(required=False, default=False)
    attachment_after_days = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    min_notice_days = serializers.IntegerField(required=False, default=0)
    max_consecutive_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    allow_past_request = serializers.BooleanField(required=False, default=False)
    allow_future_request = serializers.BooleanField(required=False, default=True)
    is_active = serializers.BooleanField(required=False, default=True)


class LeavePlanRuleSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    office_location_name = serializers.CharField(source='office_location.name', read_only=True)
    specific_employee_name = serializers.CharField(source='specific_employee.user.full_name', read_only=True)

    class Meta:
        model = LeavePlanRule
        fields = [
            'id',
            'name',
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
        ]


class LeavePlanRuleWriteSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(max_length=255)
    priority = serializers.IntegerField(min_value=0, default=100)
    is_active = serializers.BooleanField(required=False, default=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)
    specific_employee_id = serializers.UUIDField(required=False, allow_null=True)
    employment_type = serializers.CharField(required=False, allow_blank=True, default='')
    designation = serializers.CharField(required=False, allow_blank=True, default='')


class LeavePlanSerializer(serializers.ModelSerializer):
    leave_cycle = LeaveCycleSerializer(read_only=True)
    leave_types = LeaveTypeSerializer(many=True, read_only=True)
    rules = LeavePlanRuleSerializer(many=True, read_only=True)

    class Meta:
        model = LeavePlan
        fields = [
            'id',
            'name',
            'description',
            'is_default',
            'is_active',
            'priority',
            'leave_cycle',
            'leave_types',
            'rules',
            'created_at',
            'modified_at',
        ]


class LeavePlanWriteSerializer(serializers.Serializer):
    leave_cycle_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)
    priority = serializers.IntegerField(min_value=0, default=100)
    leave_types = LeaveTypeWriteSerializer(many=True, required=False, default=list)
    rules = LeavePlanRuleWriteSerializer(many=True, required=False, default=list)


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id',
            'employee',
            'employee_name',
            'leave_type',
            'leave_type_name',
            'start_date',
            'end_date',
            'start_session',
            'end_session',
            'total_units',
            'reason',
            'status',
            'rejection_reason',
            'created_at',
            'modified_at',
        ]


class LeaveRequestCreateSerializer(serializers.Serializer):
    leave_type_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_session = serializers.ChoiceField(choices=LeaveRequest._meta.get_field('start_session').choices, default='FULL_DAY')
    end_session = serializers.ChoiceField(choices=LeaveRequest._meta.get_field('end_session').choices, default='FULL_DAY')
    reason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {'end_date': 'End date must be on or after the start date.'}
            )
        return data


class OnDutyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = OnDutyPolicy
        fields = [
            'id',
            'name',
            'description',
            'is_default',
            'is_active',
            'allow_half_day',
            'allow_time_range',
            'requires_attachment',
            'min_notice_days',
            'allow_past_request',
            'allow_future_request',
            'created_at',
            'modified_at',
        ]


class OnDutyPolicyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)
    allow_half_day = serializers.BooleanField(required=False, default=True)
    allow_time_range = serializers.BooleanField(required=False, default=True)
    requires_attachment = serializers.BooleanField(required=False, default=False)
    min_notice_days = serializers.IntegerField(required=False, default=0)
    allow_past_request = serializers.BooleanField(required=False, default=False)
    allow_future_request = serializers.BooleanField(required=False, default=True)


class OnDutyRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    policy_name = serializers.CharField(source='policy.name', read_only=True)

    class Meta:
        model = OnDutyRequest
        fields = [
            'id',
            'employee',
            'employee_name',
            'policy',
            'policy_name',
            'start_date',
            'end_date',
            'duration_type',
            'start_time',
            'end_time',
            'total_units',
            'purpose',
            'destination',
            'status',
            'rejection_reason',
            'created_at',
            'modified_at',
        ]


class OnDutyRequestCreateSerializer(serializers.Serializer):
    policy_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    duration_type = serializers.ChoiceField(choices=OnDutyRequest._meta.get_field('duration_type').choices, default='FULL_DAY')
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    purpose = serializers.CharField()
    destination = serializers.CharField(required=False, allow_blank=True, default='')
