import math
import re
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.employees.models import Employee, EmployeeStatus
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
from .models import (
    LicenceBatchLifecycleState,
    LicenceBatchPaymentStatus,
    LifecycleEventType,
    LicenceLedgerReason,
    Organisation,
    OrganisationAddress,
    OrganisationAddressType,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationEntityType,
    OrganisationLifecycleEvent,
    OrganisationLicenceBatch,
    OrganisationLicenceLedger,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationOnboardingStage,
    OrganisationStateTransition,
    OrganisationStatus,
)

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GSTIN_PATTERN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')

LICENCE_CONSUMING_EMPLOYEE_STATUSES = [
    EmployeeStatus.INVITED,
    EmployeeStatus.PENDING,
    EmployeeStatus.ACTIVE,
]

MANDATORY_ADDRESS_TYPES = {
    OrganisationAddressType.REGISTERED,
    OrganisationAddressType.BILLING,
}


def normalize_pan_number(value):
    normalized = (value or '').replace(' ', '').upper()
    if not normalized:
        return ''
    if not PAN_PATTERN.match(normalized):
        raise ValueError('PAN must be in the format AAAAA9999A.')
    return normalized


def normalize_gstin(value, pan_number=''):
    normalized = (value or '').replace(' ', '').upper()
    if not normalized:
        return None
    if not GSTIN_PATTERN.match(normalized):
        raise ValueError('GSTIN must be in the format 22AAAAA0000A1Z5.')
    if pan_number and normalized[2:12] != pan_number:
        raise ValueError('GSTIN must contain the organisation PAN number.')
    return normalized


def _default_address_label(address_type):
    return {
        OrganisationAddressType.REGISTERED: 'Registered Office',
        OrganisationAddressType.BILLING: 'Billing Address',
        OrganisationAddressType.HEADQUARTERS: 'Headquarters',
        OrganisationAddressType.WAREHOUSE: 'Warehouse',
        OrganisationAddressType.CUSTOM: 'Custom Address',
    }[address_type]


def _normalize_address_payload(payload, pan_number):
    address_type = payload.get('address_type')
    if address_type not in OrganisationAddressType.values:
        raise ValueError('Address type is invalid.')

    line1 = (payload.get('line1') or '').strip()
    city = (payload.get('city') or '').strip()
    country_code = resolve_country_code(payload.get('country_code') or payload.get('country') or DEFAULT_COUNTRY_CODE)
    country = get_country_name(country_code)
    state_code, state = normalize_subdivision(
        country_code,
        state_code=payload.get('state_code', ''),
        state_name=payload.get('state', ''),
    )
    pincode = validate_postal_code(payload.get('pincode'), country_code)
    line2 = (payload.get('line2') or '').strip()
    if not all([line1, city, pincode]) or not (state or state_code):
        raise ValueError('Address line 1, city, state, and postal code are required.')

    label = (payload.get('label') or '').strip()
    if address_type in MANDATORY_ADDRESS_TYPES:
        label = _default_address_label(address_type)
    elif not label:
        raise ValueError('A label is required for headquarters, warehouse, and custom addresses.')

    return {
        'address_type': address_type,
        'label': label,
        'line1': line1,
        'line2': line2,
        'city': city,
        'state': state,
        'state_code': state_code,
        'country': country,
        'country_code': country_code,
        'pincode': pincode,
        'gstin': validate_billing_tax_identifier(
            country_code=country_code,
            address_type=address_type,
            identifier=payload.get('gstin'),
            pan_number=pan_number,
            state_code=state_code,
        ),
        'is_active': payload.get('is_active', True),
    }


def validate_address_collection(addresses, pan_number):
    if not addresses:
        raise ValueError('At least one address is required.')
    normalized_addresses = [_normalize_address_payload(address, pan_number) for address in addresses]
    active_counts = {
        address_type: sum(
            1
            for address in normalized_addresses
            if address['address_type'] == address_type and address.get('is_active', True)
        )
        for address_type in MANDATORY_ADDRESS_TYPES
    }
    missing = [address_type for address_type, count in active_counts.items() if count != 1]
    if missing:
        raise ValueError('Exactly one active registered address and one active billing address are required.')
    return normalized_addresses


