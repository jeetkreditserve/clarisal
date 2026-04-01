from celery import shared_task
from django.conf import settings
from apps.common.email_service import EmailDeliveryError, send_transactional_email


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, reset_token_id: str, raw_token: str):
    from apps.accounts.models import PasswordResetToken

    try:
        reset_token = PasswordResetToken.objects.select_related('user').get(id=reset_token_id)
    except PasswordResetToken.DoesNotExist:
        return

    if reset_token.user.account_type == 'CONTROL_TOWER':
        reset_url = f"{settings.FRONTEND_URL}/ct/reset-password/{raw_token}"
    else:
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password/{raw_token}"
    subject = 'Reset your Clarisal password'
    body = (
        f"Hi {reset_token.user.full_name},\n\n"
        "We received a request to reset your Clarisal password.\n\n"
        f"Reset it here:\n{reset_url}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRY_MINUTES} minutes.\n"
        "If you did not request this, you can ignore this email.\n\n"
        "— The Clarisal Team"
    )
    html_body = (
        f"<p>Hi {reset_token.user.full_name},</p>"
        "<p>We received a request to reset your Clarisal password.</p>"
        f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
        f"<p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRY_MINUTES} minutes.</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
        "<p>— The Clarisal Team</p>"
    )
    send_transactional_email(
        subject=subject,
        recipient_email=reset_token.user.email,
        text_body=body,
        html_body=html_body,
    )
