from django.db import IntegrityError, transaction

from apps.audit.services import log_audit_event
from apps.organisations.services import mark_master_data_configured

from .models import OfficeLocation


def create_location(organisation, actor=None, **fields):
    try:
        with transaction.atomic():
            location = OfficeLocation.objects.create(organisation=organisation, **fields)
            mark_master_data_configured(organisation, actor)
            log_audit_event(actor, 'location.created', organisation=organisation, target=location, payload=fields)
            return location
    except IntegrityError as exc:
        raise ValueError('A location with this name already exists.') from exc


def update_location(location, actor=None, **fields):
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
    location.is_active = False
    location.save(update_fields=['is_active', 'updated_at'])
    log_audit_event(actor, 'location.deactivated', organisation=location.organisation, target=location)
    return location
