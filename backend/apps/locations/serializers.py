from rest_framework import serializers

from .models import OfficeLocation


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeLocation
        fields = [
            'id',
            'name',
            'address',
            'city',
            'state',
            'country',
            'pincode',
            'is_active',
            'created_at',
            'updated_at',
        ]


class LocationCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(required=False, allow_blank=True, default='')
    city = serializers.CharField(required=False, allow_blank=True, default='')
    state = serializers.CharField(required=False, allow_blank=True, default='')
    country = serializers.CharField(required=False, allow_blank=True, default='')
    pincode = serializers.CharField(required=False, allow_blank=True, default='')
