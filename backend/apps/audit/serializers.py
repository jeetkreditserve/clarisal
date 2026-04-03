from rest_framework import serializers

from apps.accounts.models import UserRole

from .services import sanitize_audit_payload
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()
    actor_name = serializers.SerializerMethodField()
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    payload = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    target_label = serializers.SerializerMethodField()
    payload_summary = serializers.SerializerMethodField()
    ip_address = serializers.SerializerMethodField()
    user_agent = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor_email',
            'actor_name',
            'organisation_name',
            'action',
            'module',
            'target_type',
            'target_id',
            'target_label',
            'payload',
            'payload_summary',
            'ip_address',
            'user_agent',
            'created_at',
        ]

    def get_module(self, obj):
        if '.' in obj.action:
            return obj.action.split('.', 1)[0]
        return obj.action

    def _is_ct_view(self):
        request = self.context.get('request')
        return bool(
            request
            and getattr(request, 'user', None)
            and request.user.is_authenticated
            and request.user.account_type == 'CONTROL_TOWER'
        )

    def _should_mask_employee_actor(self, obj):
        return self._is_ct_view() and getattr(obj.actor, 'role', None) == UserRole.EMPLOYEE

    def get_actor_name(self, obj):
        if self._should_mask_employee_actor(obj):
            return 'Employee user'
        if obj.actor is None:
            return None
        return obj.actor.full_name

    def get_actor_email(self, obj):
        if self._should_mask_employee_actor(obj):
            return None
        if obj.actor is None:
            return None
        return obj.actor.email

    def get_payload(self, obj):
        return sanitize_audit_payload(obj.payload or {})

    def get_ip_address(self, obj):
        if self._should_mask_employee_actor(obj):
            return None
        return obj.ip_address

    def get_user_agent(self, obj):
        if self._should_mask_employee_actor(obj):
            return None
        return obj.user_agent or None

    def get_target_label(self, obj):
        payload = self.get_payload(obj)
        candidate_keys = ['name', 'title', 'label', 'full_name', 'email', 'status']
        for key in candidate_keys:
            value = payload.get(key)
            if value:
                return str(value)
        if obj.target_type and obj.target_id:
            return f'{obj.target_type} • {obj.target_id}'
        if obj.target_type:
            return obj.target_type
        return ''

    def get_payload_summary(self, obj):
        payload = self.get_payload(obj)
        summary_parts = []
        for key, value in payload.items():
            if value in ('', None, [], {}):
                continue
            summary_parts.append(f'{key}: {value}')
            if len(summary_parts) == 3:
                break
        return ' • '.join(summary_parts)
