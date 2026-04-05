from datetime import timedelta

from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.departments.models import Department
from apps.employees.models import Employee
from apps.locations.models import OfficeLocation

from .models import Notice, NoticeAudienceType, NoticeStatus


def _normalise_notice_state(fields):
    status = fields.get('status', NoticeStatus.DRAFT)
    expires_at = fields.get('expires_at')

    if status == NoticeStatus.PUBLISHED:
        fields.setdefault('published_at', timezone.now())
    elif status != NoticeStatus.PUBLISHED:
        fields['published_at'] = None

    if status != NoticeStatus.SCHEDULED:
        fields['scheduled_for'] = None

    if expires_at and status == NoticeStatus.EXPIRED:
        fields.setdefault('published_at', timezone.now())

    return fields


def create_notice(organisation, actor=None, department_ids=None, office_location_ids=None, employee_ids=None, **fields):
    fields = _normalise_notice_state(fields)
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
    fields = _normalise_notice_state(fields)
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


def publish_scheduled_notices(now=None):
    current_time = now or timezone.now()
    published_count = 0
    queryset = Notice.objects.filter(
        status=NoticeStatus.SCHEDULED,
        scheduled_for__isnull=False,
        scheduled_for__lte=current_time,
    )
    for notice in queryset.iterator():
        Notice.objects.filter(id=notice.id, status=NoticeStatus.SCHEDULED).update(
            status=NoticeStatus.PUBLISHED,
            published_at=current_time,
            modified_at=current_time,
        )
        notice.refresh_from_db()
        log_audit_event(
            None,
            'notice.auto_published',
            organisation=notice.organisation,
            target=notice,
            payload={'scheduled_for': notice.scheduled_for.isoformat() if notice.scheduled_for else None},
        )
        published_count += 1
    return published_count


def expire_stale_notices(now=None):
    current_time = now or timezone.now()
    expired_count = 0
    queryset = Notice.objects.filter(
        status__in=[NoticeStatus.PUBLISHED, NoticeStatus.SCHEDULED],
        expires_at__isnull=False,
        expires_at__lte=current_time,
    )
    for notice in queryset.iterator():
        Notice.objects.filter(
            id=notice.id,
            status__in=[NoticeStatus.PUBLISHED, NoticeStatus.SCHEDULED],
        ).update(
            status=NoticeStatus.EXPIRED,
            modified_at=current_time,
        )
        notice.refresh_from_db()
        log_audit_event(
            None,
            'notice.auto_expired',
            organisation=notice.organisation,
            target=notice,
            payload={'expires_at': notice.expires_at.isoformat() if notice.expires_at else None},
        )
        expired_count += 1
    return expired_count


def get_visible_notices(employee, now=None):
    current_time = now or timezone.now()
    audience_filter = Q(audience_type=NoticeAudienceType.ALL_EMPLOYEES)
    if employee.department_id:
        audience_filter |= Q(audience_type=NoticeAudienceType.DEPARTMENTS, departments__id=employee.department_id)
    if employee.office_location_id:
        audience_filter |= Q(audience_type=NoticeAudienceType.OFFICE_LOCATIONS, office_locations__id=employee.office_location_id)
    audience_filter |= Q(audience_type=NoticeAudienceType.SPECIFIC_EMPLOYEES, employees__id=employee.id)

    return list(
        Notice.objects.filter(
            organisation=employee.organisation,
            status=NoticeStatus.PUBLISHED,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=current_time))
        .filter(audience_filter)
        .prefetch_related(
            Prefetch('departments', queryset=Department.objects.only('id')),
            Prefetch('office_locations', queryset=OfficeLocation.objects.only('id')),
            Prefetch('employees', queryset=Employee.objects.only('id')),
        )
        .distinct()
        .order_by('-is_sticky', '-published_at', '-created_at')
    )


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
