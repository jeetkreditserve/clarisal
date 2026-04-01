from celery import shared_task
from django.conf import settings

from apps.common.email_service import EmailDeliveryError, send_transactional_email


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

        invite_url = f"{settings.FRONTEND_URL}/auth/invite/{raw_token}"
        org_name = invite.organisation.name if invite.organisation else 'Clarisal'
        invited_by_name = invite.invited_by.full_name if invite.invited_by else 'the platform admin'
        expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)

        subject = f"You've been invited to join {org_name} on Clarisal"
        action_copy = (
            'Click the link below to accept access and continue:'
            if invite.user_id and getattr(invite.user, 'is_active', False)
            else 'Click the link below to set your password and get started:'
        )
        body = (
            f"Hi {invite.email},\n\n"
            f"{invited_by_name} has invited you to join {org_name} on Clarisal "
            f"as {invite.role}.\n\n"
            f"{action_copy}\n\n"
            f"{invite_url}\n\n"
            f"This link expires in {expiry_hours} hours.\n\n"
            f"If you weren't expecting this invitation, you can safely ignore this email.\n\n"
            f"— The Clarisal Team"
        )
        html_body = (
            f"<p>Hi {invite.email},</p>"
            f"<p>{invited_by_name} has invited you to join <strong>{org_name}</strong> on Clarisal as {invite.role}.</p>"
            f"<p>{action_copy}</p>"
            f"<p><a href=\"{invite_url}\">{invite_url}</a></p>"
            f"<p>This link expires in {expiry_hours} hours.</p>"
            "<p>If you weren't expecting this invitation, you can safely ignore this email.</p>"
            "<p>— The Clarisal Team</p>"
        )

        send_transactional_email(
            subject=subject,
            recipient_email=invite.email,
            text_body=body,
            html_body=html_body,
        )

        invite.email_sent = True
        invite.save(update_fields=['email_sent'])
        if invite.user_id:
            invite.user.is_onboarding_email_sent = True
            invite.user.save(update_fields=['is_onboarding_email_sent'])
