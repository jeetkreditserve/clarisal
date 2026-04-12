import secrets
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.common.security import hash_token
from apps.invitations.models import Invitation, InvitationRole, InvitationStatus
from apps.organisations.models import (
    Organisation,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


@pytest.fixture
def ct_client(db):
    user = User.objects.create_superuser(
        email='ct@test.com', password='pass123!', role=UserRole.CONTROL_TOWER,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def paid_org(db):
    ct = User.objects.create_superuser(email='ct2@test.com', password='pass', role=UserRole.CONTROL_TOWER)
    return Organisation.objects.create(name='Acme', licence_count=10, created_by=ct, status=OrganisationStatus.PAID)


@pytest.mark.django_db
class TestInviteOrgAdmin:
    @patch('django.db.transaction.on_commit')
    def test_invite_admin_returns_201(self, mock_oc, ct_client, paid_org):
        mock_oc.side_effect = lambda f: f()
        client, _ = ct_client
        with patch('apps.invitations.tasks.send_invite_email.delay'):
            response = client.post(
                f'/api/v1/ct/organisations/{paid_org.id}/admins/invite/',
                {'email': 'admin@acme.com', 'first_name': 'Alice', 'last_name': 'Smith'},
                format='json',
            )
        assert response.status_code == 201
        assert response.data['email'] == 'admin@acme.com'

    def test_invite_to_pending_org_returns_400(self, ct_client):
        client, ct = ct_client
        org = Organisation.objects.create(name='Pending Org', licence_count=5, created_by=ct, status=OrganisationStatus.PENDING)
        response = client.post(
            f'/api/v1/ct/organisations/{org.id}/admins/invite/',
            {'email': 'a@b.com', 'first_name': 'A', 'last_name': 'B'},
            format='json',
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestValidateInviteToken:
    def test_valid_token_returns_invite_info(self, db):
        ct = User.objects.create_superuser(email='ct@t.com', password='pass', role=UserRole.CONTROL_TOWER)
        org = Organisation.objects.create(name='Org', licence_count=5, created_by=ct)
        raw_token = secrets.token_urlsafe(32)
        Invitation.objects.create(
            token_hash=hash_token(raw_token), email='a@b.com',
            organisation=org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        client = APIClient()
        response = client.get(f'/api/v1/auth/invite/validate/{raw_token}/')
        assert response.status_code == 200
        assert response.data['email'] == 'a@b.com'

    def test_invalid_token_returns_400(self):
        client = APIClient()
        response = client.get('/api/v1/auth/invite/validate/bad-token/')
        assert response.status_code == 400


@pytest.mark.django_db
class TestAcceptInvite:
    def test_accept_activates_user_and_requires_login_for_new_org_admin(self, db):
        ct = User.objects.create_superuser(email='ct@t.com', password='pass', role=UserRole.CONTROL_TOWER)
        org = Organisation.objects.create(name='Org', licence_count=5, created_by=ct, status=OrganisationStatus.PAID)
        user = User.objects.create(email='admin@org.com', role=UserRole.ORG_ADMIN, account_type=AccountType.WORKFORCE, is_active=False)
        OrganisationMembership.objects.create(
            user=user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INVITED,
        )
        raw_token = secrets.token_urlsafe(32)
        Invitation.objects.create(
            token_hash=hash_token(raw_token), email='admin@org.com',
            organisation=org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct, user=user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        client = APIClient()
        response = client.post('/api/v1/auth/invite/accept/', {
            'token': raw_token,
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
        }, format='json')
        assert response.status_code == 200
        assert response.data['requires_login'] is True
        assert response.data['login_url'].endswith('/auth/login')
        user.refresh_from_db()
        assert user.is_active
