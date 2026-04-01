from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit_event

from .models import Notice, NoticeAudienceType, NoticeStatus


def create_notice(organisation, actor=None, department_ids=None, office_location_ids=None, employee_ids=None, **fields):
    with transaction.atomic():
        notice = Notice.objects.create(
            organisation=organisation,
            created_by=actor,
            modified_by=actor,
            **fields,
        )
        if department_ids:
            notice.departments.set(department_ids)
        if office_location_ids:
            notice.office_locations.set(office_location_ids)
        if employee_ids:
            notice.employees.set(employee_ids)
    log_audit_event(actor, 'notice.created', organisation=organisation, target=notice)
    return notice


def update_notice(notice, actor=None, department_ids=None, office_location_ids=None, employee_ids=None, **fields):
    with transaction.atomic():
        for attr, value in fields.items():
            setattr(notice, attr, value)
        notice.modified_by = actor
        notice.save()
        if department_ids is not None:
            notice.departments.set(department_ids)
        if office_location_ids is not None:
            notice.office_locations.set(office_location_ids)
        if employee_ids is not None:
            notice.employees.set(employee_ids)
    log_audit_event(actor, 'notice.updated', organisation=notice.organisation, target=notice)
    return notice


def publish_notice(notice, actor=None):
    notice.status = NoticeStatus.PUBLISHED
    notice.published_at = timezone.now()
    notice.modified_by = actor
    notice.save(update_fields=['status', 'published_at', 'modified_by', 'modified_at'])
    log_audit_event(actor, 'notice.published', organisation=notice.organisation, target=notice)
    return notice


def get_visible_notices(employee):
    now = timezone.now()
    queryset = Notice.objects.filter(
        organisation=employee.organisation,
        status__in=[NoticeStatus.PUBLISHED, NoticeStatus.SCHEDULED],
    ).order_by('-published_at', '-created_at')

    visible = []
    for notice in queryset:
        if notice.status == NoticeStatus.SCHEDULED and (notice.scheduled_for is None or notice.scheduled_for > now):
            continue
        if notice.audience_type == NoticeAudienceType.ALL_EMPLOYEES:
            visible.append(notice)
            continue
        if notice.audience_type == NoticeAudienceType.DEPARTMENTS and employee.department_id and notice.departments.filter(id=employee.department_id).exists():
            visible.append(notice)
            continue
        if notice.audience_type == NoticeAudienceType.OFFICE_LOCATIONS and employee.office_location_id and notice.office_locations.filter(id=employee.office_location_id).exists():
            visible.append(notice)
            continue
        if notice.audience_type == NoticeAudienceType.SPECIFIC_EMPLOYEES and notice.employees.filter(id=employee.id).exists():
            visible.append(notice)
            continue
    return visible


def get_employee_events(employee):
    today = timezone.localdate()
    window_end = today + timedelta(days=31)
    entries = []
    coworkers = employee.organisation.employees.select_related('user', 'profile').filter(status='ACTIVE')
    for coworker in coworkers:
        profile = getattr(coworker, 'profile', None)
        if profile and profile.date_of_birth:
            event_date = profile.date_of_birth.replace(year=today.year)
            if today <= event_date <= window_end:
                entries.append(
                    {
                        'kind': 'BIRTHDAY',
                        'label': coworker.user.full_name,
                        'date': event_date.isoformat(),
                    }
                )
        if coworker.date_of_joining:
            event_date = coworker.date_of_joining.replace(year=today.year)
            if today <= event_date <= window_end:
                entries.append(
                    {
                        'kind': 'WORK_ANNIVERSARY',
                        'label': coworker.user.full_name,
                        'date': event_date.isoformat(),
                    }
                )
    entries.sort(key=lambda item: item['date'])
    return entries
