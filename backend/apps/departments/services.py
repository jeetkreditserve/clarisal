from django.db import IntegrityError, transaction

from apps.audit.services import log_audit_event
from apps.employees.models import EmployeeStatus
from apps.organisations.services import mark_master_data_configured

from .models import Department


def create_department(organisation, actor=None, **fields):
    try:
        with transaction.atomic():
            department = Department.objects.create(organisation=organisation, **fields)
            mark_master_data_configured(organisation, actor)
            log_audit_event(actor, 'department.created', organisation=organisation, target=department, payload=fields)
            return department
    except IntegrityError as exc:
        raise ValueError('A department with this name already exists.') from exc


def update_department(department, actor=None, **fields):
    for attr, value in fields.items():
        setattr(department, attr, value)
    try:
        with transaction.atomic():
            department.save()
            mark_master_data_configured(department.organisation, actor)
            log_audit_event(
                actor,
                'department.updated',
                organisation=department.organisation,
                target=department,
                payload=fields,
            )
            return department
    except IntegrityError as exc:
        raise ValueError('A department with this name already exists.') from exc


def deactivate_department(department, actor=None):
    has_active_employees = department.employees.filter(
        status__in=[EmployeeStatus.INVITED, EmployeeStatus.ACTIVE, EmployeeStatus.INACTIVE]
    ).exists()
    if has_active_employees:
        raise ValueError('Cannot deactivate a department that still has active employees.')
    department.is_active = False
    department.save(update_fields=['is_active', 'updated_at'])
    log_audit_event(actor, 'department.deactivated', organisation=department.organisation, target=department)
    return department
