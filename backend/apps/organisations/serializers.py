from rest_framework import serializers
from apps.accounts.models import User
from .models import Organisation, OrganisationStateTransition


class OrganisationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'slug', 'status', 'licence_count', 'created_at']


class StateTransitionSerializer(serializers.ModelSerializer):
    transitioned_by_email = serializers.EmailField(source='transitioned_by.email', read_only=True)

    class Meta:
        model = OrganisationStateTransition
        fields = ['id', 'from_status', 'to_status', 'note', 'transitioned_by_email', 'created_at']


class OrganisationDetailSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    state_transitions = StateTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'slug', 'status', 'licence_count',
            'address', 'phone', 'email', 'logo_url',
            'created_by_email', 'created_at', 'updated_at',
            'state_transitions',
        ]


class CreateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    licence_count = serializers.IntegerField(min_value=1)


class UpdateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class LicenceUpdateSerializer(serializers.Serializer):
    licence_count = serializers.IntegerField(min_value=0)


class OrgAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'is_onboarding_email_sent']


class CTDashboardStatsSerializer(serializers.Serializer):
    total_organisations = serializers.IntegerField()
    active_organisations = serializers.IntegerField()
    pending_organisations = serializers.IntegerField()
    paid_organisations = serializers.IntegerField()
    suspended_organisations = serializers.IntegerField()
    total_employees = serializers.IntegerField()
