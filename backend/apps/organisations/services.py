import csv
import hashlib
import hmac
import io
import json
import math
import re
import zipfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.accounts.contact_services import normalize_email_address, resolve_person_contacts
from apps.accounts.models import AccountType
from apps.accounts.workspaces import ACTIVE_EMPLOYEE_STATUSES, sync_user_role
from apps.audit.models import AuditLog
from apps.audit.services import log_audit_event
from apps.documents.s3 import generate_presigned_url, upload_file
from apps.employees.models import Employee, EmployeeStatus

from .address_metadata import (
    get_country_name,
    normalize_subdivision,
    validate_billing_tax_identifier,
    validate_postal_code,
)
from .country_metadata import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_CURRENCY_CODE,
    normalize_country_code,
    normalize_currency_code,
    resolve_country_code,
    validate_phone_for_country,
)
from .models import (
    ActAsSession,
    BootstrapAdminStatus,
    LicenceBatchLifecycleState,
    LicenceBatchPaymentStatus,
    LicenceLedgerReason,
    LifecycleEventType,
    OnboardingChecklist,
    OnboardingStepCode,
    OrgAdminSetupStep,
    Organisation,
    OrganisationAccessState,
    OrganisationAddress,
    OrganisationAddressType,
    OrganisationBillingEvent,
    OrganisationBillingEventStatus,
    OrganisationBillingProvider,
    OrganisationBillingStatus,
    OrganisationBootstrapAdmin,
    OrganisationEntityType,
    OrganisationFeatureCode,
    OrganisationFeatureFlag,
    OrganisationLegalIdentifier,
    OrganisationLegalIdentifierType,
    OrganisationLicenceBatch,
    OrganisationLicenceLedger,
    OrganisationLifecycleEvent,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationNote,
    OrganisationOnboardingStage,
    OrganisationStateTransition,
    OrganisationStatus,
    OrganisationTaxRegistration,
    OrganisationTaxRegistrationType,
    OrgUsageStat,
    TenantDataExportBatch,
    TenantDataExportStatus,
    TenantDataExportType,
)

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

LICENCE_CONSUMING_EMPLOYEE_STATUSES = list(ACTIVE_EMPLOYEE_STATUSES)

MANDATORY_ADDRESS_TYPES = {
    OrganisationAddressType.REGISTERED,
    OrganisationAddressType.BILLING,
}

ORG_ADMIN_SETUP_SEQUENCE = [
    OrgAdminSetupStep.PROFILE,
    OrgAdminSetupStep.ADDRESSES,
    OrgAdminSetupStep.LOCATIONS,
    OrgAdminSetupStep.DEPARTMENTS,
    OrgAdminSetupStep.HOLIDAYS,
    OrgAdminSetupStep.POLICIES,
    OrgAdminSetupStep.EMPLOYEES,
]

ORG_FEATURE_FLAG_DEFAULTS = {
    OrganisationFeatureCode.ATTENDANCE: True,
    OrganisationFeatureCode.APPROVALS: True,
    OrganisationFeatureCode.BIOMETRICS: True,
    OrganisationFeatureCode.NOTICES: True,
    OrganisationFeatureCode.PAYROLL: True,
    OrganisationFeatureCode.PERFORMANCE: True,
    OrganisationFeatureCode.RECRUITMENT: True,
    OrganisationFeatureCode.REPORTS: True,
    OrganisationFeatureCode.TIMEOFF: True,
}


def normalize_pan_number(value):
    normalized = (value or '').replace(' ', '').upper()
    if not normalized:
        return ''
    if not PAN_PATTERN.match(normalized):
        raise ValueError('PAN must be in the format AAAAA9999A.')
    return normalized

def _registration_type_for_country(country_code):
    return (
        OrganisationTaxRegistrationType.GSTIN
        if country_code == 'IN'
        else OrganisationTaxRegistrationType.OTHER
    )


def upsert_bootstrap_admin(organisation, *, first_name, last_name, email, phone='', actor=None):
    resolved_contacts = resolve_person_contacts(
        email=email,
        phone=phone,
        person=getattr(getattr(organisation, 'bootstrap_admin', None), 'person', None),
        email_kind='WORK',
        phone_kind='WORK',
    )
    bootstrap_admin, _ = OrganisationBootstrapAdmin.objects.get_or_create(
        organisation=organisation,
        defaults={
            'first_name': first_name.strip(),
            'last_name': last_name.strip(),
            'person': resolved_contacts.person,
            'email_address': resolved_contacts.email_address,
            'phone_number': resolved_contacts.phone_number,
            'email': resolved_contacts.normalized_email,
            'phone': resolved_contacts.normalized_phone,
        },
    )
    bootstrap_admin.first_name = first_name.strip()
    bootstrap_admin.last_name = last_name.strip()
    bootstrap_admin.person = resolved_contacts.person
    bootstrap_admin.email_address = resolved_contacts.email_address
    bootstrap_admin.phone_number = resolved_contacts.phone_number
    bootstrap_admin.email = resolved_contacts.normalized_email
    bootstrap_admin.phone = resolved_contacts.normalized_phone
    bootstrap_admin.save()
    log_audit_event(
        actor,
        'organisation.bootstrap_admin.updated',
        organisation=organisation,
        target=bootstrap_admin,
        payload={'email': bootstrap_admin.email, 'status': bootstrap_admin.status},
    )
    return bootstrap_admin


def upsert_primary_legal_identifier(organisation, *, country_code, identifier_type, identifier):
    normalized_identifier = (identifier or '').strip().upper()
    if not normalized_identifier:
        return None

    existing = OrganisationLegalIdentifier.objects.filter(
        country_code=country_code,
        identifier_type=identifier_type,
        identifier=normalized_identifier,
    ).first()
    if existing and existing.organisation_id != organisation.id:
        raise ValueError(f'{identifier_type} already belongs to another organisation.')

    record = existing or OrganisationLegalIdentifier(
        organisation=organisation,
        country_code=country_code,
        identifier_type=identifier_type,
        identifier=normalized_identifier,
    )
    record.organisation = organisation
    record.country_code = country_code
    record.identifier_type = identifier_type
    record.identifier = normalized_identifier
    record.is_primary = True
    record.save()
    return record


def ensure_tax_registration(
    organisation,
    *,
    country_code,
    identifier,
    state_code='',
    legal_identifier=None,
):
    normalized_identifier = (identifier or '').strip().upper()
    if not normalized_identifier:
        return None

    registration_type = _registration_type_for_country(country_code)
    existing = OrganisationTaxRegistration.objects.filter(
        country_code=country_code,
        registration_type=registration_type,
        identifier=normalized_identifier,
    ).first()
    if existing and existing.organisation_id != organisation.id:
        raise ValueError(f'{registration_type} already belongs to another organisation.')

    registration = existing or OrganisationTaxRegistration(
        organisation=organisation,
        country_code=country_code,
        registration_type=registration_type,
        identifier=normalized_identifier,
    )
    registration.organisation = organisation
    registration.country_code = country_code
    registration.registration_type = registration_type
    registration.identifier = normalized_identifier
    registration.state_code = state_code or ''
    if legal_identifier is not None:
        registration.legal_identifier = legal_identifier
    registration.save()
    return registration


