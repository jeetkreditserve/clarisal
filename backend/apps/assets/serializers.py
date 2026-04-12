from rest_framework import serializers

from .models import (
    AssetAssignment,
    AssetCategory,
    AssetCondition,
    AssetIncident,
    AssetItem,
    AssetMaintenance,
)


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class AssetCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['name', 'description', 'is_active']


class AssetItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    current_assignee = serializers.SerializerMethodField()

    class Meta:
        model = AssetItem
        fields = [
            'id', 'name', 'asset_tag', 'serial_number', 'vendor',
            'category', 'category_name', 'purchase_date', 'purchase_cost',
            'warranty_expiry', 'condition', 'lifecycle_status',
            'notes', 'metadata', 'current_assignee', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_current_assignee(self, obj):
        active_assignment = obj.assignments.filter(
            status='ACTIVE'
        ).select_related('employee', 'employee__user').first()
        if active_assignment:
            return {
                'id': str(active_assignment.employee.id),
                'name': active_assignment.employee.user.full_name,
                'employee_code': active_assignment.employee.employee_code,
            }
        return None


class AssetItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetItem
        fields = [
            'name', 'asset_tag', 'serial_number', 'vendor', 'category',
            'purchase_date', 'purchase_cost', 'warranty_expiry',
            'condition', 'notes', 'metadata'
        ]


class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_tag = serializers.CharField(source='asset.asset_tag', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)

    class Meta:
        model = AssetAssignment
        fields = [
            'id', 'asset', 'asset_name', 'asset_tag',
            'employee', 'employee_name', 'employee_code',
            'assigned_at', 'acknowledged_at', 'expected_return_date',
            'returned_at', 'condition_on_issue', 'condition_on_return',
            'status', 'notes'
        ]
        read_only_fields = ['id', 'assigned_at']


class AssetAssignmentWriteSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    expected_return_date = serializers.DateField(required=False, allow_null=True)
    condition_on_issue = serializers.ChoiceField(
        choices=AssetCondition.choices,
        required=False,
        default=AssetCondition.NEW
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class AssetReturnSerializer(serializers.Serializer):
    condition_on_return = serializers.ChoiceField(
        choices=AssetCondition.choices,
        required=False,
        allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)

    class Meta:
        model = AssetMaintenance
        fields = [
            'id', 'asset', 'asset_name', 'maintenance_type',
            'description', 'scheduled_date', 'completed_date',
            'cost', 'vendor', 'notes'
        ]
        read_only_fields = ['id']


class AssetMaintenanceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetMaintenance
        fields = [
            'maintenance_type', 'description', 'scheduled_date',
            'completed_date', 'cost', 'vendor', 'notes'
        ]


class AssetIncidentSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetIncident
        fields = [
            'id', 'asset', 'asset_name', 'employee', 'employee_name',
            'incident_type', 'description', 'reported_at',
            'resolved_at', 'resolution_notes'
        ]
        read_only_fields = ['id', 'reported_at']

    def get_employee_name(self, obj):
        if obj.employee:
            return obj.employee.user.full_name
        return None


class AssetIncidentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetIncident
        fields = [
            'incident_type', 'description', 'resolved_at', 'resolution_notes'
        ]
