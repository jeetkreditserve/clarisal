from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import NotFound

from apps.accounts.models import User, UserRole
from apps.common.security import hash_token
from apps.invitations.models import Invitation, InvitationRole, InvitationStatus
from apps.invitations.services import accept_invitation, create_org_admin_invitation, validate_invite_token
from apps.organisations.models import Organisation, OrganisationStatus


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@test.com', password='pass123!',
        first_name='Control', last_name='Tower', role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def paid_org(ct_user):
    return Organisation.objects.create(
        name='Acme Corp', licence_count=10, created_by=ct_user, status=OrganisationStatus.PAID,
    )


@pytest.mark.django_db
class TestCreateOrgAdminInvitation:
    @patch('django.db.transaction.on_commit')
    def test_creates_inactive_user_and_invitation(self, mock_on_commit, ct_user, paid_org):
        mock_on_commit.side_effect = lambda f: f()
        with patch('apps.invitations.tasks.send_invite_email.delay') as mock_task:
            user, invite = create_org_admin_invitation(
                organisation=paid_org, email='admin@acme.com',
                first_name='Alice', last_name='Smith', invited_by=ct_user,
            )
        assert user.email == 'admin@acme.com'
        assert not user.is_active
        assert user.role == UserRole.ORG_ADMIN
        assert invite.email == 'admin@acme.com'
        assert invite.status == InvitationStatus.PENDING
        assert invite.role == InvitationRole.ORG_ADMIN
        mock_task.assert_called_once()

    @patch('django.db.transaction.on_commit')
    def test_revokes_previous_pending_invite_on_resend(self, mock_on_commit, ct_user, paid_org):
        mock_on_commit.side_effect = lambda f: f()
        with patch('apps.invitations.tasks.send_invite_email.delay'):
            user, invite1 = create_org_admin_invitation(
                organisation=paid_org, email='admin@acme.com',
                first_name='Alice', last_name='Smith', invited_by=ct_user,
            )
            _, invite2 = create_org_admin_invitation(
                organisation=paid_org, email='admin@acme.com',
                first_name='Alice', last_name='Smith', invited_by=ct_user,
            )
        invite1.refresh_from_db()
        assert invite1.status == InvitationStatus.REVOKED
        assert invite2.status == InvitationStatus.PENDING


@pytest.mark.django_db
class TestValidateInviteToken:
    def test_returns_valid_invite(self, ct_user, paid_org):
        import secrets
        raw_token = secrets.token_urlsafe(32)
        invite = Invitation.objects.create(
            token_hash=hash_token(raw_token), email='a@b.com',
            organisation=paid_org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct_user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        result = validate_invite_token(raw_token)
        assert result.id == invite.id

    def test_raises_for_expired_invite(self, ct_user, paid_org):
        import secrets
        raw_token = secrets.token_urlsafe(32)
        Invitation.objects.create(
            token_hash=hash_token(raw_token), email='a@b.com',
            organisation=paid_org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct_user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        with pytest.raises(drf_serializers.ValidationError):
            validate_invite_token(raw_token)

    def test_raises_for_nonexistent_token(self):
        with pytest.raises(NotFound):
            validate_invite_token('nonexistent-token-xyz')


@pytest.mark.django_db
class TestAcceptInvitation:
    def test_activates_user_and_marks_accepted(self, ct_user, paid_org):
        import secrets
        raw_token = secrets.token_urlsafe(32)
        user = User.objects.create(
            email='admin@acme.com', first_name='Alice', last_name='Smith',
            role=UserRole.ORG_ADMIN, organisation=paid_org, is_active=False,
        )
        invite = Invitation.objects.create(
            token_hash=hash_token(raw_token), email='admin@acme.com',
            organisation=paid_org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct_user, user=user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        result = accept_invitation(raw_token, 'SecurePass123!')
        user.refresh_from_db()
        invite.refresh_from_db()
        paid_org.refresh_from_db()
        assert user.is_active
        assert invite.status == InvitationStatus.ACCEPTED
        assert paid_org.status == OrganisationStatus.ACTIVE
        assert result['user'].id == user.id
        assert result['requires_login'] is True