def _sync_location_address_fields(location, organisation_address):
    location.organisation_address = organisation_address
    location.address = organisation_address.line1
    location.city = organisation_address.city
    location.state = organisation_address.state
    location.country = organisation_address.country
    location.pincode = organisation_address.pincode


def _ensure_default_location_for_address(organisation_address, actor=None, is_remote=False):
    from apps.locations.models import OfficeLocation

    location, created = OfficeLocation.objects.get_or_create(
        organisation=organisation_address.organisation,
        name=organisation_address.label,
        defaults={'is_remote': is_remote},
    )
    _sync_location_address_fields(location, organisation_address)
    if created or not location.is_active:
        location.is_active = True
    if location.is_remote != is_remote:
        location.is_remote = is_remote
    location.save()
    log_audit_event(
        actor,
        'location.created' if created else 'location.updated',
        organisation=organisation_address.organisation,
        target=location,
        payload={'auto_created': True, 'organisation_address_id': str(organisation_address.id)},
    )
    return location


def create_organisation_address(
    organisation,
    *,
    address_type,
    line1,
    city,
    state,
    pincode,
    actor=None,
    line2='',
    country='India',
    country_code=DEFAULT_COUNTRY_CODE,
    label='',
    state_code='',
    gstin=None,
    is_active=True,
    auto_create_location=False,
):
    if not organisation.pan_number:
        raise ValueError('Organisation PAN must be set before adding addresses.')

    payload = _normalize_address_payload(
        {
            'address_type': address_type,
            'label': label,
            'line1': line1,
            'line2': line2,
            'city': city,
            'state': state,
            'state_code': state_code,
            'country': country,
            'country_code': country_code,
            'pincode': pincode,
            'gstin': gstin,
            'is_active': is_active,
        },
        organisation.pan_number,
    )

    try:
        with transaction.atomic():
            address = OrganisationAddress.objects.create(organisation=organisation, **payload)
            log_audit_event(
                actor,
                'organisation.address.created',
                organisation=organisation,
                target=address,
                payload={'address_type': address.address_type, 'label': address.label},
            )
            if auto_create_location and address.is_active:
                _ensure_default_location_for_address(address, actor=actor)
                mark_master_data_configured(organisation, actor)
            return address
    except IntegrityError as exc:
        raise ValueError('GSTIN must be unique and required address types can only exist once.') from exc


def update_organisation_address(address, actor=None, **fields):
    organisation = address.organisation
    pan_number = normalize_pan_number(fields.pop('pan_number', organisation.pan_number or ''))
    if pan_number and pan_number != (organisation.pan_number or ''):
        validate_organisation_pan_change(organisation, pan_number)

    payload = _normalize_address_payload(
        {
            'address_type': fields.get('address_type', address.address_type),
            'label': fields.get('label', address.label),
            'line1': fields.get('line1', address.line1),
            'line2': fields.get('line2', address.line2),
            'city': fields.get('city', address.city),
            'state': fields.get('state', address.state),
            'state_code': fields.get('state_code', address.state_code),
            'country': fields.get('country', address.country),
            'country_code': fields.get('country_code', address.country_code),
            'pincode': fields.get('pincode', address.pincode),
            'gstin': fields.get('gstin', address.gstin),
            'is_active': fields.get('is_active', address.is_active),
        },
        organisation.pan_number or pan_number,
    )

    if address.address_type in MANDATORY_ADDRESS_TYPES and (
        fields.get('is_active') is False or payload['address_type'] != address.address_type
    ):
        active_count = organisation.addresses.filter(
            address_type=address.address_type,
            is_active=True,
        ).exclude(id=address.id).count()
        if active_count == 0:
            raise ValueError(f'{address.get_address_type_display()} cannot be removed without a replacement.')

    for attr, value in payload.items():
        setattr(address, attr, value)

    try:
        with transaction.atomic():
            address.save()
            if address.office_locations.exists():
                for location in address.office_locations.all():
                    _sync_location_address_fields(location, address)
                    location.save()
            log_audit_event(
                actor,
                'organisation.address.updated',
                organisation=organisation,
                target=address,
                payload={'address_type': address.address_type, 'label': address.label},
            )
        return address
    except IntegrityError as exc:
        raise ValueError('GSTIN must be unique and required address types can only exist once.') from exc


