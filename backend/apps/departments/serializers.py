from rest_framework import serializers

from .models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    parent_department_id = serializers.UUIDField(source='parent_department.id', read_only=True)
    parent_department_name = serializers.CharField(source='parent_department.name', read_only=True)

    class Meta:
        model = Department
        fields = [
            'id',
            'name',
            'description',
            'parent_department_id',
            'parent_department_name',
            'is_active',
            'created_at',
            'modified_at',
        ]


class DepartmentCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    parent_department_id = serializers.UUIDField(required=False, allow_null=True)
