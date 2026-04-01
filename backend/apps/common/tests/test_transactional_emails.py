from types import SimpleNamespace

import pytest
from django.test import override_settings

from apps.accounts.models import AccountType
from apps.common.transactional_emails import render_invitation_email, render_password_reset_email
from apps.invitations.models import InvitationRole


class FakeInvite(SimpleNamespace):
    def get_role_display(self):
        return 'Organisation Admin' if self.role == InvitationRole.ORG_ADMIN else 'Employee'


def make_invite(*, role=InvitationRole.ORG_ADMIN, is_existing_user=False):
    return FakeInvite(
        email='info@clarisal.com',
        role=role,
        organisation=SimpleNamespace(name='Orbit Freight Pvt Ltd'),
        invited_by=SimpleNamespace(full_name='Control Tower'),
        user=SimpleNamespace(is_active=is_existing_user, first_name='Jeet'),
        user_id='preview-user-id',
    )


def make_reset_token(account_type=AccountType.WORKFORCE):
    return SimpleNamespace(
        user=SimpleNamespace(
            account_type=account_type,
            first_name='Jeet',
            full_name='Jeet',
            email='info@clarisal.com',
        )
    )


@pytest.mark.django_db
@override_settings(FRONTEND_URL='https://dev.clarisal.com')
def test_render_invitation_email_uses_frontend_url_and_human_role_label():
    rendered = render_invitation_email(make_invite(role=InvitationRole.ORG_ADMIN), 'sample-token')

    assert rendered.subject == "You're invited to join Orbit Freight Pvt Ltd on Clarisal"
    assert 'Organisation Admin' in rendered.html_body
    assert 'ORG_ADMIN' not in rendered.html_body
    assert 'https://dev.clarisal.com/auth/invite/sample-token' in rendered.html_body
    assert 'Set password and continue' in rendered.html_body
    assert 'https://dev.clarisal.com/auth/invite/sample-token' in rendered.text_body


@pytest.mark.django_db
@override_settings(FRONTEND_URL='https://dev.clarisal.com')
def test_render_invitation_email_for_existing_user_uses_accept_copy():
    rendered = render_invitation_email(make_invite(role=InvitationRole.EMPLOYEE, is_existing_user=True), 'existing-token')

    assert 'Accept access' in rendered.html_body
    assert 'accept this access and continue to your workspace' in rendered.text_body


@pytest.mark.django_db
@override_settings(FRONTEND_URL='https://dev.clarisal.com')
def test_render_password_reset_email_uses_account_specific_paths():
    workforce = render_password_reset_email(make_reset_token(AccountType.WORKFORCE), 'workforce-reset')
    control_tower = render_password_reset_email(make_reset_token(AccountType.CONTROL_TOWER), 'ct-reset')

    assert 'https://dev.clarisal.com/auth/reset-password/workforce-reset' in workforce.html_body
    assert 'https://dev.clarisal.com/ct/reset-password/ct-reset' in control_tower.html_body
    assert 'Reset your password' in workforce.html_body
