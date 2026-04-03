from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'kind',
            'title',
            'body',
            'is_read',
            'read_at',
            'created_at',
            'object_id',
        ]
        read_only_fields = fields
