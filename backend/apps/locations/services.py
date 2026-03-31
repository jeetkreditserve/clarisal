from django.db import IntegrityError, transaction

from apps.audit.services import log_audit_event
from apps.employees.models import EmployeeStatus
from apps.organisations.models import OrganisationAddress
from apps.organisations.services import mark_master_data_configured

from .models import OfficeLocation

ACTIVE_LOCATION_EMPLOYEE_STATUSES = [
    EmployeeStatus.INVITED,
    EmployeeStatus.PENDING,
    EmployeeStatus.ACTIVE,
]


def _get_address(organisation, organisation_address_id):
    address = OrganisationAddress.objects.filter(
        organisation=organisation,
        id=organisation_address_id,
        is_active=True,
    ).first()
    if address is None:
        raise ValueError('Office location must be linked to an active organisation address.')
    return address


def _sync_address_fields(location, organisation_address):
    location.organisation_address = organisation_address
    location.address = organisation_address.line1
    location.city = organisation_address.city
    location.state = organisation_address.state
    location.country = organisation_address.country
    location.pincode = organisation_address.pincode


def create_location(organisation, actor=None, **fields):
    organisation_address = _get_address(organisation, fields.pop('organisation_address_id'))
    try:
        with transaction.atomic():
            location = OfficeLocation(organisation=organisation, **fields)
            _sync_address_fields(location, organisation_address)
            location.save()
            mark_master_data_configured(organisation, actor)
            log_audit_event(
                actor,
                'location.created',
                organisation=organisation,
                target=location,
                payload={**fields, 'organisation_address_id': str(organisation_address.id)},
            )
            return location
    except IntegrityError as exc:
        raise ValueError('A location with this name already exists.') from exc


def update_location(location, actor=None, **fields):
    if 'organisation_address_id' in fields:
        organisation_address = _get_address(location.organisation, fields.pop('organisation_address_id'))
        _sync_address_fields(location, organisation_address)
    for attr, value in fields.items():
        setattr(location, attr, value)
    try:
        with transaction.atomic():
            location.save()
            mark_master_data_configured(location.organisation, actor)
            log_audit_event(
                actor,
                'location.updated',
                organisation=location.organisation,
                target=location,
                payload=fields,
            )
            return location
    except IntegrityError as exc:
        raise ValueError('A location with this name already exists.') from exc


def deactivate_location(location, actor=None):
    if location.employees.filter(status__in=ACTIVE_LOCATION_EMPLOYEE_STATUSES).exists():
        raise ValueError('Cannot deactivate an office location that still has invited, pending, or active employees.')
    location.is_active = False
    location.save(update_fields=['is_active', 'updated_at'])
    log_audit_event(actor, 'location.deactivated', organisation=location.organisation, target=location)
    return location