def _sync_address_tax_registration(organisation, payload):
    legal_identifier = None
    if organisation.pan_number:
        legal_identifier = upsert_primary_legal_identifier(
            organisation,
            country_code=organisation.country_code,
            identifier_type=OrganisationLegalIdentifierType.PAN,
            identifier=organisation.pan_number,
        )

    tax_registration = ensure_tax_registration(
        organisation,
        country_code=payload['country_code'],
        identifier=payload.get('gstin'),
        state_code=payload.get('state_code', ''),
        legal_identifier=legal_identifier if payload['country_code'] == 'IN' else None,
    )
    if payload['address_type'] == OrganisationAddressType.BILLING:
        OrganisationTaxRegistration.objects.filter(
            organisation=organisation,
            is_primary_billing=True,
        ).exclude(id=getattr(tax_registration, 'id', None)).update(is_primary_billing=False)
        if tax_registration is None:
            OrganisationTaxRegistration.objects.filter(organisation=organisation).update(is_primary_billing=False)
        elif not tax_registration.is_primary_billing:
            tax_registration.is_primary_billing = True
            tax_registration.save(update_fields=['is_primary_billing', 'modified_at'])
    payload['tax_registration'] = tax_registration
    payload['gstin'] = tax_registration.identifier if tax_registration else None
    return payload


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

    payload = _sync_address_tax_registration(organisation, payload)

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

    if address.address_type in MANDATORY_ADDRESS_TYPES:
        if fields.get('is_active') is False:
            raise ValueError(f'{address.get_address_type_display()} cannot be deactivated.')
        if payload['address_type'] != address.address_type:
            raise ValueError(f'{address.get_address_type_display()} address type cannot be changed.')

    payload = _sync_address_tax_registration(organisation, payload)
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
        raise ValueError(f'{address.get_address_type_display()} cannot be deactivated.')
    if address.office_locations.filter(is_active=True).exists():
        raise ValueError('Deactivate linked office locations before deactivating this address.')

    address.is_active = False
    address.save(update_fields=['is_active', 'modified_at'])
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
        registration.identifier
        for registration in organisation.tax_registrations.filter(
            country_code='IN',
            registration_type=OrganisationTaxRegistrationType.GSTIN,
        )
        if registration.identifier[2:12] != normalized_pan
    ]
    if invalid_gst_addresses:
        raise ValueError('PAN cannot be changed because one or more GSTINs do not match the new PAN.')
    return normalized_pan


def invite_bootstrap_admin(organisation, actor=None):
    from apps.invitations.services import create_org_admin_invitation

    bootstrap_admin = getattr(organisation, 'bootstrap_admin', None)
    if bootstrap_admin is None:
        return None
    if bootstrap_admin.status == BootstrapAdminStatus.INVITE_ACCEPTED:
        return bootstrap_admin

    user, invite = create_org_admin_invitation(
        organisation=organisation,
        email=bootstrap_admin.email,
        first_name=bootstrap_admin.first_name,
        last_name=bootstrap_admin.last_name,
        invited_by=actor,
    )
    bootstrap_admin.invited_user = user
    bootstrap_admin.status = BootstrapAdminStatus.INVITE_PENDING
    bootstrap_admin.invitation_sent_at = timezone.now()
    bootstrap_admin.save(update_fields=['invited_user', 'status', 'invitation_sent_at', 'modified_at'])
    _bump_onboarding_stage(organisation, OrganisationOnboardingStage.ADMIN_INVITED)
    organisation.save(update_fields=['onboarding_stage', 'modified_at'])
    create_lifecycle_event(
        organisation,
        LifecycleEventType.ADMIN_INVITED,
        actor,
        {'email': bootstrap_admin.email},
    )
    log_audit_event(
        actor,
        'organisation.bootstrap_admin.invited',
        organisation=organisation,
        target=user,
        payload={'email': bootstrap_admin.email, 'invite_id': str(invite.id)},
    )
    return bootstrap_admin


def mark_bootstrap_admin_accepted(organisation, user):
    bootstrap_admin = getattr(organisation, 'bootstrap_admin', None)
    if bootstrap_admin is None:
        return None
    if normalize_email_address(bootstrap_admin.email) != normalize_email_address(user.email):
        return bootstrap_admin

    bootstrap_admin.invited_user = user
    bootstrap_admin.status = BootstrapAdminStatus.INVITE_ACCEPTED
    bootstrap_admin.accepted_at = timezone.now()
    bootstrap_admin.save(update_fields=['invited_user', 'status', 'accepted_at', 'modified_at'])
    return bootstrap_admin

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


def _derive_setup_step_statuses(organisation):
    from apps.approvals.models import ApprovalWorkflow
    from apps.departments.models import Department
    from apps.employees.models import Employee
    from apps.locations.models import OfficeLocation
    from apps.timeoff.models import HolidayCalendar, LeaveCycle, LeavePlan, OnDutyPolicy

    active_addresses = organisation.addresses.filter(is_active=True)
    return {
        OrgAdminSetupStep.PROFILE: bool(organisation.name and organisation.pan_number and organisation.entity_type),
        OrgAdminSetupStep.ADDRESSES: active_addresses.filter(address_type=OrganisationAddressType.REGISTERED).exists()
        and active_addresses.filter(address_type=OrganisationAddressType.BILLING).exists(),
        OrgAdminSetupStep.LOCATIONS: OfficeLocation.objects.filter(organisation=organisation, is_active=True).exists(),
        OrgAdminSetupStep.DEPARTMENTS: Department.objects.filter(organisation=organisation, is_active=True).exists(),
        OrgAdminSetupStep.HOLIDAYS: HolidayCalendar.objects.filter(organisation=organisation).exists(),
        OrgAdminSetupStep.POLICIES: (
            LeaveCycle.objects.filter(organisation=organisation).exists()
            or LeavePlan.objects.filter(organisation=organisation).exists()
            or OnDutyPolicy.objects.filter(organisation=organisation).exists()
            or ApprovalWorkflow.objects.filter(organisation=organisation).exists()
        ),
        OrgAdminSetupStep.EMPLOYEES: Employee.objects.filter(organisation=organisation).exists(),
    }


def ensure_org_admin_setup_state(organisation):
    if organisation.admin_setup_completed_at:
        return organisation

    step_statuses = _derive_setup_step_statuses(organisation)
    should_backfill_complete = (
        step_statuses[OrgAdminSetupStep.DEPARTMENTS]
        and step_statuses[OrgAdminSetupStep.HOLIDAYS]
        and step_statuses[OrgAdminSetupStep.POLICIES]
    ) or step_statuses[OrgAdminSetupStep.EMPLOYEES]

    if should_backfill_complete:
        organisation.admin_setup_started_at = organisation.admin_setup_started_at or organisation.created_at
        organisation.admin_setup_current_step = OrgAdminSetupStep.EMPLOYEES
        organisation.admin_setup_completed_at = timezone.now()
        organisation.admin_setup_completed_by = organisation.primary_admin_user
        organisation.save(
            update_fields=[
                'admin_setup_started_at',
                'admin_setup_current_step',
                'admin_setup_completed_at',
                'admin_setup_completed_by',
                'modified_at',
            ]
        )
    return organisation


def is_org_admin_setup_required(organisation):
    ensure_org_admin_setup_state(organisation)
    return organisation.admin_setup_completed_at is None


def get_org_admin_setup_state(organisation):
    ensure_org_admin_setup_state(organisation)
    step_statuses = _derive_setup_step_statuses(organisation)
    steps = [
        {
            'key': step,
            'label': OrgAdminSetupStep(step).label,
            'is_complete': step_statuses[step],
            'sequence': index + 1,
        }
        for index, step in enumerate(ORG_ADMIN_SETUP_SEQUENCE)
    ]
    current_step = organisation.admin_setup_current_step or ORG_ADMIN_SETUP_SEQUENCE[0]
    current_index = ORG_ADMIN_SETUP_SEQUENCE.index(current_step)
    return {
        'required': organisation.admin_setup_completed_at is None,
        'started_at': organisation.admin_setup_started_at,
        'current_step': current_step,
        'current_step_index': current_index + 1,
        'total_steps': len(ORG_ADMIN_SETUP_SEQUENCE),
        'completed_at': organisation.admin_setup_completed_at,
        'completed_by': organisation.admin_setup_completed_by,
        'steps': steps,
    }