def deactivate_organisation_address(address, actor=None):
    if address.address_type in MANDATORY_ADDRESS_TYPES:
        remaining = address.organisation.addresses.filter(
            address_type=address.address_type,
            is_active=True,
        ).exclude(id=address.id)
        if not remaining.exists():
            raise ValueError(f'{address.get_address_type_display()} cannot be removed without a replacement.')
    if address.office_locations.filter(is_active=True).exists():
        raise ValueError('Deactivate linked office locations before deactivating this address.')

    address.is_active = False
    address.save(update_fields=['is_active', 'updated_at'])
    log_audit_event(
        actor,
        'organisation.address.deactivated',
        organisation=address.organisation,
        target=address,
        payload={'address_type': address.address_type, 'label': address.label},
    )
    return address


def validate_organisation_pan_change(organisation, pan_number):
    normalized_pan = normalize_pan_number(pan_number)
    invalid_gst_addresses = [
        address
        for address in organisation.addresses.exclude(gstin__isnull=True).exclude(gstin='')
        if (address.gstin or '')[2:12] != normalized_pan
    ]
    if invalid_gst_addresses:
        raise ValueError('PAN cannot be changed because one or more GSTINs do not match the new PAN.')
    return normalized_pan

VALID_TRANSITIONS = {
    OrganisationStatus.PENDING: [OrganisationStatus.PAID],
    OrganisationStatus.PAID: [OrganisationStatus.ACTIVE],
    OrganisationStatus.ACTIVE: [OrganisationStatus.SUSPENDED],
    OrganisationStatus.SUSPENDED: [OrganisationStatus.ACTIVE],
}

STAGE_ORDER = {
    OrganisationOnboardingStage.ORG_CREATED: 1,
    OrganisationOnboardingStage.LICENCES_ASSIGNED: 2,
    OrganisationOnboardingStage.PAYMENT_CONFIRMED: 3,
    OrganisationOnboardingStage.ADMIN_INVITED: 4,
    OrganisationOnboardingStage.ADMIN_ACTIVATED: 5,
    OrganisationOnboardingStage.MASTER_DATA_CONFIGURED: 6,
    OrganisationOnboardingStage.EMPLOYEES_INVITED: 7,
}


def _bump_onboarding_stage(org, stage):
    if STAGE_ORDER[stage] > STAGE_ORDER.get(org.onboarding_stage, 0):
        org.onboarding_stage = stage


def _sync_legacy_status(org):
    if org.access_state == OrganisationAccessState.SUSPENDED:
        org.status = OrganisationStatus.SUSPENDED
    elif org.access_state == OrganisationAccessState.ACTIVE:
        org.status = OrganisationStatus.ACTIVE
    elif org.billing_status == OrganisationBillingStatus.PAID:
        org.status = OrganisationStatus.PAID
    else:
        org.status = OrganisationStatus.PENDING


def create_lifecycle_event(organisation, event_type, actor=None, payload=None):
    return OrganisationLifecycleEvent.objects.create(
        organisation=organisation,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )


def _next_year(input_date):
    try:
        return input_date.replace(year=input_date.year + 1)
    except ValueError:
        return input_date.replace(month=2, day=28, year=input_date.year + 1)


