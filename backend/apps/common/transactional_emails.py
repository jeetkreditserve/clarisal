from dataclasses import dataclass

from django.conf import settings
from django.template.loader import render_to_string


APP_NAME = 'Clarisal'


@dataclass(frozen=True)
class RenderedTransactionalEmail:
    subject: str
    text_body: str
    html_body: str


def build_frontend_url(path: str, frontend_url: str | None = None) -> str:
    base_url = (frontend_url or getattr(settings, 'FRONTEND_URL', '') or '').strip().rstrip('/')
    if not base_url:
        base_url = 'http://localhost:8080'
    normalized_path = path if path.startswith('/') else f'/{path}'
    return f'{base_url}{normalized_path}'


def _render_email(*, subject: str, template_name: str, context: dict) -> RenderedTransactionalEmail:
    shared_context = {
        'app_name': APP_NAME,
        'footer_brand': f'The {APP_NAME} Team',
        **context,
    }
    return RenderedTransactionalEmail(
        subject=subject,
        text_body=render_to_string(f'emails/{template_name}.txt', shared_context).strip(),
        html_body=render_to_string(f'emails/{template_name}.html', shared_context).strip(),
    )


def render_invitation_email(invite, raw_token: str, *, frontend_url: str | None = None) -> RenderedTransactionalEmail:
    organisation_name = invite.organisation.name if invite.organisation else APP_NAME
    inviter_name = invite.invited_by.full_name if invite.invited_by else 'Control Tower'
    role_label = invite.get_role_display() if hasattr(invite, 'get_role_display') else str(invite.role).replace('_', ' ').title()
    recipient_name = getattr(getattr(invite, 'user', None), 'first_name', '') or invite.email
    invite_url = build_frontend_url(f'/auth/invite/{raw_token}', frontend_url)
    expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)
    is_existing_account = bool(invite.user_id and getattr(invite.user, 'is_active', False))

    subject = f"You're invited to join {organisation_name} on {APP_NAME}"
    return _render_email(
        subject=subject,
        template_name='invitation',
        context={
            'preheader': f'Open your secure invite to join {organisation_name} on {APP_NAME}.',
            'title': f"You're invited to join {organisation_name}",
            'subtitle': f'{role_label} access on {APP_NAME}',
            'greeting_name': recipient_name,
            'inviter_name': inviter_name,
            'organisation_name': organisation_name,
            'role_label': role_label,
            'action_copy': (
                'Use the secure link below to accept this access and continue to your workspace.'
                if is_existing_account
                else 'Use the secure link below to set your password and start your onboarding.'
            ),
            'action_label': 'Accept access' if is_existing_account else 'Set password and continue',
            'action_url': invite_url,
            'meta_lines': [
                f'This secure link expires in {expiry_hours} hours.',
                "If you weren't expecting this invite, you can safely ignore this email.",
            ],
            'fallback_label': 'If the button does not work, copy and paste this URL into your browser:',
        },
    )


def render_password_reset_email(reset_token, raw_token: str, *, frontend_url: str | None = None) -> RenderedTransactionalEmail:
    is_control_tower = reset_token.user.account_type == 'CONTROL_TOWER'
    reset_url = build_frontend_url(
        f'/ct/reset-password/{raw_token}' if is_control_tower else f'/auth/reset-password/{raw_token}',
        frontend_url,
    )
    workspace_label = 'Control Tower' if is_control_tower else 'Workforce'
    recipient_name = reset_token.user.first_name or reset_token.user.full_name or reset_token.user.email
    expiry_minutes = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_MINUTES', 30)

    return _render_email(
        subject=f'Reset your {APP_NAME} password',
        template_name='password_reset',
        context={
            'preheader': f'Reset the password for your {workspace_label} account.',
            'title': 'Reset your password',
            'subtitle': f'{workspace_label} account security',
            'greeting_name': recipient_name,
            'workspace_label': workspace_label,
            'action_label': 'Reset password',
            'action_url': reset_url,
            'meta_lines': [
                f'This secure link expires in {expiry_minutes} minutes.',
                "If you didn't request this reset, you can safely ignore this email.",
            ],
            'fallback_label': 'If the button does not work, copy and paste this URL into your browser:',
        },
    )
