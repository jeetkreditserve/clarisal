from rest_framework import serializers

from .models import AccountType, User
from .workspaces import get_default_route, get_workspace_state


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class WorkspaceSwitchSerializer(serializers.Serializer):
    workspace_kind = serializers.ChoiceField(choices=['ADMIN', 'EMPLOYEE'])
    organisation_id = serializers.UUIDField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    organisation_id = serializers.SerializerMethodField()
    organisation_name = serializers.SerializerMethodField()
    organisation_status = serializers.SerializerMethodField()
    organisation_onboarding_stage = serializers.SerializerMethodField()
    organisation_access_state = serializers.SerializerMethodField()
    active_workspace_kind = serializers.SerializerMethodField()
    default_route = serializers.SerializerMethodField()
    has_control_tower_access = serializers.SerializerMethodField()
    has_org_admin_access = serializers.SerializerMethodField()
    has_employee_access = serializers.SerializerMethodField()
    admin_organisations = serializers.SerializerMethodField()
    employee_workspaces = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'account_type',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'organisation_id',
            'organisation_name',
            'organisation_status',
            'organisation_onboarding_stage',
            'organisation_access_state',
            'active_workspace_kind',
            'default_route',
            'has_control_tower_access',
            'has_org_admin_access',
            'has_employee_access',
            'admin_organisations',
            'employee_workspaces',
            'is_active',
        ]
        read_only_fields = fields

    def _state(self, obj):
        request = self.context.get('request')
        return get_workspace_state(obj, request)

    def _current_org(self, obj):
        state = self._state(obj)
        if state.active_kind == 'ADMIN' and state.active_admin_membership:
            return state.active_admin_membership.organisation
        if state.active_kind == 'EMPLOYEE' and state.active_employee:
            return state.active_employee.organisation
        if state.active_admin_membership:
            return state.active_admin_membership.organisation
        if state.active_employee:
            return state.active_employee.organisation
        return None

    def get_organisation_id(self, obj):
        organisation = self._current_org(obj)
        return str(organisation.id) if organisation else None

    def get_organisation_name(self, obj):
        organisation = self._current_org(obj)
        return organisation.name if organisation else None

    def get_organisation_status(self, obj):
        organisation = self._current_org(obj)
        return organisation.status if organisation else None

    def get_organisation_onboarding_stage(self, obj):
        organisation = self._current_org(obj)
        return organisation.onboarding_stage if organisation else None

    def get_organisation_access_state(self, obj):
        organisation = self._current_org(obj)
        return organisation.access_state if organisation else None

    def get_active_workspace_kind(self, obj):
        if obj.account_type == AccountType.CONTROL_TOWER:
            return 'CONTROL_TOWER'
        return self._state(obj).active_kind

    def get_default_route(self, obj):
        return get_default_route(obj, self.context.get('request'))

    def get_has_control_tower_access(self, obj):
        return obj.account_type == AccountType.CONTROL_TOWER

    def get_has_org_admin_access(self, obj):
        return bool(self._state(obj).admin_memberships)

    def get_has_employee_access(self, obj):
        return bool(self._state(obj).employee_records)

    def get_admin_organisations(self, obj):
        state = self._state(obj)
        results = []
        for membership in state.admin_memberships:
            organisation = membership.organisation
            results.append(
                {
                    'organisation_id': str(organisation.id),
                    'organisation_name': organisation.name,
                    'status': organisation.status,
                    'access_state': organisation.access_state,
                    'onboarding_stage': organisation.onboarding_stage,
                    'is_active_context': bool(
                        state.active_admin_membership and state.active_admin_membership.id == membership.id
                    ),
                }
            )
        return results

    def get_employee_workspaces(self, obj):
        state = self._state(obj)
        results = []
        for employee in state.employee_records:
            organisation = employee.organisation
            results.append(
                {
                    'employee_id': str(employee.id),
                    'employee_code': employee.employee_code,
                    'organisation_id': str(organisation.id),
                    'organisation_name': organisation.name,
                    'employee_status': employee.status,
                    'is_active_context': bool(state.active_employee and state.active_employee.id == employee.id),
                }
            )
        return results