def get_default_licence_price():
    raw_value = getattr(settings, 'DEFAULT_LICENCE_PRICE_PER_MONTH', Decimal('0.00'))
    return Decimal(str(raw_value)).quantize(Decimal('0.01'))


def calculate_licence_billing_months(start_date, end_date):
    if end_date < start_date:
        raise ValueError('End date cannot be earlier than start date.')
    total_days = (end_date - start_date).days + 1
    return max(1, math.ceil(total_days / 30))


def calculate_licence_total_amount(quantity, price_per_licence_per_month, billing_months):
    price = Decimal(str(price_per_licence_per_month)).quantize(Decimal('0.01'))
    total = Decimal(quantity) * price * Decimal(billing_months)
    return total.quantize(Decimal('0.01'))


def get_batch_lifecycle_state(batch, as_of=None):
    effective_date = as_of or timezone.localdate()
    if batch.payment_status == LicenceBatchPaymentStatus.DRAFT:
        return LicenceBatchLifecycleState.DRAFT
    if effective_date < batch.start_date:
        return LicenceBatchLifecycleState.PAID_PENDING_START
    if batch.start_date <= effective_date <= batch.end_date:
        return LicenceBatchLifecycleState.ACTIVE
    return LicenceBatchLifecycleState.EXPIRED


def get_active_licence_batches(org, as_of=None):
    effective_date = as_of or timezone.localdate()
    return OrganisationLicenceBatch.objects.filter(
        organisation=org,
        payment_status=LicenceBatchPaymentStatus.PAID,
        start_date__lte=effective_date,
        end_date__gte=effective_date,
    )


def get_licence_batch_defaults(org, quantity=1, start_date=None, as_of=None):
    effective_date = as_of or timezone.localdate()
    resolved_start_date = start_date or effective_date
    latest_active_end_date = (
        get_active_licence_batches(org, as_of=effective_date)
        .order_by('-end_date')
        .values_list('end_date', flat=True)
        .first()
    )
    resolved_end_date = latest_active_end_date or _next_year(resolved_start_date)
    price = get_default_licence_price()
    billing_months = calculate_licence_billing_months(resolved_start_date, resolved_end_date)
    total_amount = calculate_licence_total_amount(quantity, price, billing_months)
    return {
        'start_date': resolved_start_date,
        'end_date': resolved_end_date,
        'price_per_licence_per_month': price,
        'billing_months': billing_months,
        'total_amount': total_amount,
    }


def get_org_licence_summary(org, as_of=None):
    active_paid_quantity = get_active_licence_batches(org, as_of=as_of).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    used = Employee.objects.filter(
        organisation=org,
        status__in=LICENCE_CONSUMING_EMPLOYEE_STATUSES,
    ).count()
    available = max(active_paid_quantity - used, 0)
    overage = max(used - active_paid_quantity, 0)
    utilisation_percent = int((used / active_paid_quantity) * 100) if active_paid_quantity else 0
    return {
        'active_paid_quantity': active_paid_quantity,
        'allocated': used,
        'available': available,
        'overage': overage,
        'has_overage': overage > 0,
        'utilisation_percent': utilisation_percent,
    }


def get_org_operations_guard(org, as_of=None):
    summary = get_org_licence_summary(org, as_of=as_of)
    licence_expired = summary['active_paid_quantity'] <= 0
    return {
        'licence_expired': licence_expired,
        'admin_mutations_blocked': licence_expired,
        'approval_actions_blocked': licence_expired,
        'seat_assignment_blocked': summary['available'] <= 0,
        'reason': 'Organisation licences have expired. Renew licences in Control Tower to continue.'
        if licence_expired
        else '',
        'summary': summary,
    }


