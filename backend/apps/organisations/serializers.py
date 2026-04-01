from decimal import Decimal

from rest_framework import serializers
from .models import (
    BootstrapAdminStatus,
    LicenceBatchLifecycleState,
    LicenceBatchPaymentStatus,
    Organisation,
    OrganisationAddress,
    OrganisationBootstrapAdmin,
    OrganisationEntityType,
    OrganisationLegalIdentifier,
    OrganisationLegalIdentifierType,
    OrganisationLicenceBatch,
    OrganisationLifecycleEvent,
    OrganisationLicenceLedger,
    OrganisationMembership,
    OrganisationNote,
    OrganisationStateTransition,
    OrganisationTaxRegistration,
    OrganisationTaxRegistrationType,
)
from .country_metadata import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_CURRENCY_CODE,
    normalize_country_code,
    normalize_currency_code,
    resolve_country_code,
    validate_phone_for_country,
)
from .address_metadata import (
    get_country_name,
    normalize_subdivision,
    validate_billing_tax_identifier,
    validate_postal_code,
)
from .services import normalize_pan_number


class OrganisationAddressSerializer(serializers.ModelSerializer):
    address_type_label = serializers.CharField(source='get_address_type_display', read_only=True)
    tax_registration_id = serializers.UUIDField(source='tax_registration.id', read_only=True)

    class Meta:
        model = OrganisationAddress
        fields = [
            'id',
            'address_type',
            'address_type_label',
            'label',
            'line1',
            'line2',
            'city',
            'state',
            'state_code',
            'country',
            'country_code',
            'pincode',
            'gstin',
            'tax_registration_id',
            'is_active',
            'created_at',
            'updated_at',
        ]


class OrganisationAddressWriteSerializer(serializers.Serializer):
    address_type = serializers.ChoiceField(choices=OrganisationAddress._meta.get_field('address_type').choices)
    label = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    line1 = serializers.CharField()
    line2 = serializers.CharField(required=False, allow_blank=True, default='')
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    state_code = serializers.CharField(max_length=16, required=False, allow_blank=True, default='')
    country = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True, default=DEFAULT_COUNTRY_CODE)
    pincode = serializers.CharField(max_length=20)
    gstin = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_country_code(self, value):
        try:
            return resolve_country_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        address = self.context.get('address')
        address_type = attrs.get('address_type') or getattr(address, 'address_type', None)
        country_code = attrs.get('country_code') or getattr(address, 'country_code', '') or ''
        if not country_code:
            country_code = resolve_country_code(attrs.get('country') or getattr(address, 'country', ''))
        try:
            state_code, state = normalize_subdivision(
                country_code,
                state_code=attrs.get('state_code', getattr(address, 'state_code', '')),
                state_name=attrs.get('state', getattr(address, 'state', '')),
            )
            attrs['pincode'] = validate_postal_code(
                attrs.get('pincode', getattr(address, 'pincode', '')),
                country_code,
            )
            attrs['gstin'] = validate_billing_tax_identifier(
                country_code=country_code,
                address_type=address_type,
                identifier=attrs.get('gstin', getattr(address, 'gstin', None)),
                state_code=state_code,
            )
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        attrs['address_type'] = address_type
        attrs['country_code'] = country_code
        attrs['country'] = get_country_name(country_code)
        attrs['state_code'] = state_code
        attrs['state'] = state
        if attrs.get('address_type') in {'REGISTERED', 'BILLING'}:
            attrs['label'] = {
                'REGISTERED': 'Registered Office',
                'BILLING': 'Billing Address',
            }[attrs['address_type']]
        return attrs


class PrimaryAdminWriteSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')


class BootstrapAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    invited_user_email = serializers.EmailField(source='invited_user.email', read_only=True)
    invited_user_id = serializers.UUIDField(source='invited_user.id', read_only=True)

    class Meta:
        model = OrganisationBootstrapAdmin
        fields = [
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'status',
            'invited_user_id',
            'invited_user_email',
            'invitation_sent_at',
            'accepted_at',
            'updated_at',
        ]

    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip()


class OrganisationLegalIdentifierSerializer(serializers.ModelSerializer):
    identifier_type_label = serializers.CharField(source='get_identifier_type_display', read_only=True)

    class Meta:
        model = OrganisationLegalIdentifier
        fields = ['id', 'country_code', 'identifier_type', 'identifier_type_label', 'identifier', 'is_primary']


class OrganisationTaxRegistrationSerializer(serializers.ModelSerializer):
    registration_type_label = serializers.CharField(source='get_registration_type_display', read_only=True)

    class Meta:
        model = OrganisationTaxRegistration
        fields = [
            'id',
            'country_code',
            'registration_type',
            'registration_type_label',
            'identifier',
            'state_code',
            'is_primary_billing',
        ]


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


class OrganisationNoteSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = OrganisationNote
        fields = ['id', 'body', 'created_at', 'created_by']

    def get_created_by(self, obj):
        return {
            'id': str(obj.created_by_id),
            'full_name': obj.created_by.full_name,
            'email': obj.created_by.email,
        }


class OrganisationNoteWriteSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000)


class OrganisationConfigurationSummarySerializer(serializers.Serializer):
    locations = serializers.IntegerField()
    departments = serializers.IntegerField()
    leave_cycles = serializers.IntegerField()
    leave_plans = serializers.IntegerField()
    on_duty_policies = serializers.IntegerField()
    approval_workflows = serializers.IntegerField()
    notices = serializers.IntegerField()


class OrganisationDetailSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    primary_admin_email = serializers.EmailField(source='primary_admin_user.email', read_only=True)
    entity_type_label = serializers.CharField(source='get_entity_type_display', read_only=True)
    licence_count = serializers.SerializerMethodField()
    primary_admin = BootstrapAdminSerializer(source='bootstrap_admin', read_only=True)
    bootstrap_admin = BootstrapAdminSerializer(read_only=True)
    addresses = OrganisationAddressSerializer(many=True, read_only=True)
    legal_identifiers = OrganisationLegalIdentifierSerializer(many=True, read_only=True)
    tax_registrations = OrganisationTaxRegistrationSerializer(many=True, read_only=True)
    state_transitions = StateTransitionSerializer(many=True, read_only=True)
    lifecycle_events = LifecycleEventSerializer(many=True, read_only=True)
    licence_ledger_entries = LicenceLedgerEntrySerializer(many=True, read_only=True)
    licence_summary = serializers.SerializerMethodField()
    licence_batches = LicenceBatchSerializer(many=True, read_only=True)
    batch_defaults = serializers.SerializerMethodField()
    admin_count = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()
    holiday_calendar_count = serializers.SerializerMethodField()
    note_count = serializers.SerializerMethodField()
    configuration_summary = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'slug', 'status', 'billing_status', 'access_state', 'onboarding_stage',
            'licence_count', 'country_code', 'currency', 'entity_type', 'entity_type_label', 'pan_number',
            'address', 'phone', 'email', 'logo_url',
            'primary_admin_email', 'primary_admin', 'bootstrap_admin', 'paid_marked_at', 'activated_at', 'suspended_at',
            'created_by_email', 'created_at', 'updated_at',
            'admin_count', 'employee_count', 'holiday_calendar_count', 'note_count', 'configuration_summary',
            'addresses', 'legal_identifiers', 'tax_registrations',
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

    def get_admin_count(self, obj):
        return obj.memberships.filter(is_org_admin=True, status='ACTIVE').count()

    def get_employee_count(self, obj):
        from apps.employees.models import Employee

        return Employee.objects.filter(organisation=obj).count()

    def get_holiday_calendar_count(self, obj):
        from apps.timeoff.models import HolidayCalendar

        return HolidayCalendar.objects.filter(organisation=obj).count()

    def get_note_count(self, obj):
        return obj.notes.count()

    def get_configuration_summary(self, obj):
        from apps.approvals.models import ApprovalWorkflow
        from apps.communications.models import Notice
        from apps.departments.models import Department
        from apps.locations.models import OfficeLocation
        from apps.timeoff.models import LeaveCycle, LeavePlan, OnDutyPolicy

        return OrganisationConfigurationSummarySerializer(
            {
                'locations': OfficeLocation.objects.filter(organisation=obj).count(),
                'departments': Department.objects.filter(organisation=obj).count(),
                'leave_cycles': LeaveCycle.objects.filter(organisation=obj).count(),
                'leave_plans': LeavePlan.objects.filter(organisation=obj).count(),
                'on_duty_policies': OnDutyPolicy.objects.filter(organisation=obj).count(),
                'approval_workflows': ApprovalWorkflow.objects.filter(organisation=obj).count(),
                'notices': Notice.objects.filter(organisation=obj).count(),
            }
        ).data


class CreateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    pan_number = serializers.CharField(max_length=10)
    country_code = serializers.CharField(max_length=2, required=False, default=DEFAULT_COUNTRY_CODE)
    currency = serializers.CharField(max_length=3, required=False, default=DEFAULT_CURRENCY_CODE)
    entity_type = serializers.ChoiceField(choices=OrganisationEntityType.choices)
    billing_same_as_registered = serializers.BooleanField(required=False, default=False)
    primary_admin = PrimaryAdminWriteSerializer()
    addresses = OrganisationAddressWriteSerializer(many=True)

    def validate_pan_number(self, value):
        try:
            return normalize_pan_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_country_code(self, value):
        try:
            return normalize_country_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_currency(self, value):
        try:
            return normalize_currency_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        try:
            attrs['primary_admin']['phone'] = validate_phone_for_country(
                attrs['primary_admin'].get('phone', ''),
                attrs['country_code'],
            )
        except ValueError as exc:
            raise serializers.ValidationError({'primary_admin': {'phone': str(exc)}}) from exc
        address_types = [address['address_type'] for address in attrs.get('addresses', []) if address.get('is_active', True)]
        if address_types.count('REGISTERED') != 1 or address_types.count('BILLING') != 1:
            raise serializers.ValidationError(
                {'addresses': 'Exactly one active registered address and one active billing address are required.'}
            )
        pan_number = attrs['pan_number']
        registered_address = next((address for address in attrs['addresses'] if address['address_type'] == 'REGISTERED'), None)
        billing_address = next((address for address in attrs['addresses'] if address['address_type'] == 'BILLING'), None)
        if (
            attrs.get('billing_same_as_registered')
            and registered_address
            and billing_address
            and (registered_address.get('gstin') or '') != (billing_address.get('gstin') or '')
        ):
            raise serializers.ValidationError(
                {'addresses': 'Billing same as registered requires the same billing tax identifier on both addresses.'}
            )
        for index, address in enumerate(attrs.get('addresses', [])):
            try:
                attrs['addresses'][index]['gstin'] = validate_billing_tax_identifier(
                    country_code=address.get('country_code'),
                    address_type=address.get('address_type'),
                    identifier=address.get('gstin'),
                    pan_number=pan_number,
                    state_code=address.get('state_code'),
                )
            except ValueError as exc:
                raise serializers.ValidationError({'addresses': str(exc)}) from exc
        return attrs


class UpdateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    pan_number = serializers.CharField(max_length=10, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    entity_type = serializers.ChoiceField(choices=OrganisationEntityType.choices, required=False)
    logo_url = serializers.URLField(required=False, allow_blank=True)
    primary_admin = PrimaryAdminWriteSerializer(required=False)

    def validate_pan_number(self, value):
        try:
            return normalize_pan_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_country_code(self, value):
        try:
            return normalize_country_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_currency(self, value):
        try:
            return normalize_currency_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        organisation = self.context.get('organisation')
        if organisation is None:
            return attrs
        country_code = attrs.get('country_code', organisation.country_code)
        if 'country_code' in attrs:
            attrs['country_code'] = country_code
        phone_value = attrs.get('phone', organisation.phone)
        if 'phone' in attrs or 'country_code' in attrs:
            try:
                normalized_phone = validate_phone_for_country(phone_value, country_code)
            except ValueError as exc:
                raise serializers.ValidationError({'phone': str(exc)}) from exc
            if 'phone' in attrs:
                attrs['phone'] = normalized_phone
        primary_admin = attrs.get('primary_admin')
        if primary_admin:
            try:
                primary_admin['phone'] = validate_phone_for_country(primary_admin.get('phone', ''), country_code)
            except ValueError as exc:
                raise serializers.ValidationError({'primary_admin': {'phone': str(exc)}}) from exc
        return attrs


class LicenceUpdateSerializer(serializers.Serializer):
    licence_count = serializers.IntegerField(min_value=0)
    note = serializers.CharField(required=False, allow_blank=True, default='')


class LicenceBatchWriteSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    price_per_licence_per_month = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, default='')


class LicenceBatchUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=False)
    price_per_licence_per_month = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'), required=False)
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
    membership_status = serializers.CharField(source='status', read_only=True)
    invited_at = serializers.DateTimeField(read_only=True)
    accepted_at = serializers.DateTimeField(read_only=True)
    last_used_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = OrganisationMembership
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'is_active',
            'is_onboarding_email_sent',
            'membership_status',
            'invited_at',
            'accepted_at',
            'last_used_at',
        ]

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
    pending_employees = serializers.IntegerField()
    resigned_employees = serializers.IntegerField()
    retired_employees = serializers.IntegerField()
    terminated_employees = serializers.IntegerField()
    by_department = serializers.ListField()
    by_location = serializers.ListField()
    recent_joins = serializers.ListField()
    licence_used = serializers.IntegerField()
    licence_total = serializers.IntegerField()
    onboarding_stage = serializers.CharField()
    pending_approvals = serializers.IntegerField()
    documents_awaiting_review = serializers.IntegerField()