def update_org_admin_setup_state(organisation, *, actor, current_step=None, completed=False):
    ensure_org_admin_setup_state(organisation)
    update_fields = []
    if organisation.admin_setup_started_at is None:
        organisation.admin_setup_started_at = timezone.now()
        update_fields.append('admin_setup_started_at')

    if current_step:
        if current_step not in ORG_ADMIN_SETUP_SEQUENCE:
            raise ValueError('Setup step is invalid.')
        organisation.admin_setup_current_step = current_step
        update_fields.append('admin_setup_current_step')

    if completed:
        organisation.admin_setup_current_step = OrgAdminSetupStep.EMPLOYEES
        organisation.admin_setup_completed_at = timezone.now()
        organisation.admin_setup_completed_by = actor
        update_fields.extend([
            'admin_setup_current_step',
            'admin_setup_completed_at',
            'admin_setup_completed_by',
        ])

    if update_fields:
        organisation.save(update_fields=[*update_fields, 'modified_at'])
        log_audit_event(
            actor,
            'organisation.admin_setup.updated',
            organisation=organisation,
            target=organisation,
            payload={
                'current_step': organisation.admin_setup_current_step,
                'completed_at': organisation.admin_setup_completed_at.isoformat()
                if organisation.admin_setup_completed_at
                else None,
            },
        )

    return organisation


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


