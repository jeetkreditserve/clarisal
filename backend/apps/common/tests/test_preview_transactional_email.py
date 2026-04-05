from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.mark.parametrize(
    ('kind', 'expected_renderer'),
    [
        ('invite-org-admin', 'render_invitation_email'),
        ('invite-employee', 'render_invitation_email'),
        ('password-reset-workforce', 'render_password_reset_email'),
        ('password-reset-control-tower', 'render_password_reset_email'),
    ],
)
def test_preview_transactional_email_renders_supported_kinds(kind, expected_renderer):
    rendered = SimpleNamespace(subject='Subject', text_body='Plain text', html_body='<p>HTML</p>')
    stdout = StringIO()

    with patch('apps.common.management.commands.preview_transactional_email.render_invitation_email', return_value=rendered) as mock_invite, patch(
        'apps.common.management.commands.preview_transactional_email.render_password_reset_email',
        return_value=rendered,
    ) as mock_reset:
        call_command('preview_transactional_email', kind, stdout=stdout)

    output = stdout.getvalue()

    assert 'Subject: Subject' in output
    assert '--- TEXT ---' in output
    assert '--- HTML ---' in output
    if expected_renderer == 'render_invitation_email':
        mock_invite.assert_called_once()
        mock_reset.assert_not_called()
    else:
        mock_reset.assert_called_once()
        mock_invite.assert_not_called()
