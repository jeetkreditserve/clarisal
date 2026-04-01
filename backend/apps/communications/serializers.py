from rest_framework import serializers

from .models import Notice


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
            'audience_type',
            'status',
            'scheduled_for',
            'published_at',
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
    audience_type = serializers.ChoiceField(choices=Notice._meta.get_field('audience_type').choices)
    status = serializers.ChoiceField(choices=Notice._meta.get_field('status').choices, required=False, default='DRAFT')
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    department_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    office_location_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    employee_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
