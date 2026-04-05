from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import NotFound

from apps.audit.services import log_audit_event
from apps.common.security import generate_secure_token, hash_token

from .models import AccountType, PasswordResetToken

User = get_user_model()


def create_password_reset_request(
    email: str,
    account_type: str = AccountType.WORKFORCE,
    requested_by_ip: str | None = None,
    request=None,
):
    from .tasks import send_password_reset_email

    try:
        user = User.objects.get(email__iexact=email, account_type=account_type)
    except User.DoesNotExist:
        log_audit_event(
            None,
            'auth.password_reset.requested',
            payload={'email': email, 'account_type': account_type, 'user_found': False},
            request=request,
        )
        return None

    if not user.is_active:
        log_audit_event(
            None,
            'auth.password_reset.requested',
            target=user,
            payload={'email': email, 'account_type': account_type, 'user_found': True, 'user_active': False},
            request=request,
        )
        return None

    expiry_minutes = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_MINUTES', 30)
    raw_token = generate_secure_token()

    with transaction.atomic():
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).delete()
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            requested_by_ip=requested_by_ip,
        )
        transaction.on_commit(
            lambda: send_password_reset_email.delay(str(reset_token.id), raw_token)
        )

    log_audit_event(
        None,
        'auth.password_reset.requested',
        target=user,
        payload={'email': email, 'account_type': account_type, 'user_found': True, 'user_active': True},
        request=request,
    )
    return reset_token


def validate_password_reset_token(raw_token: str):
    token_hash = hash_token(raw_token)
    try:
        reset_token = PasswordResetToken.objects.select_related('user').get(token_hash=token_hash)
    except PasswordResetToken.DoesNotExist as exc:
        raise NotFound('Password reset link not found.') from exc

    if not reset_token.is_valid:
        if reset_token.is_expired:
            raise drf_serializers.ValidationError({'token': 'This password reset link has expired.'})  # nosec B105
        raise drf_serializers.ValidationError({'token': 'This password reset link has already been used.'})  # nosec B105

    return reset_token


def confirm_password_reset(raw_token: str, password: str, request=None):
    reset_token = validate_password_reset_token(raw_token)
    user = reset_token.user

    with transaction.atomic():
        user.set_password(password)
        user.save(update_fields=['password'])
        reset_token.used_at = timezone.now()
        reset_token.save(update_fields=['used_at'])

    log_audit_event(
        user,
        'auth.password_reset.confirmed',
        target=user,
        payload={'account_type': user.account_type},
        request=request,
    )
    return user