def create_organisation(
    name,
    created_by,
    pan_number,
    addresses,
    phone='',
    email='',
    country_code=DEFAULT_COUNTRY_CODE,
    currency=DEFAULT_CURRENCY_CODE,
    entity_type=OrganisationEntityType.PRIVATE_LIMITED,
    licence_count=0,
):
    normalized_pan = normalize_pan_number(pan_number)
    normalized_addresses = validate_address_collection(addresses, normalized_pan)
    normalized_country_code = normalize_country_code(country_code)
    normalized_currency = normalize_currency_code(currency)
    normalized_phone = validate_phone_for_country(phone, normalized_country_code)

    with transaction.atomic():
        organisation = Organisation.objects.create(
            name=name,
            pan_number=normalized_pan,
            address=normalized_addresses[0]['line1'],
            phone=normalized_phone,
            email=email,
            licence_count=licence_count,
            created_by=created_by,
            country_code=normalized_country_code,
            currency=normalized_currency,
            entity_type=entity_type,
            billing_status=OrganisationBillingStatus.PENDING_PAYMENT,
            access_state=OrganisationAccessState.PROVISIONING,
            onboarding_stage=(
                OrganisationOnboardingStage.LICENCES_ASSIGNED
                if licence_count
                else OrganisationOnboardingStage.ORG_CREATED
            ),
        )
        if licence_count:
            OrganisationLicenceLedger.objects.create(
                organisation=organisation,
                delta=licence_count,
                reason=LicenceLedgerReason.OPENING_BALANCE,
                note='Initial licence allocation',
                created_by=created_by,
            )
        create_lifecycle_event(
            organisation,
            LifecycleEventType.ORGANISATION_CREATED,
            created_by,
            {'licence_count': licence_count},
        )
        for address_payload in normalized_addresses:
            create_organisation_address(
                organisation,
                actor=created_by,
                auto_create_location=True,
                **address_payload,
            )
        log_audit_event(
            created_by,
            'organisation.created',
            organisation=organisation,
            target=organisation,
            payload={'licence_count': licence_count, 'pan_number': normalized_pan},
        )
    return organisation


def update_organisation_profile(organisation, actor=None, **fields):
    if 'pan_number' in fields:
        organisation.pan_number = validate_organisation_pan_change(
            organisation,
            fields.pop('pan_number'),
        )

    if 'country_code' in fields:
        fields['country_code'] = normalize_country_code(fields['country_code'])
    if 'currency' in fields:
        fields['currency'] = normalize_currency_code(fields['currency'])
    if 'phone' in fields:
        country_code = fields.get('country_code', organisation.country_code)
        fields['phone'] = validate_phone_for_country(fields['phone'], country_code)
    elif 'country_code' in fields and organisation.phone:
        validate_phone_for_country(organisation.phone, fields['country_code'])

    legacy_address = fields.pop('address', None)
    for attr, value in fields.items():
        setattr(organisation, attr, value)

    if legacy_address:
        organisation.address = legacy_address
    elif organisation.addresses.filter(is_active=True).exists():
        primary_address = (
            organisation.addresses.filter(
                address_type=OrganisationAddressType.REGISTERED,
                is_active=True,
            ).first()
            or organisation.addresses.filter(is_active=True).first()
        )
        organisation.address = primary_address.line1 if primary_address else organisation.address

    organisation.save()
    log_audit_event(
        actor,
        'organisation.updated',
        organisation=organisation,
        target=organisation,
        payload={key: value for key, value in fields.items() if value is not None},
    )
    return organisation


