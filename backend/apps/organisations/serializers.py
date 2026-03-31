from rest_framework import serializers
from .models import (
    LicenceBatchLifecycleState,
    LicenceBatchPaymentStatus,
    Organisation,
    OrganisationLicenceBatch,
    OrganisationLifecycleEvent,
    OrganisationLicenceLedger,
    OrganisationMembership,
    OrganisationStateTransition,
)


class OrganisationListSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    licence_count = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = [
            'id',
            'name',
            'slug',
            'status',
            'status_label',
            'billing_status',
            'access_state',
            'onboarding_stage',
            'licence_count',
            'created_at',
        ]

    def get_licence_count(self, obj):
        from .services import get_org_licence_summary

        return get_org_licence_summary(obj)['active_paid_quantity']


class StateTransitionSerializer(serializers.ModelSerializer):
    transitioned_by_email = serializers.EmailField(source='transitioned_by.email', read_only=True)

    class Meta:
        model = OrganisationStateTransition
        fields = ['id', 'from_status', 'to_status', 'note', 'transitioned_by_email', 'created_at']


class LifecycleEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = OrganisationLifecycleEvent
        fields = ['id', 'event_type', 'actor_email', 'payload', 'created_at']


class LicenceLedgerEntrySerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = OrganisationLicenceLedger
        fields = ['id', 'delta', 'reason', 'note', 'effective_from', 'created_by_email', 'created_at']


class LicenceBatchSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    paid_by_email = serializers.EmailField(source='paid_by.email', read_only=True)
    lifecycle_state = serializers.SerializerMethodField()

    class Meta:
        model = OrganisationLicenceBatch
        fields = [
            'id',
            'quantity',
            'price_per_licence_per_month',
            'start_date',
            'end_date',
            'billing_months',
            'total_amount',
            'payment_status',
            'lifecycle_state',
            'note',
            'created_by_email',
            'paid_by_email',
            'paid_at',
            'created_at',
            'updated_at',
        ]

    def get_lifecycle_state(self, obj):
        from .services import get_batch_lifecycle_state

        return get_batch_lifecycle_state(obj)


class LicenceCapacitySummarySerializer(serializers.Serializer):
    active_paid_quantity = serializers.IntegerField()
    allocated = serializers.IntegerField()
    available = serializers.IntegerField()
    overage = serializers.IntegerField()
    has_overage = serializers.BooleanField()
    utilisation_percent = serializers.IntegerField()


class LicenceBatchDefaultsSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    price_per_licence_per_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    billing_months = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class OrganisationDetailSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    primary_admin_email = serializers.EmailField(source='primary_admin_user.email', read_only=True)
    licence_count = serializers.SerializerMethodField()
    state_transitions = StateTransitionSerializer(many=True, read_only=True)
    lifecycle_events = LifecycleEventSerializer(many=True, read_only=True)
    licence_ledger_entries = LicenceLedgerEntrySerializer(many=True, read_only=True)
    licence_summary = serializers.SerializerMethodField()
    licence_batches = LicenceBatchSerializer(many=True, read_only=True)
    batch_defaults = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'slug', 'status', 'billing_status', 'access_state', 'onboarding_stage',
            'licence_count', 'country_code', 'currency',
            'address', 'phone', 'email', 'logo_url',
            'primary_admin_email', 'paid_marked_at', 'activated_at', 'suspended_at',
            'created_by_email', 'created_at', 'updated_at',
            'state_transitions', 'lifecycle_events', 'licence_ledger_entries', 'licence_summary',
            'licence_batches', 'batch_defaults',
        ]

    def get_licence_count(self, obj):
        from .services import get_org_licence_summary

        return get_org_licence_summary(obj)['active_paid_quantity']

    def get_licence_summary(self, obj):
        from .services import get_org_licence_summary

        return get_org_licence_summary(obj)

    def get_batch_defaults(self, obj):
        from .services import get_licence_batch_defaults

        return LicenceBatchDefaultsSerializer(get_licence_batch_defaults(obj)).data


class CreateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    country_code = serializers.CharField(max_length=2, required=False, default='IN')
    currency = serializers.CharField(max_length=3, required=False, default='INR')
    licence_count = serializers.IntegerField(min_value=0, required=False, default=0)


class UpdateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)


class LicenceUpdateSerializer(serializers.Serializer):
    licence_count = serializers.IntegerField(min_value=0)
    note = serializers.CharField(required=False, allow_blank=True, default='')


class LicenceBatchWriteSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    price_per_licence_per_month = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, default='')


class LicenceBatchUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=False)
    price_per_licence_per_month = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)


class LicenceBatchMarkPaidSerializer(serializers.Serializer):
    paid_at = serializers.DateField(required=False)


class OrgAdminSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    is_active = serializers.SerializerMethodField()
    is_onboarding_email_sent = serializers.BooleanField(source='user.is_onboarding_email_sent', read_only=True)

    class Meta:
        model = OrganisationMembership
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'is_onboarding_email_sent']

    def get_is_active(self, obj):
        return obj.user.is_active


class CTDashboardStatsSerializer(serializers.Serializer):
    total_organisations = serializers.IntegerField()
    active_organisations = serializers.IntegerField()
    pending_organisations = serializers.IntegerField()
    paid_organisations = serializers.IntegerField()
    suspended_organisations = serializers.IntegerField()
    total_employees = serializers.IntegerField()
    total_licences = serializers.IntegerField()
    allocated_licences = serializers.IntegerField()


class OrgDashboardStatsSerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    invited_employees = serializers.IntegerField()
    inactive_employees = serializers.IntegerField()
    terminated_employees = serializers.IntegerField()
    by_department = serializers.ListField()
    by_location = serializers.ListField()
    recent_joins = serializers.ListField()
    licence_used = serializers.IntegerField()
    licence_total = serializers.IntegerField()
    onboarding_stage = serializers.CharField()