def _resolve_act_as_target_org_admin(organisation, target_org_admin=None):
    if target_org_admin is not None:
        membership_exists = OrganisationMembership.objects.filter(
            organisation=organisation,
            user=target_org_admin,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        ).exists()
        if not membership_exists:
            raise ValueError('Selected target admin does not have active org admin access to this organisation.')
        return target_org_admin

    if organisation.primary_admin_user_id:
        return organisation.primary_admin_user

    membership = (
        OrganisationMembership.objects.select_related('user')
        .filter(
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        .order_by('created_at')
        .first()
    )
    return membership.user if membership is not None else None


def get_org_feature_flags_map(organisation):
    stored_flags = {
        feature_flag.feature_code: feature_flag.is_enabled
        for feature_flag in OrganisationFeatureFlag.objects.filter(organisation=organisation)
    }
    return {
        feature_code: stored_flags.get(feature_code, default_value)
        for feature_code, default_value in ORG_FEATURE_FLAG_DEFAULTS.items()
    }


def list_org_feature_flags(organisation):
    stored_flags = {
        feature_flag.feature_code: feature_flag
        for feature_flag in OrganisationFeatureFlag.objects.filter(organisation=organisation)
    }
    return [
        {
            'feature_code': feature_code,
            'label': OrganisationFeatureCode(feature_code).label,
            'is_enabled': stored_flags.get(feature_code).is_enabled if stored_flags.get(feature_code) else default_value,
            'is_default': feature_code not in stored_flags,
        }
        for feature_code, default_value in ORG_FEATURE_FLAG_DEFAULTS.items()
    ]


def is_org_feature_enabled(organisation, feature_code):
    if feature_code not in ORG_FEATURE_FLAG_DEFAULTS:
        raise ValueError(f'Unknown organisation feature code: {feature_code}')
    return get_org_feature_flags_map(organisation)[feature_code]


def set_org_feature_flag(organisation, *, feature_code, is_enabled, actor=None):
    if feature_code not in ORG_FEATURE_FLAG_DEFAULTS:
        raise ValueError(f'Unknown organisation feature code: {feature_code}')
    feature_flag, _ = OrganisationFeatureFlag.objects.update_or_create(
        organisation=organisation,
        feature_code=feature_code,
        defaults={'is_enabled': is_enabled},
    )
    log_audit_event(
        actor,
        'organisation.feature_flag.updated',
        organisation=organisation,
        target=feature_flag,
        payload={'feature_code': feature_code, 'is_enabled': is_enabled},
    )
    return feature_flag


@transaction.atomic
def stop_act_as_session(session, *, actor, request=None, reason=''):
    if not session.is_active:
        return session

    now = timezone.now()
    session.ended_at = now
    session.ended_by = actor
    session.save(update_fields=['ended_at', 'ended_by', 'modified_at'])

    create_lifecycle_event(
        session.organisation,
        LifecycleEventType.ACT_AS_STOPPED,
        actor,
        payload={'session_id': str(session.id), 'reason': reason},
    )
    log_audit_event(
        actor,
        'organisation.act_as.stopped',
        organisation=session.organisation,
        target=session,
        payload={'reason': reason, 'target_org_admin_id': str(session.target_org_admin_id) if session.target_org_admin_id else None},
        request=request,
    )
    return session


@transaction.atomic
def start_act_as_session(organisation, *, actor, reason, request=None, target_org_admin=None):
    if actor.account_type != AccountType.CONTROL_TOWER:
        raise ValueError('Only Control Tower users can start impersonation sessions.')

    now = timezone.now()
    active_sessions = list(
        ActAsSession.objects.select_for_update()
        .filter(actor=actor, ended_at__isnull=True, revoked_at__isnull=True)
    )
    for active_session in active_sessions:
        active_session.ended_at = now
        active_session.ended_by = actor
        active_session.save(update_fields=['ended_at', 'ended_by', 'modified_at'])

    resolved_target_org_admin = _resolve_act_as_target_org_admin(organisation, target_org_admin=target_org_admin)
    session = ActAsSession.objects.create(
        actor=actor,
        organisation=organisation,
        target_org_admin=resolved_target_org_admin,
        reason=reason.strip(),
        started_at=now,
        refreshed_at=now,
    )
    create_lifecycle_event(
        organisation,
        LifecycleEventType.ACT_AS_STARTED,
        actor,
        payload={
            'session_id': str(session.id),
            'reason': session.reason,
            'target_org_admin_id': str(session.target_org_admin_id) if session.target_org_admin_id else None,
        },
    )
    log_audit_event(
        actor,
        'organisation.act_as.started',
        organisation=organisation,
        target=session,
        payload={
            'reason': session.reason,
            'target_org_admin_id': str(session.target_org_admin_id) if session.target_org_admin_id else None,
        },
        request=request,
    )
    return session


def refresh_act_as_session(session, *, actor, request=None):
    if not session.is_active:
        raise ValueError('This impersonation session is no longer active.')
    session.refreshed_at = timezone.now()
    session.save(update_fields=['refreshed_at', 'modified_at'])
    create_lifecycle_event(
        session.organisation,
        LifecycleEventType.ACT_AS_REFRESHED,
        actor,
        payload={'session_id': str(session.id)},
    )
    log_audit_event(
        actor,
        'organisation.act_as.refreshed',
        organisation=session.organisation,
        target=session,
        payload={},
        request=request,
    )
    return session


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
    primary_admin,
    country_code=DEFAULT_COUNTRY_CODE,
    currency=DEFAULT_CURRENCY_CODE,
    entity_type=OrganisationEntityType.PRIVATE_LIMITED,
    licence_count=0,
    billing_same_as_registered=False,
):
    normalized_pan = normalize_pan_number(pan_number)
    normalized_addresses = validate_address_collection(addresses, normalized_pan)
    normalized_country_code = normalize_country_code(country_code)
    normalized_currency = normalize_currency_code(currency)
    normalized_primary_admin = {
        'first_name': (primary_admin.get('first_name') or '').strip(),
        'last_name': (primary_admin.get('last_name') or '').strip(),
        'email': normalize_email_address(primary_admin.get('email')),
        'phone': validate_phone_for_country(primary_admin.get('phone', ''), normalized_country_code),
    }
    if not normalized_primary_admin['email']:
        raise ValueError('Primary admin email is required.')

    with transaction.atomic():
        organisation = Organisation.objects.create(
            name=name,
            pan_number=normalized_pan,
            address=normalized_addresses[0]['line1'],
            phone='',
            email='',
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
        upsert_bootstrap_admin(
            organisation,
            actor=created_by,
            **normalized_primary_admin,
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
            {
                'licence_count': licence_count,
                'billing_same_as_registered': billing_same_as_registered,
                'primary_admin_email': normalized_primary_admin['email'],
            },
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
            payload={
                'licence_count': licence_count,
                'pan_number': normalized_pan,
                'primary_admin_email': normalized_primary_admin['email'],
            },
        )
        initialize_onboarding_checklist(organisation)
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

    primary_admin = fields.pop('primary_admin', None)
    if primary_admin and organisation.billing_status == OrganisationBillingStatus.PAID:
        raise ValueError('Primary admin details can only be edited before the first paid licence batch.')

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
    upsert_primary_legal_identifier(
        organisation,
        country_code=organisation.country_code,
        identifier_type=OrganisationLegalIdentifierType.PAN,
        identifier=organisation.pan_number,
    )
    if organisation.country_code == 'IN':
        organisation.tax_registrations.filter(
            country_code='IN',
            registration_type=OrganisationTaxRegistrationType.GSTIN,
        ).update(legal_identifier=organisation.legal_identifiers.filter(
            country_code='IN',
            identifier_type=OrganisationLegalIdentifierType.PAN,
            is_primary=True,
        ).first())

    if primary_admin:
        upsert_bootstrap_admin(
            organisation,
            actor=actor,
            first_name=primary_admin['first_name'],
            last_name=primary_admin['last_name'],
            email=primary_admin['email'],
            phone=primary_admin.get('phone', ''),
        )

    log_audit_event(
        actor,
        'organisation.updated',
        organisation=organisation,
        target=organisation,
        payload={
            **{key: value for key, value in fields.items() if value is not None},
            **({'primary_admin_email': primary_admin['email']} if primary_admin else {}),
        },
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
        org.save(update_fields=['licence_count', 'onboarding_stage', 'modified_at'])
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
        payment_provider=OrganisationBillingProvider.MANUAL,
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


def extend_licence_batch_expiry(batch, *, new_end_date, actor=None, reason=''):
    if batch.payment_status != LicenceBatchPaymentStatus.PAID:
        raise ValueError('Only paid licence batches can be extended.')
    if new_end_date <= batch.end_date:
        raise ValueError('New expiry date must be after the current expiry date.')

    previous_end_date = batch.end_date
    batch.end_date = new_end_date
    batch.save(update_fields=['end_date', 'modified_at'])
    log_audit_event(
        actor,
        'organisation.licence_batch.expiry_extended',
        organisation=batch.organisation,
        target=batch,
        payload={
            'previous_end_date': previous_end_date.isoformat(),
            'new_end_date': new_end_date.isoformat(),
            'reason': reason,
        },
    )
    return batch


def mark_licence_batch_paid(
    batch,
    paid_by=None,
    paid_at=None,
    payment_provider=None,
    payment_reference='',
    invoice_reference='',
):
    if batch.payment_status != LicenceBatchPaymentStatus.DRAFT:
        raise ValueError('Licence batch is already marked as paid.')

    resolved_paid_at = paid_at or timezone.localdate()
    with transaction.atomic():
        batch.payment_status = LicenceBatchPaymentStatus.PAID
        if payment_provider:
            batch.payment_provider = payment_provider
        if payment_reference:
            batch.payment_reference = payment_reference
        if invoice_reference:
            batch.invoice_reference = invoice_reference
        batch.paid_at = resolved_paid_at
        batch.paid_by = paid_by
        batch.save(
            update_fields=[
                'payment_status',
                'payment_provider',
                'payment_reference',
                'invoice_reference',
                'paid_at',
                'paid_by',
                'modified_at',
            ]
        )

        first_paid_batch = batch.organisation.status == OrganisationStatus.PENDING
        if batch.organisation.status == OrganisationStatus.PENDING:
            transition_organisation_state(
                batch.organisation,
                OrganisationStatus.PAID,
                transitioned_by=paid_by,
                note=f'Licence batch {batch.id} marked paid',
            )
        if first_paid_batch:
            invite_bootstrap_admin(batch.organisation, actor=paid_by)

    log_audit_event(
        paid_by,
        'organisation.licence_batch.paid',
        organisation=batch.organisation,
        target=batch,
        payload={
            'paid_at': resolved_paid_at.isoformat(),
            'payment_provider': batch.payment_provider,
            'payment_reference': batch.payment_reference,
            'invoice_reference': batch.invoice_reference,
        },
    )
    return batch


def aggregate_org_usage_stat(organisation: Organisation, *, snapshot_date: date | None = None) -> OrgUsageStat:
    from apps.approvals.models import ApprovalRun, ApprovalRunStatus
    from apps.attendance.models import AttendanceDay
    from apps.payroll.models import PayrollRun
    from apps.timeoff.models import LeaveRequest

    resolved_date = snapshot_date or timezone.localdate()
    employee_user_ids = set(
        Employee.objects.filter(organisation=organisation, status=EmployeeStatus.ACTIVE)
        .exclude(user__isnull=True)
        .values_list('user_id', flat=True)
    )
    admin_user_ids = set(
        OrganisationMembership.objects.filter(
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        ).exclude(user__isnull=True).values_list('user_id', flat=True)
    )
    usage_stat, _ = OrgUsageStat.objects.update_or_create(
        organisation=organisation,
        snapshot_date=resolved_date,
        defaults={
            'active_employees': Employee.objects.filter(organisation=organisation, status=EmployeeStatus.ACTIVE).count(),
            'active_users': len(employee_user_ids | admin_user_ids),
            'attendance_days_count': AttendanceDay.objects.filter(
                organisation=organisation,
                attendance_date=resolved_date,
            ).count(),
            'leave_requests_count': LeaveRequest.objects.filter(
                employee__organisation=organisation,
                created_at__date=resolved_date,
            ).count(),
            'payroll_runs_count': PayrollRun.objects.filter(
                organisation=organisation,
                created_at__date=resolved_date,
            ).count(),
            'pending_approvals_count': ApprovalRun.objects.filter(
                organisation=organisation,
                status=ApprovalRunStatus.PENDING,
            ).count(),
            'metadata': {'source': 'aggregation'},
        },
    )
    return usage_stat


def get_org_usage_analytics(organisation: Organisation, *, days: int = 30) -> dict:
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    stats = list(
        OrgUsageStat.objects.filter(
            organisation=organisation,
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date,
        ).order_by('snapshot_date')
    )
    if not stats:
        latest_existing = (
            OrgUsageStat.objects.filter(organisation=organisation)
            .order_by('-snapshot_date')
            .first()
        )
        stats = [latest_existing] if latest_existing is not None else [aggregate_org_usage_stat(organisation, snapshot_date=end_date)]
    latest = stats[-1]
    series_fields = [
        'active_employees',
        'active_users',
        'attendance_days_count',
        'leave_requests_count',
        'payroll_runs_count',
        'pending_approvals_count',
    ]
    return {
        'latest': {
            'snapshot_date': latest.snapshot_date.isoformat(),
            'active_employees': latest.active_employees,
            'active_users': latest.active_users,
            'attendance_days_count': latest.attendance_days_count,
            'leave_requests_count': latest.leave_requests_count,
            'payroll_runs_count': latest.payroll_runs_count,
            'pending_approvals_count': latest.pending_approvals_count,
            'metadata': latest.metadata,
        },
        'series': {
            field: [
                {'date': stat.snapshot_date.isoformat(), 'value': getattr(stat, field)}
                for stat in stats
            ]
            for field in series_fields
        },
    }


def request_tenant_data_export(organisation: Organisation, *, export_type: str, requested_by=None) -> TenantDataExportBatch:
    batch = TenantDataExportBatch.objects.create(
        organisation=organisation,
        requested_by=requested_by,
        export_type=export_type,
        status=TenantDataExportStatus.REQUESTED,
    )
    log_audit_event(
        requested_by,
        'organisation.data_export.requested',
        organisation=organisation,
        target=batch,
        payload={'export_type': export_type},
    )
    return batch


def list_tenant_data_exports(organisation: Organisation):
    return TenantDataExportBatch.objects.filter(organisation=organisation).select_related('requested_by')


def get_tenant_data_export(organisation: Organisation, export_batch_id) -> TenantDataExportBatch:
    return list_tenant_data_exports(organisation).get(id=export_batch_id)


def _write_csv_to_archive(archive: zipfile.ZipFile, file_name: str, fieldnames: list[str], rows: list[dict]) -> int:
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    archive.writestr(file_name, csv_buffer.getvalue().encode('utf-8'))
    return len(rows)


def _build_employee_export_rows(organisation: Organisation) -> list[dict]:
    employees = (
        Employee.all_objects.select_related('user', 'department', 'office_location')
        .filter(organisation=organisation)
        .order_by('employee_code', 'created_at')
    )
    return [
        {
            'employee_id': str(employee.id),
            'employee_code': employee.employee_code or '',
            'full_name': employee.user.full_name,
            'email': employee.user.email,
            'designation': employee.designation,
            'employment_type': employee.employment_type,
            'status': employee.status,
            'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
            'date_of_exit': employee.date_of_exit.isoformat() if employee.date_of_exit else '',
            'department': employee.department.name if employee.department_id else '',
            'office_location': employee.office_location.name if employee.office_location_id else '',
        }
        for employee in employees
    ]


def _build_leave_history_export_rows(organisation: Organisation) -> list[dict]:
    from apps.timeoff.models import LeaveRequest

    requests = (
        LeaveRequest.objects.select_related('employee__user', 'leave_type')
        .filter(employee__organisation=organisation)
        .order_by('-start_date', '-created_at')
    )
    return [
        {
            'leave_request_id': str(item.id),
            'employee_code': item.employee.employee_code or '',
            'employee_name': item.employee.user.full_name,
            'leave_type': item.leave_type.name,
            'start_date': item.start_date.isoformat(),
            'end_date': item.end_date.isoformat(),
            'total_units': str(item.total_units),
            'status': item.status,
            'reason': item.reason,
        }
        for item in requests
    ]


def _build_audit_log_export_rows(organisation: Organisation) -> list[dict]:
    logs = (
        AuditLog.objects.select_related('actor')
        .filter(organisation=organisation)
        .order_by('-created_at')
    )
    return [
        {
            'created_at': item.created_at.isoformat(),
            'action': item.action,
            'actor_email': item.actor.email if item.actor_id else '',
            'target_type': item.target_type,
            'target_id': str(item.target_id) if item.target_id else '',
            'ip_address': item.ip_address or '',
        }
        for item in logs
    ]


def _build_payslip_export_rows(organisation: Organisation) -> list[dict]:
    from apps.payroll.models import Payslip

    payslips = (
        Payslip.objects.select_related('employee__user', 'pay_run')
        .filter(organisation=organisation)
        .order_by('-period_year', '-period_month', '-created_at')
    )
    return [
        {
            'payslip_id': str(item.id),
            'slip_number': item.slip_number,
            'employee_code': item.employee.employee_code or '',
            'employee_name': item.employee.user.full_name,
            'period_year': item.period_year,
            'period_month': item.period_month,
            'pay_run': item.pay_run.name,
            'net_pay': item.snapshot.get('net_pay', ''),
            'rendered_text_present': bool(item.rendered_text),
        }
        for item in payslips
    ]


def _build_tenant_data_export_payload(batch: TenantDataExportBatch) -> tuple[io.BytesIO, str, dict]:
    export_builders = {
        TenantDataExportType.EMPLOYEES: (
            'employees.csv',
            ['employee_id', 'employee_code', 'full_name', 'email', 'designation', 'employment_type', 'status', 'date_of_joining', 'date_of_exit', 'department', 'office_location'],
            _build_employee_export_rows,
        ),
        TenantDataExportType.LEAVE_HISTORY: (
            'leave_history.csv',
            ['leave_request_id', 'employee_code', 'employee_name', 'leave_type', 'start_date', 'end_date', 'total_units', 'status', 'reason'],
            _build_leave_history_export_rows,
        ),
        TenantDataExportType.AUDIT_LOG: (
            'audit_log.csv',
            ['created_at', 'action', 'actor_email', 'target_type', 'target_id', 'ip_address'],
            _build_audit_log_export_rows,
        ),
        TenantDataExportType.PAYSLIPS: (
            'payslips.csv',
            ['payslip_id', 'slip_number', 'employee_code', 'employee_name', 'period_year', 'period_month', 'pay_run', 'net_pay', 'rendered_text_present'],
            _build_payslip_export_rows,
        ),
    }
    inner_file_name, fieldnames, builder = export_builders[batch.export_type]
    rows = builder(batch.organisation)
    file_buffer = io.BytesIO()
    with zipfile.ZipFile(file_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        row_count = _write_csv_to_archive(archive, inner_file_name, fieldnames, rows)
    file_buffer.seek(0)
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    export_name = f'{batch.organisation.slug}-{batch.export_type.lower()}-{timestamp}.zip'
    return file_buffer, export_name, {'row_count': row_count, 'inner_file_name': inner_file_name}


def generate_tenant_data_export_batch(export_batch: TenantDataExportBatch) -> TenantDataExportBatch:
    with transaction.atomic():
        batch = TenantDataExportBatch.objects.select_for_update().select_related('organisation').get(id=export_batch.id)
        if batch.status == TenantDataExportStatus.COMPLETED and batch.artifact_key:
            return batch
        batch.status = TenantDataExportStatus.PROCESSING
        batch.failure_reason = ''
        batch.save(update_fields=['status', 'failure_reason', 'modified_at'])

    try:
        file_buffer, file_name, metadata = _build_tenant_data_export_payload(batch)
        artifact_key = f'organisations/{batch.organisation.slug}/exports/{batch.id}/{file_name}'
        upload_file(file_buffer, artifact_key, 'application/zip')
        batch.status = TenantDataExportStatus.COMPLETED
        batch.artifact_key = artifact_key
        batch.file_name = file_name
        batch.content_type = 'application/zip'
        batch.file_size_bytes = len(file_buffer.getvalue())
        batch.generated_at = timezone.now()
        batch.failure_reason = ''
        batch.metadata = metadata
        batch.save(
            update_fields=[
                'status',
                'artifact_key',
                'file_name',
                'content_type',
                'file_size_bytes',
                'generated_at',
                'failure_reason',
                'metadata',
                'modified_at',
            ]
        )
        log_audit_event(
            batch.requested_by,
            'organisation.data_export.completed',
            organisation=batch.organisation,
            target=batch,
            payload={'export_type': batch.export_type, 'artifact_key': batch.artifact_key},
        )
    except Exception as exc:  # noqa: BLE001
        batch.status = TenantDataExportStatus.FAILED
        batch.failure_reason = str(exc)
        batch.save(update_fields=['status', 'failure_reason', 'modified_at'])
        log_audit_event(
            batch.requested_by,
            'organisation.data_export.failed',
            organisation=batch.organisation,
            target=batch,
            payload={'export_type': batch.export_type, 'failure_reason': str(exc)},
        )
    return batch


def generate_tenant_data_export_download_url(batch: TenantDataExportBatch, *, actor=None, request=None, expiry=900) -> str:
    if batch.status != TenantDataExportStatus.COMPLETED or not batch.artifact_key:
        raise ValueError('Export is not ready for download.')
    url = generate_presigned_url(batch.artifact_key, expiry=expiry)
    log_audit_event(
        actor,
        'organisation.data_export.download_url_generated',
        organisation=batch.organisation,
        target=batch,
        payload={'export_type': batch.export_type, 'expires_in_seconds': expiry},
        request=request,
    )
    return url


def _get_razorpay_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()


def process_razorpay_webhook(raw_body: bytes, signature: str) -> OrganisationBillingEvent:
    secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    if not secret:
        raise ValueError('Razorpay webhook secret is not configured.')
    if not signature or not hmac.compare_digest(_get_razorpay_signature(raw_body, secret), signature):
        raise ValueError('Invalid Razorpay signature.')

    payload = json.loads(raw_body.decode('utf-8'))
    event_type = payload.get('event', '')
    payment_entity = ((payload.get('payload') or {}).get('payment') or {}).get('entity') or {}
    notes = payment_entity.get('notes') or {}
    organisation_id = notes.get('organisation_id')
    batch_id = notes.get('licence_batch_id')
    payment_id = payment_entity.get('id', '')
    invoice_reference = payment_entity.get('invoice_id', '') or notes.get('invoice_reference', '')
    provider_event_id = f'{event_type}:{payment_id or payload.get("id") or payload.get("created_at")}'

    if not organisation_id or not batch_id:
        raise ValueError('Razorpay payload must include organisation_id and licence_batch_id notes.')

    organisation = Organisation.objects.get(id=organisation_id)
    batch = OrganisationLicenceBatch.objects.get(id=batch_id, organisation=organisation)
    billing_event, created = OrganisationBillingEvent.objects.get_or_create(
        provider_event_id=provider_event_id,
        defaults={
            'organisation': organisation,
            'licence_batch': batch,
            'provider': OrganisationBillingProvider.RAZORPAY,
            'event_type': event_type,
            'provider_payment_id': payment_id,
            'invoice_reference': invoice_reference,
            'status': OrganisationBillingEventStatus.RECEIVED,
            'payload': payload,
        },
    )
    if not created:
        return billing_event

    billing_event.payload = payload
    billing_event.provider_payment_id = payment_id
    billing_event.invoice_reference = invoice_reference

    event_created_at = payload.get('created_at')
    paid_at = (
        datetime.fromtimestamp(event_created_at, tz=UTC).date()
        if event_created_at
        else timezone.localdate()
    )

    if event_type in {'payment.captured', 'order.paid'}:
        if batch.payment_status == LicenceBatchPaymentStatus.DRAFT:
            mark_licence_batch_paid(
                batch,
                paid_at=paid_at,
                payment_provider=OrganisationBillingProvider.RAZORPAY,
                payment_reference=payment_id,
                invoice_reference=invoice_reference,
            )
        billing_event.status = OrganisationBillingEventStatus.PROCESSED
        billing_event.processed_at = timezone.now()
    else:
        billing_event.status = OrganisationBillingEventStatus.IGNORED
        billing_event.processed_at = timezone.now()

    billing_event.save(
        update_fields=[
            'payload',
            'provider_payment_id',
            'invoice_reference',
            'status',
            'processed_at',
            'modified_at',
        ]
    )
    return billing_event


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
    organisation.save(update_fields=['primary_admin_user', 'onboarding_stage', 'modified_at'])
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


def deactivate_org_admin_membership(organisation, user, actor=None):
    membership = OrganisationMembership.objects.select_related('user').filter(
        organisation=organisation,
        user=user,
        is_org_admin=True,
    ).first()
    if membership is None:
        raise ValueError('Organisation admin membership not found.')
    if membership.status != OrganisationMembershipStatus.ACTIVE:
        raise ValueError('Only active organisation admins can be deactivated.')
    if organisation.primary_admin_user_id == user.id:
        raise ValueError('Reassign the primary organisation admin before deactivating this admin.')
    if not OrganisationMembership.objects.filter(
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).exclude(id=membership.id).exists():
        raise ValueError('At least one active organisation admin must remain assigned.')

    membership.status = OrganisationMembershipStatus.INACTIVE
    membership.save(update_fields=['status', 'modified_at'])
    sync_user_role(user)
    log_audit_event(
        actor,
        'organisation.admin.deactivated',
        organisation=organisation,
        target=user,
        payload={'email': user.email},
    )
    return membership


def reactivate_org_admin_membership(organisation, user, actor=None):
    membership = OrganisationMembership.objects.select_related('user').filter(
        organisation=organisation,
        user=user,
        is_org_admin=True,
    ).first()
    if membership is None:
        raise ValueError('Organisation admin membership not found.')
    if membership.status != OrganisationMembershipStatus.INACTIVE:
        raise ValueError('Only inactive organisation admins can be reactivated.')
    if not user.is_active:
        raise ValueError('This admin account is inactive. Resend the invite instead.')

    membership.status = OrganisationMembershipStatus.ACTIVE
    if membership.accepted_at is None:
        membership.accepted_at = timezone.now()
        membership.save(update_fields=['status', 'accepted_at', 'modified_at'])
    else:
        membership.save(update_fields=['status', 'modified_at'])
    sync_user_role(user)
    log_audit_event(
        actor,
        'organisation.admin.reactivated',
        organisation=organisation,
        target=user,
        payload={'email': user.email},
    )
    return membership


def revoke_org_admin_membership_invitation(organisation, user, actor=None):
    from apps.invitations.models import Invitation, InvitationRole, InvitationStatus

    membership = OrganisationMembership.objects.select_related('user').filter(
        organisation=organisation,
        user=user,
        is_org_admin=True,
    ).first()
    if membership is None:
        raise ValueError('Organisation admin membership not found.')
    if membership.status != OrganisationMembershipStatus.INVITED:
        raise ValueError('Only invited organisation admins can be revoked.')

    Invitation.objects.filter(
        organisation=organisation,
        user=user,
        role=InvitationRole.ORG_ADMIN,
        status=InvitationStatus.PENDING,
    ).update(status=InvitationStatus.REVOKED, revoked_at=timezone.now())

    membership.status = OrganisationMembershipStatus.REVOKED
    membership.save(update_fields=['status', 'modified_at'])

    bootstrap_admin = getattr(organisation, 'bootstrap_admin', None)
    if bootstrap_admin and normalize_email_address(bootstrap_admin.email) == normalize_email_address(user.email):
        bootstrap_admin.status = BootstrapAdminStatus.DRAFT
        bootstrap_admin.invited_user = None
        bootstrap_admin.invitation_sent_at = None
        bootstrap_admin.save(update_fields=['status', 'invited_user', 'invitation_sent_at', 'modified_at'])
        if organisation.primary_admin_user_id == user.id:
            organisation.primary_admin_user = None
            organisation.save(update_fields=['primary_admin_user', 'modified_at'])

    sync_user_role(user)
    log_audit_event(
        actor,
        'organisation.admin.invitation.revoked',
        organisation=organisation,
        target=user,
        payload={'email': user.email},
    )
    return membership


def mark_master_data_configured(organisation, actor=None):
    step_states = _build_onboarding_step_states(organisation)
    if all(
        step_states[step]["is_complete"]
        for step in (
            OnboardingStepCode.DEPARTMENTS,
            OnboardingStepCode.LOCATIONS,
            OnboardingStepCode.LEAVE,
            OnboardingStepCode.PAYROLL,
            OnboardingStepCode.POLICIES,
            OnboardingStepCode.HOLIDAYS,
        )
    ):
        if organisation.onboarding_stage != OrganisationOnboardingStage.MASTER_DATA_CONFIGURED:
            organisation.onboarding_stage = OrganisationOnboardingStage.MASTER_DATA_CONFIGURED
            organisation.save(update_fields=['onboarding_stage', 'modified_at'])
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
    organisation.save(update_fields=['onboarding_stage', 'modified_at'])
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


def create_organisation_note(organisation, body, created_by):
    note = OrganisationNote.objects.create(
        organisation=organisation,
        body=body.strip(),
        created_by=created_by,
    )
    log_audit_event(
        created_by,
        'organisation.note.created',
        organisation=organisation,
        target=note,
        payload={'body_preview': note.body[:120]},
    )
    return note


ONBOARDING_STEP_ACTIONS = {
    OnboardingStepCode.ADMINS: 'admins',
    OnboardingStepCode.DEPARTMENTS: 'configuration',
    OnboardingStepCode.LOCATIONS: 'configuration',
    OnboardingStepCode.LEAVE: 'configuration',
    OnboardingStepCode.PAYROLL: 'configuration',
    OnboardingStepCode.POLICIES: 'approvals',
    OnboardingStepCode.HOLIDAYS: 'holidays',
    OnboardingStepCode.FIRST_EMPLOYEE: 'employees',
}

ONBOARDING_STEP_ORDER = [step for step, _label in OnboardingStepCode.choices]


def _build_onboarding_step_states(organisation: Organisation) -> dict[str, dict]:
    from apps.approvals.models import ApprovalWorkflow
    from apps.attendance.models import AttendancePolicy
    from apps.departments.models import Department
    from apps.locations.models import OfficeLocation
    from apps.payroll.models import PayrollTaxSlabSet
    from apps.timeoff.models import HolidayCalendar, LeaveCycle, LeavePlan

    has_active_admin = OrganisationMembership.objects.filter(
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).exists()
    has_departments = Department.objects.filter(organisation=organisation, is_active=True).exists()
    has_locations = OfficeLocation.objects.filter(organisation=organisation, is_active=True).exists()
    has_leave_policy = (
        LeaveCycle.objects.filter(organisation=organisation, is_active=True).exists()
        or LeavePlan.objects.filter(organisation=organisation, is_active=True).exists()
    )
    has_payroll_setup = PayrollTaxSlabSet.objects.filter(organisation=organisation, is_active=True).exists()
    has_attendance_policy = AttendancePolicy.objects.filter(organisation=organisation, is_active=True).exists()
    has_approval_workflow = ApprovalWorkflow.objects.filter(organisation=organisation, is_active=True).exists()
    has_published_holidays = HolidayCalendar.objects.filter(
        organisation=organisation,
        status='PUBLISHED',
        holidays__isnull=False,
    ).distinct().exists()
    has_first_employee = Employee.objects.filter(organisation=organisation).exists()

    return {
        OnboardingStepCode.ADMINS: {
            'is_complete': has_active_admin,
            'blockers': [] if has_active_admin else ['No active organisation admin'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.ADMINS],
        },
        OnboardingStepCode.DEPARTMENTS: {
            'is_complete': has_departments,
            'blockers': [] if has_departments else ['No department configured'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.DEPARTMENTS],
        },
        OnboardingStepCode.LOCATIONS: {
            'is_complete': has_locations,
            'blockers': [] if has_locations else ['No office location configured'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.LOCATIONS],
        },
        OnboardingStepCode.LEAVE: {
            'is_complete': has_leave_policy,
            'blockers': [] if has_leave_policy else ['No leave cycle or leave plan configured'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.LEAVE],
        },
        OnboardingStepCode.PAYROLL: {
            'is_complete': has_payroll_setup,
            'blockers': [] if has_payroll_setup else ['No active payroll tax slab set'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.PAYROLL],
        },
        OnboardingStepCode.POLICIES: {
            'is_complete': has_attendance_policy and has_approval_workflow,
            'blockers': [
                *([] if has_attendance_policy else ['No attendance policy configured']),
                *([] if has_approval_workflow else ['No approval workflow configured']),
            ],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.POLICIES],
        },
        OnboardingStepCode.HOLIDAYS: {
            'is_complete': has_published_holidays,
            'blockers': [] if has_published_holidays else ['No published holiday calendar with holidays'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.HOLIDAYS],
        },
        OnboardingStepCode.FIRST_EMPLOYEE: {
            'is_complete': has_first_employee,
            'blockers': [] if has_first_employee else ['No employee invited'],
            'action': ONBOARDING_STEP_ACTIONS[OnboardingStepCode.FIRST_EMPLOYEE],
        },
    }


def _completion_source(item: OnboardingChecklist) -> str | None:
    if not item.is_completed:
        return None
    if item.completed_by_id is None:
        return 'SYSTEM'
    if getattr(item.completed_by, 'account_type', None) == AccountType.CONTROL_TOWER:
        return 'CONTROL_TOWER'
    return 'WORKFORCE'


def _sync_onboarding_stage(organisation: Organisation, step_states: dict[str, dict], *, actor=None) -> None:
    master_data_complete = all(
        step_states[step]['is_complete']
        for step in (
            OnboardingStepCode.DEPARTMENTS,
            OnboardingStepCode.LOCATIONS,
            OnboardingStepCode.LEAVE,
            OnboardingStepCode.PAYROLL,
            OnboardingStepCode.POLICIES,
            OnboardingStepCode.HOLIDAYS,
        )
    )
    if master_data_complete:
        mark_master_data_configured(organisation, actor=actor)
    if step_states[OnboardingStepCode.FIRST_EMPLOYEE]['is_complete']:
        mark_employee_invited(organisation, actor=actor)


def get_ct_onboarding_checklist(organisation):
    """Return a structured CT onboarding checklist derived from organisation state."""
    from apps.approvals.models import ApprovalWorkflow
    from apps.departments.models import Department
    from apps.locations.models import OfficeLocation
    from apps.payroll.models import PayrollTaxSlabSet
    from apps.timeoff.models import HolidayCalendar, LeaveCycle, LeavePlan

    has_name = bool(organisation.name and organisation.pan_number and organisation.entity_type)
    addresses = list(organisation.addresses.filter(is_active=True).values_list('address_type', flat=True))
    has_registered_address = OrganisationAddressType.REGISTERED in addresses
    has_billing_address = OrganisationAddressType.BILLING in addresses
    has_any_batch = organisation.licence_batches.exists()
    has_paid_batch = organisation.licence_batches.filter(
        payment_status=LicenceBatchPaymentStatus.PAID,
    ).exists()
    has_bootstrap_admin = OrganisationBootstrapAdmin.objects.filter(organisation=organisation).exists()
    has_active_admin = OrganisationMembership.objects.filter(
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).exists()
    has_locations = OfficeLocation.objects.filter(organisation=organisation, is_active=True).exists()
    has_departments = Department.objects.filter(organisation=organisation, is_active=True).exists()
    has_holidays = HolidayCalendar.objects.filter(organisation=organisation).exists()
    has_leave_policy = (
        LeaveCycle.objects.filter(organisation=organisation).exists()
        or LeavePlan.objects.filter(organisation=organisation).exists()
    )
    has_approvals = ApprovalWorkflow.objects.filter(organisation=organisation).exists()
    has_tax_slabs = PayrollTaxSlabSet.objects.filter(organisation=organisation, is_active=True).exists()
    has_employees = Employee.objects.filter(organisation=organisation).exists()

    stages = [
        {
            'id': 'ORG_CREATED',
            'label': 'Organisation created',
            'is_complete': has_name and has_registered_address and has_billing_address,
            'items': [
                {'label': 'Legal details (name, PAN, entity type)', 'is_complete': has_name, 'action': 'details'},
                {'label': 'Registered address', 'is_complete': has_registered_address, 'action': 'details'},
                {'label': 'Billing address', 'is_complete': has_billing_address, 'action': 'details'},
            ],
        },
        {
            'id': 'LICENCES_ASSIGNED',
            'label': 'Licences assigned',
            'is_complete': has_any_batch,
            'items': [
                {'label': 'At least one licence batch created', 'is_complete': has_any_batch, 'action': 'licences'},
            ],
        },
        {
            'id': 'PAYMENT_CONFIRMED',
            'label': 'Payment confirmed',
            'is_complete': has_paid_batch,
            'items': [
                {'label': 'First licence batch marked as paid', 'is_complete': has_paid_batch, 'action': 'licences'},
            ],
        },
        {
            'id': 'ADMIN_INVITED',
            'label': 'Primary admin invited',
            'is_complete': has_bootstrap_admin,
            'items': [
                {'label': 'Bootstrap admin configured', 'is_complete': has_bootstrap_admin, 'action': 'details'},
            ],
        },
        {
            'id': 'ADMIN_ACTIVATED',
            'label': 'Admin activated',
            'is_complete': has_active_admin,
            'items': [
                {'label': 'At least one active org admin', 'is_complete': has_active_admin, 'action': 'admins'},
            ],
        },
        {
            'id': 'MASTER_DATA_CONFIGURED',
            'label': 'Master data configured',
            'is_complete': has_locations and has_departments and has_holidays and has_leave_policy and has_approvals,
            'items': [
                {'label': 'Office location', 'is_complete': has_locations, 'action': 'configuration'},
                {'label': 'Department', 'is_complete': has_departments, 'action': 'configuration'},
                {'label': 'Holiday calendar', 'is_complete': has_holidays, 'action': 'holidays'},
                {'label': 'Leave cycle or leave plan', 'is_complete': has_leave_policy, 'action': 'configuration'},
                {'label': 'Approval workflow', 'is_complete': has_approvals, 'action': 'approvals'},
                {'label': 'Payroll tax slab set (optional)', 'is_complete': has_tax_slabs, 'action': 'configuration'},
            ],
        },
        {
            'id': 'EMPLOYEES_INVITED',
            'label': 'Employees invited',
            'is_complete': has_employees,
            'items': [
                {'label': 'At least one employee invited', 'is_complete': has_employees, 'action': 'employees'},
            ],
        },
    ]

    mandatory_blockers = []
    if not has_paid_batch:
        mandatory_blockers.append('Licence payment not confirmed')
    if not has_active_admin:
        mandatory_blockers.append('No active organisation admin')
    if not has_locations:
        mandatory_blockers.append('No office location configured')
    if not has_departments:
        mandatory_blockers.append('No department configured')
    if not has_holidays:
        mandatory_blockers.append('No holiday calendar configured')

    return {
        'current_stage': organisation.onboarding_stage,
        'stages': stages,
        'can_activate': len(mandatory_blockers) == 0,
        'activation_blockers': mandatory_blockers,
    }


def initialize_onboarding_checklist(organisation: Organisation) -> None:
    """Create 8 onboarding checklist items for a new organisation."""
    steps = [code for code, _ in OnboardingStepCode.choices]
    OnboardingChecklist.objects.bulk_create([
        OnboardingChecklist(organisation=organisation, step=step)
        for step in steps
    ], ignore_conflicts=True)


def sync_onboarding_progress(organisation: Organisation, *, actor=None) -> dict:
    initialize_onboarding_checklist(organisation)
    items = {
        item.step: item
        for item in OnboardingChecklist.objects.filter(organisation=organisation).select_related('completed_by')
    }
    step_states = _build_onboarding_step_states(organisation)
    now = timezone.now()

    for step in ONBOARDING_STEP_ORDER:
        item = items[step]
        state = step_states[step]
        if state['is_complete'] and not item.is_completed:
            item.is_completed = True
            item.completed_at = now
            item.completed_by = None
            item.save(update_fields=['is_completed', 'completed_at', 'completed_by', 'modified_at'])
        elif not state['is_complete'] and item.is_completed:
            item.is_completed = False
            item.completed_at = None
            item.completed_by = None
            item.save(update_fields=['is_completed', 'completed_at', 'completed_by', 'modified_at'])

    _sync_onboarding_stage(organisation, step_states, actor=actor)
    return get_onboarding_progress(organisation)


def mark_onboarding_step_complete(
    organisation: Organisation, step: str, *, actor
) -> OnboardingChecklist:
    initialize_onboarding_checklist(organisation)
    step_states = _build_onboarding_step_states(organisation)
    state = step_states[step]
    if not state['is_complete']:
        raise ValueError(state['blockers'][0] if state['blockers'] else 'Cannot complete onboarding step.')

    from django.utils import timezone as tz
    item = OnboardingChecklist.objects.get(organisation=organisation, step=step)
    item.is_completed = True
    item.completed_at = tz.now()
    item.completed_by = actor
    item.save(update_fields=["is_completed", "completed_at", "completed_by", "modified_at"])
    log_audit_event(
        actor,
        'organisation.onboarding.step.completed',
        organisation=organisation,
        target=organisation,
        payload={'step': step},
    )
    _sync_onboarding_stage(organisation, step_states, actor=actor)
    return item


def reset_onboarding_step(
    organisation: Organisation, step: str, *, actor, reason: str = ''
) -> OnboardingChecklist:
    initialize_onboarding_checklist(organisation)
    item = OnboardingChecklist.objects.get(organisation=organisation, step=step)
    item.is_completed = False
    item.completed_at = None
    item.completed_by = None
    item.save(update_fields=["is_completed", "completed_at", "completed_by", "modified_at"])
    log_audit_event(
        actor,
        'organisation.onboarding.step.reset',
        organisation=organisation,
        target=organisation,
        payload={'step': step, 'reason': reason},
    )
    return item


def get_onboarding_progress(organisation: Organisation) -> dict:
    initialize_onboarding_checklist(organisation)
    items_by_step = {
        item.step: item
        for item in OnboardingChecklist.objects.filter(organisation=organisation).select_related('completed_by')
    }
    step_states = _build_onboarding_step_states(organisation)
    items = [items_by_step[step] for step in ONBOARDING_STEP_ORDER]
    completed = sum(1 for i in items if i.is_completed)
    return {
        'current_stage': organisation.onboarding_stage,
        "steps": [
            {
                'step': i.step,
                'label': dict(OnboardingStepCode.choices)[i.step],
                'is_completed': i.is_completed,
                'completed_at': i.completed_at,
                'completion_source': _completion_source(i),
                'blockers': step_states[i.step]['blockers'],
                'can_reset': i.is_completed,
                'is_actionable': True,
                'action': step_states[i.step]['action'],
            }
            for i in items
        ],
        "completed_count": completed,
        "total_count": len(items),
        "percent_complete": round(completed / len(items) * 100) if items else 0,
    }