def transition_organisation_state(org, new_status, transitioned_by, note=''):
    allowed = VALID_TRANSITIONS.get(org.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{org.status}' to '{new_status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )
    with transaction.atomic():
        old_status = org.status
        now = timezone.now()
        if new_status == OrganisationStatus.PAID:
            org.billing_status = OrganisationBillingStatus.PAID
            org.access_state = OrganisationAccessState.PROVISIONING
            org.paid_marked_at = now
            org.paid_marked_by = transitioned_by
            _bump_onboarding_stage(org, OrganisationOnboardingStage.PAYMENT_CONFIRMED)
            event_type = LifecycleEventType.PAYMENT_MARKED
        elif new_status == OrganisationStatus.ACTIVE:
            org.access_state = OrganisationAccessState.ACTIVE
            org.activated_at = now
            org.suspended_at = None
            _bump_onboarding_stage(org, OrganisationOnboardingStage.ADMIN_ACTIVATED)
            event_type = (
                LifecycleEventType.ACCESS_RESTORED
                if old_status == OrganisationStatus.SUSPENDED
                else LifecycleEventType.ADMIN_ACTIVATED
            )
        elif new_status == OrganisationStatus.SUSPENDED:
            org.access_state = OrganisationAccessState.SUSPENDED
            org.suspended_at = now
            event_type = LifecycleEventType.ACCESS_SUSPENDED
        _sync_legacy_status(org)
        org.save()
        OrganisationStateTransition.objects.create(
            organisation=org,
            from_status=old_status,
            to_status=new_status,
            transitioned_by=transitioned_by,
            note=note,
        )
        create_lifecycle_event(
            org,
            event_type,
            transitioned_by,
            {'note': note, 'from_status': old_status, 'to_status': new_status},
        )
        log_audit_event(
            transitioned_by,
            f'organisation.status.{new_status.lower()}',
            organisation=org,
            target=org,
            payload={'from_status': old_status, 'to_status': new_status, 'note': note},
        )
    return org


def update_licence_count(org, new_count, changed_by=None, note=''):
    current_summary = get_org_licence_summary(org)
    if new_count < current_summary['allocated']:
        raise ValueError('Licence count cannot be lower than allocated employees.')

    delta = new_count - org.licence_count
    if delta == 0:
        return org

    with transaction.atomic():
        OrganisationLicenceLedger.objects.create(
            organisation=org,
            delta=delta,
            reason=LicenceLedgerReason.PURCHASE if delta > 0 else LicenceLedgerReason.ADJUSTMENT,
            note=note,
            created_by=changed_by,
        )
        org.licence_count = new_count
        _bump_onboarding_stage(org, OrganisationOnboardingStage.LICENCES_ASSIGNED)
        org.save(update_fields=['licence_count', 'onboarding_stage', 'updated_at'])
        create_lifecycle_event(
            org,
            LifecycleEventType.LICENCES_UPDATED,
            changed_by,
            {'delta': delta, 'new_count': new_count, 'note': note},
        )
        log_audit_event(
            changed_by,
            'organisation.licences.updated',
            organisation=org,
            target=org,
            payload={'delta': delta, 'new_count': new_count, 'note': note},
        )
    return org


def create_licence_batch(
    organisation,
    quantity,
    price_per_licence_per_month,
    start_date,
    end_date,
    created_by=None,
    note='',
):
    billing_months = calculate_licence_billing_months(start_date, end_date)
    total_amount = calculate_licence_total_amount(quantity, price_per_licence_per_month, billing_months)
    batch = OrganisationLicenceBatch.objects.create(
        organisation=organisation,
        quantity=quantity,
        price_per_licence_per_month=Decimal(str(price_per_licence_per_month)).quantize(Decimal('0.01')),
        start_date=start_date,
        end_date=end_date,
        billing_months=billing_months,
        total_amount=total_amount,
        payment_status=LicenceBatchPaymentStatus.DRAFT,
        created_by=created_by,
        note=note,
    )
    log_audit_event(
        created_by,
        'organisation.licence_batch.created',
        organisation=organisation,
        target=batch,
        payload={
            'quantity': quantity,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'payment_status': batch.payment_status,
        },
    )
    return batch


def update_licence_batch(batch, actor=None, **fields):
    if batch.payment_status != LicenceBatchPaymentStatus.DRAFT:
        raise ValueError('Paid licence batches cannot be edited.')

    for attr in ['quantity', 'price_per_licence_per_month', 'start_date', 'end_date', 'note']:
        if attr in fields:
            setattr(batch, attr, fields[attr])

    batch.price_per_licence_per_month = Decimal(str(batch.price_per_licence_per_month)).quantize(Decimal('0.01'))
    batch.billing_months = calculate_licence_billing_months(batch.start_date, batch.end_date)
    batch.total_amount = calculate_licence_total_amount(
        batch.quantity,
        batch.price_per_licence_per_month,
        batch.billing_months,
    )
    batch.save()
    log_audit_event(
        actor,
        'organisation.licence_batch.updated',
        organisation=batch.organisation,
        target=batch,
        payload={
            'quantity': batch.quantity,
            'start_date': batch.start_date.isoformat(),
            'end_date': batch.end_date.isoformat(),
        },
    )
    return batch


def mark_licence_batch_paid(batch, paid_by=None, paid_at=None):
    if batch.payment_status != LicenceBatchPaymentStatus.DRAFT:
        raise ValueError('Licence batch is already marked as paid.')

    resolved_paid_at = paid_at or timezone.localdate()
    with transaction.atomic():
        batch.payment_status = LicenceBatchPaymentStatus.PAID
        batch.paid_at = resolved_paid_at
        batch.paid_by = paid_by
        batch.save(update_fields=['payment_status', 'paid_at', 'paid_by', 'updated_at'])

        if batch.organisation.status == OrganisationStatus.PENDING:
            transition_organisation_state(
                batch.organisation,
                OrganisationStatus.PAID,
                transitioned_by=paid_by,
                note=f'Licence batch {batch.id} marked paid',
            )

    log_audit_event(
        paid_by,
        'organisation.licence_batch.paid',
        organisation=batch.organisation,
        target=batch,
        payload={'paid_at': resolved_paid_at.isoformat()},
    )
    return batch


def get_ct_dashboard_stats():
    agg = Organisation.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status=OrganisationStatus.ACTIVE)),
        pending=Count('id', filter=Q(status=OrganisationStatus.PENDING)),
        paid=Count('id', filter=Q(status=OrganisationStatus.PAID)),
        suspended=Count('id', filter=Q(status=OrganisationStatus.SUSPENDED)),
    )
    active_licences = OrganisationLicenceBatch.objects.filter(
        payment_status=LicenceBatchPaymentStatus.PAID,
        start_date__lte=timezone.localdate(),
        end_date__gte=timezone.localdate(),
    ).aggregate(total=Sum('quantity'))['total'] or 0
    return {
        'total_organisations': agg['total'],
        'active_organisations': agg['active'],
        'pending_organisations': agg['pending'],
        'paid_organisations': agg['paid'],
        'suspended_organisations': agg['suspended'],
        'total_employees': Employee.objects.filter(status=EmployeeStatus.ACTIVE).count(),
        'total_licences': active_licences,
        'allocated_licences': Employee.objects.filter(
            status__in=LICENCE_CONSUMING_EMPLOYEE_STATUSES
        ).count(),
    }


