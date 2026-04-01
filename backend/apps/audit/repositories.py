from uuid import UUID

from django.db.models import Q

from .models import AuditLog


def get_audit_logs():
    return AuditLog.objects.select_related('actor', 'organisation').order_by('-created_at')


def get_audit_logs_for_organisation(organisation):
    return get_audit_logs().filter(organisation=organisation)


def apply_audit_filters(queryset, params):
    module = params.get('module')
    action = params.get('action')
    actor = params.get('actor')
    target_type = params.get('target_type')
    search = params.get('search')
    date_from = params.get('date_from')
    date_to = params.get('date_to')

    if module:
        queryset = queryset.filter(action__startswith=f'{module}.')
    if action:
        queryset = queryset.filter(action=action)
    if actor:
        queryset = queryset.filter(
            Q(actor__email__icontains=actor)
            | Q(actor__first_name__icontains=actor)
            | Q(actor__last_name__icontains=actor)
        )
    if target_type:
        queryset = queryset.filter(target_type__iexact=target_type)
    if search:
        search_filter = (
            Q(action__icontains=search)
            | Q(target_type__icontains=search)
            | Q(actor__email__icontains=search)
            | Q(actor__first_name__icontains=search)
            | Q(actor__last_name__icontains=search)
        )
        search_uuid = search.strip()
        try:
            search_filter |= Q(target_id=UUID(search_uuid))
        except (ValueError, TypeError):
            pass
        queryset = queryset.filter(search_filter)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    return queryset
