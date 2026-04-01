from celery import shared_task

from apps.common.email_service import EmailDeliveryError, send_transactional_email
from apps.common.transactional_emails import render_invitation_email


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_invite_email(self, invite_id: str, raw_token: str):
    from apps.invitations.models import Invitation
    from django.db import transaction

    with transaction.atomic():
        try:
            invite = Invitation.objects.select_for_update().get(id=invite_id)
        except Invitation.DoesNotExist:
            return

        if invite.email_sent:
            return  # idempotency — already sent

        rendered_email = render_invitation_email(invite, raw_token)

        send_transactional_email(
            subject=rendered_email.subject,
            recipient_email=invite.email,
            text_body=rendered_email.text_body,
            html_body=rendered_email.html_body,
        )

        invite.email_sent = True
        invite.save(update_fields=['email_sent'])
        if invite.user_id:
            invite.user.is_onboarding_email_sent = True
            invite.user.save(update_fields=['is_onboarding_email_sent'])
