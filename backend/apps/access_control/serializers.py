from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.departments.models import Department
from apps.employees.models import Employee
from apps.locations.models import OfficeLocation
from apps.organisations.models import Organisation, OrganisationMembership

from .models import AccessPermission, AccessRole, AccessRoleAssignment, AccessRoleScope, AccessScope, DataScopeKind


class AccessPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPermission
        fields = ['code', 'label', 'description']


class AccessRoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = AccessRole
        fields = ['id', 'code', 'scope', 'name', 'description', 'is_system', 'permissions']

    def get_permissions(self, obj):
        return list(obj.role_permissions.values_list('permission__code', flat=True))


class AccessScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessScope
        fields = [
            'id',
            'scope_kind',
            'organisation_id',
            'department_id',
            'office_location_id',
            'employee_id',
            'value_text',
        ]

    def _get_label(self, obj: AccessScope) -> str:
        if obj.scope_kind == DataScopeKind.SELECTED_OFFICE_LOCATIONS and obj.office_location is not None:
            return str(obj.office_location.name)
        if obj.scope_kind == DataScopeKind.SELECTED_EMPLOYEES and obj.employee is not None:
            return str(obj.employee.user.full_name)
        if obj.scope_kind == DataScopeKind.SELECTED_ORGANISATIONS and obj.organisation is not None:
            return str(obj.organisation.name)
        if obj.scope_kind == DataScopeKind.SELECTED_DEPARTMENTS and obj.department is not None:
            return str(obj.department.name)
        return obj.value_text or obj.get_scope_kind_display()

    def to_representation(self, instance: AccessScope) -> dict[str, Any]:
        data = super().to_representation(instance)
        data['label'] = self._get_label(instance)
        return data


class AccessRoleAssignmentSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    role_code = serializers.CharField(source='role.code', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    scopes = AccessScopeSerializer(many=True, read_only=True)

    class Meta:
        model = AccessRoleAssignment
        fields = [
            'id',
            'user_id',
            'user_email',
            'user_full_name',
            'role_code',
            'role_name',
            'is_active',
            'scopes',
        ]


class AccessScopeWriteSerializer(serializers.Serializer):
    scope_kind = serializers.ChoiceField(choices=DataScopeKind.choices)
    organisation_id = serializers.UUIDField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    office_location_id = serializers.UUIDField(required=False, allow_null=True)
    employee_id = serializers.UUIDField(required=False, allow_null=True)
    value_text = serializers.CharField(required=False, allow_blank=True, default='')


class AccessRoleAssignmentWriteSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role_code = serializers.CharField()
    is_active = serializers.BooleanField(default=True)
    scopes = AccessScopeWriteSerializer(many=True, required=False, default=list)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        organisation: Organisation = self.context['organisation']
        user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user').run_validation(attrs['user_id'])
        role = serializers.PrimaryKeyRelatedField(
            queryset=AccessRole.objects.filter(scope=AccessRoleScope.ORGANISATION, is_active=True),
            source='role',
        ).run_validation(
            AccessRole.objects.filter(code=attrs['role_code']).values_list('id', flat=True).first()
        )
        belongs_to_org = OrganisationMembership.objects.filter(user=user, organisation=organisation).exists() or Employee.objects.filter(
            user=user,
            organisation=organisation,
        ).exists()
        if not belongs_to_org:
            raise serializers.ValidationError({'user_id': 'The selected user does not belong to this organisation.'})

        validated_scopes: list[dict[str, Any]] = []
        for scope_payload in attrs.get('scopes', []):
            scope_kind = scope_payload['scope_kind']
            resolved = {
                'scope_kind': scope_kind,
                'value_text': scope_payload.get('value_text', ''),
                'organisation': None,
                'department': None,
                'office_location': None,
                'employee': None,
            }
            if scope_payload.get('organisation_id'):
                resolved['organisation'] = serializers.PrimaryKeyRelatedField(
                    queryset=Organisation.objects.filter(id=organisation.id),
                ).run_validation(scope_payload['organisation_id'])
            if scope_payload.get('office_location_id'):
                resolved['office_location'] = serializers.PrimaryKeyRelatedField(
                    queryset=OfficeLocation.objects.filter(organisation=organisation),
                ).run_validation(scope_payload['office_location_id'])
            if scope_payload.get('department_id'):
                resolved['department'] = serializers.PrimaryKeyRelatedField(
                    queryset=Department.objects.filter(organisation=organisation),
                ).run_validation(scope_payload['department_id'])
            if scope_payload.get('employee_id'):
                resolved['employee'] = serializers.PrimaryKeyRelatedField(
                    queryset=Employee.objects.filter(organisation=organisation),
                ).run_validation(scope_payload['employee_id'])
            validated_scopes.append(resolved)

        attrs['user'] = user
        attrs['role'] = role
        attrs['validated_scopes'] = validated_scopes
        return attrs

    def save(self, **kwargs):
        organisation: Organisation = kwargs['organisation']
        actor = kwargs.get('actor')
        assignment, _ = AccessRoleAssignment.objects.update_or_create(
            user=self.validated_data['user'],
            role=self.validated_data['role'],
            organisation=organisation,
            defaults={'is_active': self.validated_data['is_active']},
        )
        assignment.scopes.all().delete()
        for scope_payload in self.validated_data['validated_scopes']:
            AccessScope.objects.create(
                assignment=assignment,
                scope_kind=scope_payload['scope_kind'],
                organisation=scope_payload['organisation'],
                department=scope_payload['department'],
                office_location=scope_payload['office_location'],
                employee=scope_payload['employee'],
                value_text=scope_payload['value_text'],
                created_by=actor,
                modified_by=actor,
            )
        return assignment
