from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    module = serializers.SerializerMethodField()
    target_label = serializers.SerializerMethodField()
    payload_summary = serializers.SerializerMethodField()

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

    def get_target_label(self, obj):
        payload = obj.payload or {}
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
        payload = obj.payload or {}
        summary_parts = []
        for key, value in payload.items():
            if value in ('', None, [], {}):
                continue
            summary_parts.append(f'{key}: {value}')
            if len(summary_parts) == 3:
                break
        return ' • '.join(summary_parts)
