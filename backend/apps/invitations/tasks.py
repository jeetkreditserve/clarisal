from smtplib import SMTPException
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, autoretry_for=(SMTPException, OSError), max_retries=3, default_retry_delay=60)
def send_invite_email(self, invite_id: str):
    from apps.invitations.models import Invitation
    from django.db import transaction

    with transaction.atomic():
        try:
            invite = Invitation.objects.select_for_update().get(id=invite_id)
        except Invitation.DoesNotExist:
            return

        if invite.email_sent:
            return  # idempotency — already sent

        invite_url = f"{settings.FRONTEND_URL}/auth/invite/{invite.token}"
        org_name = invite.organisation.name if invite.organisation else 'Calrisal'
        invited_by_name = invite.invited_by.full_name if invite.invited_by else 'the platform admin'
        expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)

        subject = f"You've been invited to join {org_name} on Calrisal"
        body = (
            f"Hi {invite.email},\n\n"
            f"{invited_by_name} has invited you to join {org_name} on Calrisal "
            f"as {invite.role}.\n\n"
            f"Click the link below to set your password and get started:\n\n"
            f"{invite_url}\n\n"
            f"This link expires in {expiry_hours} hours.\n\n"
            f"If you weren't expecting this invitation, you can safely ignore this email.\n\n"
            f"— The Calrisal Team"
        )

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invite.email],
            fail_silently=False,
        )

        invite.email_sent = True
        invite.save(update_fields=['email_sent'])
