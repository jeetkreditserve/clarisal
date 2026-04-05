from celery import shared_task

from apps.common.email_service import EmailDeliveryError, send_transactional_email
from apps.common.transactional_emails import render_notification_email


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_approval_outcome_email(self, user_id: str, *, subject: str, title: str, body: str):
    from apps.accounts.models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    if not user.email:
        return

    rendered_email = render_notification_email(
        subject=subject,
        greeting_name=user.first_name or user.full_name or user.email,
        title=title,
        subtitle='Approval update',
        body=body,
        action_label='Open Clarisal',
        action_path='/auth/login',
    )
    send_transactional_email(
        subject=rendered_email.subject,
        recipient_email=user.email,
        text_body=rendered_email.text_body,
        html_body=rendered_email.html_body,
    )


@shared_task(bind=True, autoretry_for=(EmailDeliveryError, OSError), max_retries=3, default_retry_delay=60)
def send_payroll_ready_email(self, user_id: str, *, pay_period: str):
    from apps.accounts.models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    if not user.email:
        return

    subject = f'Your payslip for {pay_period} is ready'
    rendered_email = render_notification_email(
        subject=subject,
        greeting_name=user.first_name or user.full_name or user.email,
        title='Payslip ready',
        subtitle=pay_period,
        body='Your payroll has been finalized and your payslip is now available in Clarisal.',
        action_label='View payslips',
        action_path='/me/payslips',
        meta_lines=['Sign in to your employee workspace to review the finalized payslip.'],
    )
    send_transactional_email(
        subject=rendered_email.subject,
        recipient_email=user.email,
        text_body=rendered_email.text_body,
        html_body=rendered_email.html_body,
    )