def get_org_dashboard_stats(organisation):
    from apps.approvals.models import ApprovalAction, ApprovalActionStatus
    from apps.documents.models import Document, DocumentStatus

    employees = Employee.objects.filter(organisation=organisation)
    return {
        'total_employees': employees.count(),
        'active_employees': employees.filter(status=EmployeeStatus.ACTIVE).count(),
        'invited_employees': employees.filter(status=EmployeeStatus.INVITED).count(),
        'pending_employees': employees.filter(status=EmployeeStatus.PENDING).count(),
        'resigned_employees': employees.filter(status=EmployeeStatus.RESIGNED).count(),
        'retired_employees': employees.filter(status=EmployeeStatus.RETIRED).count(),
        'terminated_employees': employees.filter(status=EmployeeStatus.TERMINATED).count(),
        'by_department': list(
            employees.filter(status=EmployeeStatus.ACTIVE)
            .exclude(department__isnull=True)
            .values(department_name=F('department__name'))
            .annotate(count=Count('id'))
            .order_by('-count', 'department_name')
        ),
        'by_location': list(
            employees.filter(status=EmployeeStatus.ACTIVE)
            .exclude(office_location__isnull=True)
            .values(location_name=F('office_location__name'))
            .annotate(count=Count('id'))
            .order_by('-count', 'location_name')
        ),
        'recent_joins': list(
            employees.exclude(date_of_joining__isnull=True)
            .order_by('-date_of_joining')
            .values('id', 'employee_code', 'designation', 'date_of_joining', 'user__first_name', 'user__last_name')[:10]
        ),
        'licence_used': get_org_licence_summary(organisation)['allocated'],
        'licence_total': get_org_licence_summary(organisation)['active_paid_quantity'],
        'onboarding_stage': organisation.onboarding_stage,
        'pending_approvals': ApprovalAction.objects.filter(
            approval_run__organisation=organisation,
            status=ApprovalActionStatus.PENDING,
        ).count(),
        'documents_awaiting_review': Document.objects.filter(
            employee__organisation=organisation,
            status=DocumentStatus.PENDING,
        ).count(),
    }


