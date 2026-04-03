from django.urls import reverse
from rest_framework import serializers

from .models import BiometricDevice, BiometricProtocol, BiometricSyncLog


class BiometricDeviceSerializer(serializers.ModelSerializer):
    location_id = serializers.UUIDField(read_only=True)
    secret_preview = serializers.SerializerMethodField()
    endpoint_path = serializers.SerializerMethodField()

    class Meta:
        model = BiometricDevice
        fields = [
            'id',
            'name',
            'device_serial',
            'protocol',
            'ip_address',
            'port',
            'auth_username',
            'oauth_client_id',
            'location_id',
            'secret_preview',
            'endpoint_path',
            'is_active',
            'last_sync_at',
            'created_at',
        ]
        read_only_fields = ['id', 'last_sync_at', 'created_at']

    def get_secret_preview(self, obj):
        return obj.get_api_key_preview() if obj.api_key_encrypted else ''

    def get_endpoint_path(self, obj):
        if obj.protocol == BiometricProtocol.ZK_ADMS:
            return reverse('biometric-adms-cdata')
        if obj.protocol == BiometricProtocol.ESSL_EBIOSERVER:
            return reverse('biometric-essl-ebioserver-events', kwargs={'device_id': obj.id})
        return ''


class BiometricDeviceWriteSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    oauth_client_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    location_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = BiometricDevice
        fields = [
            'name',
            'device_serial',
            'protocol',
            'ip_address',
            'port',
            'auth_username',
            'location_id',
            'is_active',
            'api_key',
            'oauth_client_id',
            'oauth_client_secret',
        ]

    def validate(self, attrs):
        protocol = attrs.get('protocol') or getattr(self.instance, 'protocol', '')
        device_serial = attrs.get('device_serial') if 'device_serial' in attrs else getattr(self.instance, 'device_serial', '')
        ip_address = attrs.get('ip_address') if 'ip_address' in attrs else getattr(self.instance, 'ip_address', None)
        auth_username = attrs.get('auth_username') if 'auth_username' in attrs else getattr(self.instance, 'auth_username', '')
        oauth_client_id = attrs.get('oauth_client_id') if 'oauth_client_id' in attrs else getattr(self.instance, 'oauth_client_id', '')
        api_key = attrs.get('api_key', '')
        oauth_client_secret = attrs.get('oauth_client_secret', '')

        existing_api_key = getattr(self.instance, 'api_key_encrypted', '')
        existing_oauth_secret = getattr(self.instance, 'oauth_client_secret_encrypted', '')

        if protocol == BiometricProtocol.ZK_ADMS and not device_serial:
            raise serializers.ValidationError({'device_serial': 'Device serial is required for ZK ADMS push devices.'})
        if protocol in {BiometricProtocol.MATRIX_COSEC, BiometricProtocol.SUPREMA_BIOSTAR, BiometricProtocol.HIKVISION_ISAPI} and not ip_address:
            raise serializers.ValidationError({'ip_address': 'IP address is required for pull protocol devices.'})
        if protocol == BiometricProtocol.ESSL_EBIOSERVER and not (api_key or existing_api_key):
            raise serializers.ValidationError({'api_key': 'eSSL eBioserver requires a shared secret.'})
        if protocol == BiometricProtocol.MATRIX_COSEC and not (api_key or existing_api_key):
            raise serializers.ValidationError({'api_key': 'Matrix COSEC requires an API key.'})
        if protocol == BiometricProtocol.HIKVISION_ISAPI:
            if not auth_username:
                raise serializers.ValidationError({'auth_username': 'HikVision requires a username.'})
            if not (api_key or existing_api_key):
                raise serializers.ValidationError({'api_key': 'HikVision requires a password.'})
        if protocol == BiometricProtocol.SUPREMA_BIOSTAR:
            if not oauth_client_id:
                raise serializers.ValidationError({'oauth_client_id': 'Suprema requires a login id.'})
            if not (oauth_client_secret or existing_oauth_secret):
                raise serializers.ValidationError({'oauth_client_secret': 'Suprema requires a password.'})  # nosec B105
        return attrs

    def create(self, validated_data):
        api_key = validated_data.pop('api_key', '')
        oauth_client_secret = validated_data.pop('oauth_client_secret', '')
        location_id = validated_data.pop('location_id', None)
        device = BiometricDevice(**validated_data)
        if location_id is not None:
            device.location_id = location_id
        if api_key:
            device.set_api_key(api_key)
        if oauth_client_secret:
            device.set_oauth_client_secret(oauth_client_secret)
        device.save()
        return device

    def update(self, instance, validated_data):
        api_key = validated_data.pop('api_key', '')
        oauth_client_secret = validated_data.pop('oauth_client_secret', '')
        location_id = validated_data.pop('location_id', serializers.empty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if location_id is not serializers.empty:
            instance.location_id = location_id
        if api_key:
            instance.set_api_key(api_key)
        if oauth_client_secret:
            instance.set_oauth_client_secret(oauth_client_secret)
        instance.save()
        return instance


class BiometricSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricSyncLog
        fields = [
            'id',
            'synced_at',
            'records_fetched',
            'records_processed',
            'records_skipped',
            'errors',
            'success',
        ]
        read_only_fields = fields
