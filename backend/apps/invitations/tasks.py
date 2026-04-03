from celery import shared_task

from apps.common.email_service import EmailDeliveryError, send_transactional_email
from apps.common.transactional_emails import (
    render_invitation_email,
    render_org_admin_password_set_email,
)


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_invite_email(self, invite_id: str, raw_token: str):
    from django.db import transaction

    from apps.invitations.models import Invitation

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
            user = invite.user
            if user is not None:
                user.is_onboarding_email_sent = True
                user.save(update_fields=['is_onboarding_email_sent'])


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_org_admin_password_set_email(self, user_id: str, organisation_name: str):
    from apps.accounts.models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    rendered_email = render_org_admin_password_set_email(
        user=user,
        organisation_name=organisation_name,
    )
    send_transactional_email(
        subject=rendered_email.subject,
        recipient_email=user.email,
        text_body=rendered_email.text_body,
        html_body=rendered_email.html_body,
    )
