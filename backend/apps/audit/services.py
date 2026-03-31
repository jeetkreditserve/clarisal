from .models import AuditLog


def log_audit_event(actor, action, organisation=None, target=None, payload=None, request=None):
    payload = payload or {}
    target_type = target.__class__.__name__ if target is not None else ''
    target_id = getattr(target, 'id', None) if target is not None else None
    ip_address = None
    user_agent = ''
    if request is not None:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    return AuditLog.objects.create(
        actor=actor,
        organisation=organisation,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
