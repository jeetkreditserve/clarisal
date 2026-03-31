from django.db import IntegrityError, transaction

from apps.audit.services import log_audit_event
from apps.employees.models import EmployeeStatus
from apps.organisations.services import mark_master_data_configured

from .models import Department

ACTIVE_DEPARTMENT_EMPLOYEE_STATUSES = [
    EmployeeStatus.INVITED,
    EmployeeStatus.PENDING,
    EmployeeStatus.ACTIVE,
]


def _resolve_parent_department(organisation, parent_department_id, department=None):
    if not parent_department_id:
        return None

    parent = Department.objects.filter(
        organisation=organisation,
        id=parent_department_id,
        is_active=True,
    ).first()
    if parent is None:
        raise ValueError('Parent department must belong to the same organisation and be active.')
    if department and parent.id == department.id:
        raise ValueError('A department cannot be its own parent.')

    cursor = parent
    while cursor is not None:
        if department and cursor.id == department.id:
            raise ValueError('Department hierarchy cannot contain cycles.')
        cursor = cursor.parent_department
    return parent


def create_department(organisation, actor=None, **fields):
    if 'parent_department_id' in fields:
        fields['parent_department'] = _resolve_parent_department(
            organisation,
            fields.pop('parent_department_id'),
        )
    try:
        with transaction.atomic():
            department = Department.objects.create(organisation=organisation, **fields)
            mark_master_data_configured(organisation, actor)
            log_audit_event(actor, 'department.created', organisation=organisation, target=department, payload=fields)
            return department
    except IntegrityError as exc:
        raise ValueError('A department with this name already exists.') from exc


def update_department(department, actor=None, **fields):
    if 'parent_department_id' in fields:
        department.parent_department = _resolve_parent_department(
            department.organisation,
            fields.pop('parent_department_id'),
            department=department,
        )
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
    if department.child_departments.filter(is_active=True).exists():
        raise ValueError('Cannot deactivate a department that still has active child departments.')
    has_active_employees = department.employees.filter(
        status__in=ACTIVE_DEPARTMENT_EMPLOYEE_STATUSES
    ).exists()
    if has_active_employees:
        raise ValueError('Cannot deactivate a department that still has active employees.')
    department.is_active = False
    department.save(update_fields=['is_active', 'updated_at'])
    log_audit_event(actor, 'department.deactivated', organisation=department.organisation, target=department)
    return department