def set_primary_admin(organisation, user, actor=None):
    organisation.primary_admin_user = user
    _bump_onboarding_stage(organisation, OrganisationOnboardingStage.ADMIN_INVITED)
    organisation.save(update_fields=['primary_admin_user', 'onboarding_stage', 'updated_at'])
    create_lifecycle_event(
        organisation,
        LifecycleEventType.ADMIN_INVITED,
        actor,
        {'user_id': str(user.id), 'email': user.email},
    )
    log_audit_event(
        actor,
        'organisation.primary_admin.assigned',
        organisation=organisation,
        target=user,
        payload={'email': user.email},
    )
    return organisation


def ensure_org_admin_membership(organisation, user, invited_by=None, status=OrganisationMembershipStatus.ACTIVE):
    membership, _ = OrganisationMembership.objects.get_or_create(
        organisation=organisation,
        user=user,
        defaults={
            'is_org_admin': True,
            'status': status,
            'invited_by': invited_by,
            'accepted_at': timezone.now() if status == OrganisationMembershipStatus.ACTIVE else None,
        },
    )
    changed = False
    if not membership.is_org_admin:
        membership.is_org_admin = True
        changed = True
    if membership.status != status:
        membership.status = status
        changed = True
    if invited_by and membership.invited_by_id is None:
        membership.invited_by = invited_by
        changed = True
    if status == OrganisationMembershipStatus.ACTIVE and membership.accepted_at is None:
        membership.accepted_at = timezone.now()
        changed = True
    if changed:
        membership.save()
    return membership


def mark_master_data_configured(organisation, actor=None):
    if organisation.locations.filter(is_active=True).exists() and organisation.departments.filter(is_active=True).exists():
        if organisation.onboarding_stage != OrganisationOnboardingStage.MASTER_DATA_CONFIGURED:
            organisation.onboarding_stage = OrganisationOnboardingStage.MASTER_DATA_CONFIGURED
            organisation.save(update_fields=['onboarding_stage', 'updated_at'])
            create_lifecycle_event(organisation, LifecycleEventType.MASTER_DATA_CONFIGURED, actor)
            log_audit_event(
                actor,
                'organisation.master_data.configured',
                organisation=organisation,
                target=organisation,
            )
    return organisation


def mark_employee_invited(organisation, actor=None, employee=None):
    _bump_onboarding_stage(organisation, OrganisationOnboardingStage.EMPLOYEES_INVITED)
    organisation.save(update_fields=['onboarding_stage', 'updated_at'])
    create_lifecycle_event(
        organisation,
        LifecycleEventType.EMPLOYEE_INVITED,
        actor,
        {'employee_id': str(employee.id) if employee else None},
    )
    log_audit_event(
        actor,
        'organisation.employee.invited',
        organisation=organisation,
        target=employee,
        payload={'employee_id': str(employee.id) if employee else None},
    )
    return organisation
