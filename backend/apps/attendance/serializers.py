from rest_framework import serializers

from .models import (
    AttendanceDay,
    AttendanceImportJob,
    AttendancePolicy,
    AttendanceRegularizationRequest,
    AttendanceSourceConfig,
    Shift,
    ShiftAssignment,
)


class AttendanceImportJobSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    normalized_file_available = serializers.SerializerMethodField()
    error_preview = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceImportJob
        fields = [
            'id',
            'mode',
            'status',
            'original_filename',
            'uploaded_by_email',
            'total_rows',
            'valid_rows',
            'error_rows',
            'posted_rows',
            'normalized_file_available',
            'error_preview',
            'created_at',
            'modified_at',
        ]

    def get_normalized_file_available(self, obj):
        return obj.mode == 'PUNCH_SHEET' and obj.valid_rows > 0

    def get_error_preview(self, obj):
        rows = obj.rows.filter(status='ERROR').order_by('row_number')[:5]
        return [
            {
                'row_number': row.row_number,
                'employee_code': row.employee_code,
                'message': row.error_message,
            }
            for row in rows
        ]


class AttendancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendancePolicy
        fields = [
            'id',
            'name',
            'timezone_name',
            'default_start_time',
            'default_end_time',
            'grace_minutes',
            'full_day_min_minutes',
            'half_day_min_minutes',
            'overtime_after_minutes',
            'week_off_days',
            'allow_web_punch',
            'restrict_by_ip',
            'allowed_ip_ranges',
            'restrict_by_geo',
            'allowed_geo_sites',
            'is_default',
            'is_active',
            'created_at',
            'modified_at',
        ]


class AttendancePolicyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=False)
    timezone_name = serializers.CharField(required=False)
    default_start_time = serializers.TimeField(required=False)
    default_end_time = serializers.TimeField(required=False)
    grace_minutes = serializers.IntegerField(required=False, min_value=0)
    full_day_min_minutes = serializers.IntegerField(required=False, min_value=1)
    half_day_min_minutes = serializers.IntegerField(required=False, min_value=1)
    overtime_after_minutes = serializers.IntegerField(required=False, min_value=1)
    week_off_days = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False)
    allow_web_punch = serializers.BooleanField(required=False)
    restrict_by_ip = serializers.BooleanField(required=False)
    allowed_ip_ranges = serializers.ListField(child=serializers.CharField(), required=False)
    restrict_by_geo = serializers.BooleanField(required=False)
    allowed_geo_sites = serializers.ListField(child=serializers.JSONField(), required=False)
    is_default = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            'id',
            'name',
            'start_time',
            'end_time',
            'grace_minutes',
            'full_day_min_minutes',
            'half_day_min_minutes',
            'overtime_after_minutes',
            'is_overnight',
            'is_active',
            'created_at',
            'modified_at',
        ]


class ShiftWriteSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    start_time = serializers.TimeField(required=True)
    end_time = serializers.TimeField(required=True)
    grace_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    full_day_min_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    half_day_min_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    overtime_after_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    is_overnight = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True)

    class Meta:
        model = ShiftAssignment
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'employee_code',
            'shift',
            'shift_name',
            'start_date',
            'end_date',
            'is_active',
            'created_at',
            'modified_at',
        ]


class ShiftAssignmentWriteSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)


class AttendanceDaySerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True, allow_null=True)
    policy_name = serializers.CharField(source='policy.name', read_only=True, allow_null=True)

    class Meta:
        model = AttendanceDay
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'employee_code',
            'attendance_date',
            'status',
            'source',
            'check_in_at',
            'check_out_at',
            'worked_minutes',
            'overtime_minutes',
            'late_minutes',
            'paid_fraction',
            'leave_fraction',
            'on_duty_fraction',
            'is_holiday',
            'is_week_off',
            'is_late',
            'needs_regularization',
            'raw_punch_count',
            'note',
            'metadata',
            'shift_name',
            'policy_name',
            'created_at',
            'modified_at',
        ]


class AttendanceDayOverrideSerializer(serializers.Serializer):
    check_in = serializers.TimeField(required=False, allow_null=True)
    check_out = serializers.TimeField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class AttendanceRegularizationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    approval_run_id = serializers.UUIDField(source='approval_run.id', read_only=True, allow_null=True)

    class Meta:
        model = AttendanceRegularizationRequest
        fields = [
            'id',
            'attendance_day',
            'attendance_date',
            'employee_name',
            'employee_code',
            'requested_check_in_at',
            'requested_check_out_at',
            'reason',
            'status',
            'rejection_reason',
            'approval_run_id',
            'created_at',
            'modified_at',
        ]


class AttendanceSourceConfigSerializer(serializers.ModelSerializer):
    configuration = serializers.SerializerMethodField()
    api_key_masked = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSourceConfig
        fields = [
            'id',
            'name',
            'kind',
            'configuration',
            'api_key_masked',
            'is_active',
            'last_error',
            'created_at',
            'modified_at',
        ]

    def get_api_key_masked(self, obj):
        from .services import get_source_api_key_preview

        return get_source_api_key_preview(obj) if obj.kind == 'API' else ''

    def get_configuration(self, obj):
        configuration = dict(obj.configuration or {})
        configuration.pop('api_key_hash', None)
        configuration.pop('api_key_encrypted', None)
        return configuration


class AttendanceSourceConfigWriteSerializer(serializers.Serializer):
    name = serializers.CharField()
    kind = serializers.ChoiceField(choices=AttendanceSourceConfig._meta.get_field('kind').choices)  # type: ignore[arg-type]
    configuration = serializers.JSONField(required=False)
    is_active = serializers.BooleanField(required=False, default=True)
    rotate_api_key = serializers.BooleanField(required=False, default=False)


class AttendanceSourcePunchItemSerializer(serializers.Serializer):
    employee_code = serializers.CharField()
    punch_at = serializers.CharField()
    action_type = serializers.CharField(required=False, allow_blank=True)
    remote_ip = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)
    external_reference = serializers.CharField(required=False, allow_blank=True)
    batch_id = serializers.CharField(required=False, allow_blank=True)


class AttendanceSourceIngestSerializer(serializers.Serializer):
    punches = AttendanceSourcePunchItemSerializer(many=True)


class AttendancePunchWriteSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(required=False, allow_null=True, max_digits=9, decimal_places=6)


class AttendanceRegularizationWriteSerializer(serializers.Serializer):
    attendance_date = serializers.DateField()
    requested_check_in = serializers.TimeField(required=False, allow_null=True)
    requested_check_out = serializers.TimeField(required=False, allow_null=True)
    reason = serializers.CharField()


class AttendanceRegularizationUpdateSerializer(serializers.Serializer):
    requested_check_in = serializers.TimeField(required=False, allow_null=True)
    requested_check_out = serializers.TimeField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=False)
