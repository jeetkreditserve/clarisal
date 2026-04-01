from rest_framework import serializers

from .models import Notice, NoticeAudienceType, NoticeStatus


class NoticeSerializer(serializers.ModelSerializer):
    department_ids = serializers.SerializerMethodField()
    office_location_ids = serializers.SerializerMethodField()
    employee_ids = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = [
            'id',
            'title',
            'body',
            'category',
            'audience_type',
            'status',
            'is_sticky',
            'scheduled_for',
            'published_at',
            'expires_at',
            'department_ids',
            'office_location_ids',
            'employee_ids',
            'created_at',
            'modified_at',
        ]

    def get_department_ids(self, obj):
        return [str(item.id) for item in obj.departments.all()]

    def get_office_location_ids(self, obj):
        return [str(item.id) for item in obj.office_locations.all()]

    def get_employee_ids(self, obj):
        return [str(item.id) for item in obj.employees.all()]


class NoticeWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    category = serializers.ChoiceField(choices=Notice._meta.get_field('category').choices, required=False, default='GENERAL')
    audience_type = serializers.ChoiceField(choices=Notice._meta.get_field('audience_type').choices)
    status = serializers.ChoiceField(choices=Notice._meta.get_field('status').choices, required=False, default='DRAFT')
    is_sticky = serializers.BooleanField(required=False, default=False)
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    department_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    office_location_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    employee_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)

    def validate(self, attrs):
        audience_type = attrs.get('audience_type')
        status = attrs.get('status', NoticeStatus.DRAFT)
        scheduled_for = attrs.get('scheduled_for')
        expires_at = attrs.get('expires_at')
        department_ids = attrs.get('department_ids', [])
        office_location_ids = attrs.get('office_location_ids', [])
        employee_ids = attrs.get('employee_ids', [])

        if audience_type == NoticeAudienceType.DEPARTMENTS and not department_ids:
            raise serializers.ValidationError({'department_ids': 'Select at least one department for this audience.'})
        if audience_type == NoticeAudienceType.OFFICE_LOCATIONS and not office_location_ids:
            raise serializers.ValidationError({'office_location_ids': 'Select at least one office location for this audience.'})
        if audience_type == NoticeAudienceType.SPECIFIC_EMPLOYEES and not employee_ids:
            raise serializers.ValidationError({'employee_ids': 'Select at least one employee for this audience.'})

        if status == NoticeStatus.SCHEDULED and not scheduled_for:
            raise serializers.ValidationError({'scheduled_for': 'A scheduled notice must include a publish time.'})
        if expires_at and scheduled_for and expires_at <= scheduled_for:
            raise serializers.ValidationError({'expires_at': 'Expiry must be later than the scheduled publish time.'})

        return attrs
