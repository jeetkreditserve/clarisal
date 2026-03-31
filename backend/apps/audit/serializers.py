from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor_email',
            'organisation_name',
            'action',
            'target_type',
            'target_id',
            'payload',
            'ip_address',
            'user_agent',
            'created_at',
        ]
