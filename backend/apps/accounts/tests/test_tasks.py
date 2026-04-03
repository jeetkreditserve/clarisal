from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import AccountType, PasswordResetToken, User, UserRole
from apps.accounts.tasks import send_password_reset_email


@pytest.mark.django_db
def test_send_password_reset_email_returns_when_token_missing():
    with patch('apps.accounts.tasks.render_password_reset_email') as mock_render, patch(
        'apps.accounts.tasks.send_transactional_email'
    ) as mock_send:
        send_password_reset_email.run('00000000-0000-0000-0000-000000000000', 'raw-token')

    mock_render.assert_not_called()
    mock_send.assert_not_called()


@pytest.mark.django_db
def test_send_password_reset_email_renders_and_sends_email():
    user = User.objects.create_user(
        email='reset-task@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    reset_token = PasswordResetToken.objects.create(
        user=user,
        token_hash='hash-123',
        expires_at=timezone.now() + timedelta(hours=1),
    )
    rendered_email = SimpleNamespace(
        subject='Reset password',
        text_body='Text body',
        html_body='<p>HTML</p>',
    )
    with patch('apps.accounts.tasks.render_password_reset_email', return_value=rendered_email) as mock_render, patch(
        'apps.accounts.tasks.send_transactional_email'
    ) as mock_send:
        send_password_reset_email.run(str(reset_token.id), 'raw-token')

    mock_render.assert_called_once_with(reset_token, 'raw-token')
    mock_send.assert_called_once_with(
        subject='Reset password',
        recipient_email=user.email,
        text_body='Text body',
        html_body='<p>HTML</p>',
    )
