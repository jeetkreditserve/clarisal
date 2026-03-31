from .models import AuditLog


def get_audit_logs():
    return AuditLog.objects.select_related('actor', 'organisation').order_by('-created_at')


def get_audit_logs_for_organisation(organisation):
    return get_audit_logs().filter(organisation=organisation)
