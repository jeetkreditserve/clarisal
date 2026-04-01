from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.audit.services import log_audit_event


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):  # noqa: ARG001
    log_audit_event(
        user,
        'auth.login.succeeded',
        target=user,
        payload={'account_type': getattr(user, 'account_type', ''), 'is_staff': getattr(user, 'is_staff', False)},
        request=request,
    )


@receiver(user_logged_out)
def handle_user_logged_out(sender, request, user, **kwargs):  # noqa: ARG001
    if user is None:
        return
    log_audit_event(
        user,
        'auth.logout.completed',
        target=user,
        payload={'account_type': getattr(user, 'account_type', '')},
        request=request,
    )


@receiver(user_login_failed)
def handle_user_login_failed(sender, credentials, request, **kwargs):  # noqa: ARG001
    log_audit_event(
        None,
        'auth.login.failed',
        payload={
            'email': credentials.get('username', ''),
            'account_type': credentials.get('account_type', ''),
        },
        request=request,
    )
