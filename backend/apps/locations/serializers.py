from rest_framework import serializers

from apps.organisations.serializers import OrganisationAddressSerializer

from .models import OfficeLocation


class LocationSerializer(serializers.ModelSerializer):
    organisation_address = OrganisationAddressSerializer(read_only=True)
    organisation_address_id = serializers.UUIDField(source='organisation_address.id', read_only=True)

    class Meta:
        model = OfficeLocation
        fields = [
            'id',
            'name',
            'organisation_address',
            'organisation_address_id',
            'address',
            'city',
            'state',
            'country',
            'pincode',
            'is_remote',
            'is_active',
            'created_at',
            'modified_at',
        ]


class LocationCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    organisation_address_id = serializers.UUIDField()
    is_remote = serializers.BooleanField(required=False, default=False)
