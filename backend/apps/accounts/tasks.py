from celery import shared_task

from apps.common.email_service import EmailDeliveryError, send_transactional_email
from apps.common.transactional_emails import render_password_reset_email


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, reset_token_id: str, raw_token: str):
    from apps.accounts.models import PasswordResetToken

    try:
        reset_token = PasswordResetToken.objects.select_related('user').get(id=reset_token_id)
    except PasswordResetToken.DoesNotExist:
        return

    rendered_email = render_password_reset_email(reset_token, raw_token)
    send_transactional_email(
        subject=rendered_email.subject,
        recipient_email=reset_token.user.email,
        text_body=rendered_email.text_body,
        html_body=rendered_email.html_body,
    )
