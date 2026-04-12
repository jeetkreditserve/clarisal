from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.models import AccountType, User
from apps.departments.models import Department
from apps.employees.models import Employee
from apps.locations.models import OfficeLocation
from apps.organisations.models import Organisation, OrganisationMembership

from .models import (
    AccessPermission,
    AccessRole,
    AccessRoleAssignment,
    AccessRolePermission,
    AccessRoleScope,
    AccessScope,
    DataScopeKind,
)


class AccessPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPermission
        fields = ['id', 'code', 'label', 'domain', 'resource', 'action', 'description']


class AccessRoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = AccessRole
        fields = ['id', 'code', 'scope', 'name', 'description', 'is_system', 'permissions']

    def get_permissions(self, obj):
        return sorted(obj.role_permissions.values_list('permission__code', flat=True))


class AccessRoleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=160),
        allow_empty=False,
    )

    def validate_permission_codes(self, value):
        organisation: Organisation | None = self.context.get('organisation')
        domain = 'org' if organisation is not None else 'ct'
        permissions = AccessPermission.objects.filter(code__in=value, domain=domain, is_active=True)
        found_codes = set(permissions.values_list('code', flat=True))
        missing = sorted(set(value) - found_codes)
        if missing:
            raise serializers.ValidationError(f'Unknown or out-of-scope permissions: {", ".join(missing)}')
        return value

    def save(self, **kwargs):
        organisation: Organisation | None = kwargs.get('organisation')
        actor = kwargs.get('actor')
        scope = AccessRoleScope.ORGANISATION if organisation is not None else AccessRoleScope.CONTROL_TOWER
        prefix = 'ORG_CUSTOM' if organisation is not None else 'CT_CUSTOM'
        code = self._build_unique_code(prefix, self.validated_data['name'], organisation=organisation)
        with transaction.atomic():
            role = AccessRole.objects.create(
                organisation=organisation,
                code=code,
                scope=scope,
                name=self.validated_data['name'],
                description=self.validated_data.get('description', ''),
                is_system=False,
                is_active=True,
                created_by=actor,
                modified_by=actor,
            )
            permissions = AccessPermission.objects.filter(code__in=self.validated_data['permission_codes'])
            AccessRolePermission.objects.bulk_create(
                [
                    AccessRolePermission(
                        role=role,
                        permission=permission,
                        created_by=actor,
                        modified_by=actor,
                    )
                    for permission in permissions
                ]
            )
        return role

    @staticmethod
    def _build_unique_code(prefix: str, name: str, *, organisation: Organisation | None) -> str:
        slug = slugify(name).replace('-', '_').upper() or 'ROLE'
        base = f'{prefix}_{slug}'[:100]
        candidate = base
        index = 2
        queryset = AccessRole.objects.filter(organisation=organisation)
        while queryset.filter(code=candidate).exists():
            suffix = f'_{index}'
            candidate = f'{base[:120 - len(suffix)]}{suffix}'
            index += 1
        return candidate


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
        organisation: Organisation | None = self.context.get('organisation')
        user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user').run_validation(attrs['user_id'])
        if organisation is None:
            role = AccessRole.objects.filter(
                organisation__isnull=True,
                code=attrs['role_code'],
                scope=AccessRoleScope.CONTROL_TOWER,
                is_active=True,
            ).first()
            if role is None:
                raise serializers.ValidationError({'role_code': 'Select a valid Control Tower access role.'})
            if user.account_type != AccountType.CONTROL_TOWER:
                raise serializers.ValidationError({'user_id': 'The selected user is not a Control Tower user.'})
        else:
            role = (
                AccessRole.objects.filter(
                    Q(organisation__isnull=True) | Q(organisation=organisation),
                    code=attrs['role_code'],
                    scope=AccessRoleScope.ORGANISATION,
                    is_active=True,
                )
                .order_by('-organisation_id')
                .first()
            )
            if role is None:
                raise serializers.ValidationError({'role_code': 'Select a valid organisation access role.'})
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
                    queryset=Organisation.objects.filter(id=organisation.id) if organisation is not None else Organisation.objects.all(),
                ).run_validation(scope_payload['organisation_id'])
            if scope_payload.get('office_location_id') and organisation is not None:
                resolved['office_location'] = serializers.PrimaryKeyRelatedField(
                    queryset=OfficeLocation.objects.filter(organisation=organisation),
                ).run_validation(scope_payload['office_location_id'])
            if scope_payload.get('department_id') and organisation is not None:
                resolved['department'] = serializers.PrimaryKeyRelatedField(
                    queryset=Department.objects.filter(organisation=organisation),
                ).run_validation(scope_payload['department_id'])
            if scope_payload.get('employee_id') and organisation is not None:
                resolved['employee'] = serializers.PrimaryKeyRelatedField(
                    queryset=Employee.objects.filter(organisation=organisation),
                ).run_validation(scope_payload['employee_id'])
            validated_scopes.append(resolved)

        attrs['user'] = user
        attrs['role'] = role
        attrs['validated_scopes'] = validated_scopes
        return attrs

    def save(self, **kwargs):
        organisation: Organisation | None = kwargs.get('organisation')
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


class AccessSimulationSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    employee_id = serializers.UUIDField(required=False, allow_null=True)
