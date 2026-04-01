# Phase 2: CT Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full Control Tower module — org lifecycle management, invitation system, Celery email tasks, and CT frontend (dashboard, org list, org detail, invite admin flow).

**Architecture:** Service-layer pattern (repositories → services → views). All business logic in services.py, querysets in repositories.py, HTTP handling in views.py. Frontend uses TanStack Query with a typed API layer.

**Tech Stack:** Django 4.2, DRF, Celery 5, SimpleJWT, React 18, TanStack Query 5, TypeScript, Tailwind CSS v4, axios.

---

## Coverage Map

| Phase 2 Feature | Task |
|---|---|
| Organisation CRUD | Task 1 (service), Task 3 (API) |
| State machine PENDING→PAID→ACTIVE→SUSPENDED | Task 1 (service), Task 3 (API) |
| Licence management | Task 1 (service), Task 3 (API) |
| Org admin invitation flow | Task 2 (service), Task 4 (API) |
| Celery email tasks | Task 2 (tasks.py) |
| CT Dashboard (real data) | Task 5 (hooks/API), Task 6 (UI) |
| CT Org list page | Task 5 (hooks/API), Task 6 (UI) |
| CT Org detail page | Task 5 (hooks/API), Task 7 (UI) |
| CT New Organisation page | Task 7 (UI) |
| CT Invite Admin flow | Task 4 (API), Task 7 (UI modal) |
| Frontend types layer | Task 5 |
| Frontend API layer | Task 5 |
| Invite accept page (real API) | Task 8 |

---

## Task 1: Organisation Service Layer

**Files:**
- `backend/apps/organisations/serializers.py` — create
- `backend/apps/organisations/repositories.py` — create
- `backend/apps/organisations/services.py` — create
- `backend/apps/organisations/tests/test_services.py` — create

---

### Step 1.1: Write failing tests

- [ ] Create `backend/apps/organisations/tests/test_services.py` with the full content below:

```python
import pytest
from apps.accounts.models import User, UserRole
from apps.organisations.models import Organisation, OrganisationStateTransition, OrganisationStatus
from apps.organisations.services import (
    create_organisation, transition_organisation_state,
    update_licence_count, get_ct_dashboard_stats,
)


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@test.com', password='pass123!',
        first_name='Control', last_name='Tower',
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def pending_org(ct_user):
    return Organisation.objects.create(
        name='Acme Corp', licence_count=10, created_by=ct_user,
    )


@pytest.mark.django_db
class TestCreateOrganisation:
    def test_creates_with_pending_status(self, ct_user):
        org = create_organisation(name='Test Corp', licence_count=5, created_by=ct_user)
        assert org.status == OrganisationStatus.PENDING
        assert org.name == 'Test Corp'
        assert org.licence_count == 5

    def test_auto_generates_slug(self, ct_user):
        org = create_organisation(name='Hello World Corp', licence_count=1, created_by=ct_user)
        assert 'hello' in org.slug
        assert org.slug != ''

    def test_stores_optional_fields(self, ct_user):
        org = create_organisation(
            name='Test', licence_count=1, created_by=ct_user,
            address='123 Main St', phone='+91999', email='org@test.com',
        )
        assert org.address == '123 Main St'
        assert org.email == 'org@test.com'


@pytest.mark.django_db
class TestTransitionOrganisationState:
    def test_pending_to_paid_succeeds(self, ct_user, pending_org):
        result = transition_organisation_state(pending_org, OrganisationStatus.PAID, ct_user)
        assert result.status == OrganisationStatus.PAID
        pending_org.refresh_from_db()
        assert pending_org.status == OrganisationStatus.PAID

    def test_creates_state_transition_record(self, ct_user, pending_org):
        transition_organisation_state(pending_org, OrganisationStatus.PAID, ct_user, note='Payment received')
        t = OrganisationStateTransition.objects.get(organisation=pending_org)
        assert t.from_status == OrganisationStatus.PENDING
        assert t.to_status == OrganisationStatus.PAID
        assert t.note == 'Payment received'
        assert t.transitioned_by == ct_user

    def test_invalid_transition_raises_value_error(self, ct_user, pending_org):
        with pytest.raises(ValueError, match='Cannot transition'):
            transition_organisation_state(pending_org, OrganisationStatus.ACTIVE, ct_user)

    def test_paid_to_active_succeeds(self, ct_user, pending_org):
        pending_org.status = OrganisationStatus.PAID
        pending_org.save()
        result = transition_organisation_state(pending_org, OrganisationStatus.ACTIVE, ct_user)
        assert result.status == OrganisationStatus.ACTIVE

    def test_active_to_suspended_succeeds(self, ct_user, pending_org):
        pending_org.status = OrganisationStatus.ACTIVE
        pending_org.save()
        result = transition_organisation_state(pending_org, OrganisationStatus.SUSPENDED, ct_user)
        assert result.status == OrganisationStatus.SUSPENDED


@pytest.mark.django_db
class TestUpdateLicenceCount:
    def test_updates_licence_count(self, ct_user, pending_org):
        result = update_licence_count(pending_org, 25)
        assert result.licence_count == 25
        pending_org.refresh_from_db()
        assert pending_org.licence_count == 25


@pytest.mark.django_db
class TestGetCtDashboardStats:
    def test_returns_correct_counts(self, ct_user):
        Organisation.objects.create(name='Org1', licence_count=5, created_by=ct_user, status=OrganisationStatus.ACTIVE)
        Organisation.objects.create(name='Org2', licence_count=5, created_by=ct_user, status=OrganisationStatus.PENDING)
        stats = get_ct_dashboard_stats()
        assert stats['total_organisations'] == 2
        assert stats['active_organisations'] == 1
        assert stats['pending_organisations'] == 1
```

---

### Step 1.2: Run tests — expect FAIL

- [ ] Run: `docker compose exec backend pytest apps/organisations/tests/test_services.py -v`
- [ ] Confirm: `ImportError` or `ModuleNotFoundError` on `apps.organisations.services` — tests are red as expected.

---

### Step 1.3: Implement serializers, repositories, and services

- [ ] Create `backend/apps/organisations/serializers.py` with the full content below:

```python
from rest_framework import serializers
from apps.accounts.models import User
from .models import Organisation, OrganisationStateTransition


class OrganisationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'slug', 'status', 'licence_count', 'created_at']


class StateTransitionSerializer(serializers.ModelSerializer):
    transitioned_by_email = serializers.EmailField(source='transitioned_by.email', read_only=True)

    class Meta:
        model = OrganisationStateTransition
        fields = ['id', 'from_status', 'to_status', 'note', 'transitioned_by_email', 'created_at']


class OrganisationDetailSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    state_transitions = StateTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'slug', 'status', 'licence_count',
            'address', 'phone', 'email', 'logo_url',
            'created_by_email', 'created_at', 'updated_at',
            'state_transitions',
        ]


class CreateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    licence_count = serializers.IntegerField(min_value=1)


class UpdateOrganisationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class LicenceUpdateSerializer(serializers.Serializer):
    licence_count = serializers.IntegerField(min_value=0)


class OrgAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'is_onboarding_email_sent']


class CTDashboardStatsSerializer(serializers.Serializer):
    total_organisations = serializers.IntegerField()
    active_organisations = serializers.IntegerField()
    pending_organisations = serializers.IntegerField()
    paid_organisations = serializers.IntegerField()
    suspended_organisations = serializers.IntegerField()
    total_employees = serializers.IntegerField()
```

- [ ] Create `backend/apps/organisations/repositories.py` with the full content below:

```python
from .models import Organisation


def get_organisations():
    return Organisation.objects.select_related('created_by').prefetch_related('state_transitions').order_by('-created_at')


def get_organisation_by_id(pk):
    return Organisation.objects.select_related('created_by').prefetch_related('state_transitions').get(id=pk)


def get_org_admins(organisation):
    from apps.accounts.models import User, UserRole
    return User.objects.filter(organisation=organisation, role=UserRole.ORG_ADMIN)
```

- [ ] Create `backend/apps/organisations/services.py` with the full content below:

```python
from django.db import transaction
from apps.accounts.models import User, UserRole
from .models import Organisation, OrganisationStateTransition, OrganisationStatus

VALID_TRANSITIONS = {
    OrganisationStatus.PENDING: [OrganisationStatus.PAID],
    OrganisationStatus.PAID: [OrganisationStatus.ACTIVE],
    OrganisationStatus.ACTIVE: [OrganisationStatus.SUSPENDED],
    OrganisationStatus.SUSPENDED: [OrganisationStatus.ACTIVE],
}


def create_organisation(name, licence_count, created_by, address='', phone='', email=''):
    return Organisation.objects.create(
        name=name,
        address=address,
        phone=phone,
        email=email,
        licence_count=licence_count,
        created_by=created_by,
    )


def transition_organisation_state(org, new_status, transitioned_by, note=''):
    allowed = VALID_TRANSITIONS.get(org.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{org.status}' to '{new_status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )
    old_status = org.status
    org.status = new_status
    org.save(update_fields=['status', 'updated_at'])
    OrganisationStateTransition.objects.create(
        organisation=org,
        from_status=old_status,
        to_status=new_status,
        transitioned_by=transitioned_by,
        note=note,
    )
    return org


def update_licence_count(org, new_count):
    org.licence_count = new_count
    org.save(update_fields=['licence_count', 'updated_at'])
    return org


def get_ct_dashboard_stats():
    return {
        'total_organisations': Organisation.objects.count(),
        'active_organisations': Organisation.objects.filter(status=OrganisationStatus.ACTIVE).count(),
        'pending_organisations': Organisation.objects.filter(status=OrganisationStatus.PENDING).count(),
        'paid_organisations': Organisation.objects.filter(status=OrganisationStatus.PAID).count(),
        'suspended_organisations': Organisation.objects.filter(status=OrganisationStatus.SUSPENDED).count(),
        'total_employees': User.objects.filter(role=UserRole.EMPLOYEE, is_active=True).count(),
    }
```

---

### Step 1.4: Run tests — expect PASS

- [ ] Run: `docker compose exec backend pytest apps/organisations/tests/test_services.py -v`
- [ ] Confirm: All tests pass (green).

---

### Step 1.5: Commit

- [ ] `git add backend/apps/organisations/serializers.py backend/apps/organisations/repositories.py backend/apps/organisations/services.py backend/apps/organisations/tests/test_services.py`
- [ ] `git commit -m "feat(organisations): add service layer, repositories, and serializers"`

---

## Task 2: Invitation Service + Celery Email Task

**Files:**
- `backend/apps/invitations/serializers.py` — create
- `backend/apps/invitations/services.py` — create
- `backend/apps/invitations/tasks.py` — create
- `backend/apps/invitations/tests/test_services.py` — create

---

### Step 2.1: Write failing tests

- [ ] Create `backend/apps/invitations/tests/test_services.py` with the full content below:

```python
import pytest
from unittest.mock import patch
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.invitations.models import Invitation, InvitationRole, InvitationStatus
from apps.invitations.services import create_org_admin_invitation, validate_invite_token, accept_invitation
from apps.organisations.models import Organisation, OrganisationStatus
from rest_framework import serializers as drf_serializers


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
        mock_task.assert_called_once_with(str(invite.id))

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
        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32), email='a@b.com',
            organisation=paid_org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct_user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        result = validate_invite_token(invite.token)
        assert result.id == invite.id

    def test_raises_for_expired_invite(self, ct_user, paid_org):
        import secrets
        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32), email='a@b.com',
            organisation=paid_org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct_user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        with pytest.raises(drf_serializers.ValidationError):
            validate_invite_token(invite.token)

    def test_raises_for_nonexistent_token(self):
        with pytest.raises(drf_serializers.ValidationError):
            validate_invite_token('nonexistent-token-xyz')


@pytest.mark.django_db
class TestAcceptInvitation:
    def test_activates_user_and_marks_accepted(self, ct_user, paid_org):
        import secrets
        user = User.objects.create(
            email='admin@acme.com', first_name='Alice', last_name='Smith',
            role=UserRole.ORG_ADMIN, organisation=paid_org, is_active=False,
        )
        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32), email='admin@acme.com',
            organisation=paid_org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct_user, user=user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        result = accept_invitation(invite.token, 'SecurePass123!')
        user.refresh_from_db()
        invite.refresh_from_db()
        paid_org.refresh_from_db()
        assert user.is_active
        assert invite.status == InvitationStatus.ACCEPTED
        assert paid_org.status == OrganisationStatus.ACTIVE
        assert 'access' in result
        assert 'refresh' in result
```

---

### Step 2.2: Run tests — expect FAIL

- [ ] Run: `docker compose exec backend pytest apps/invitations/tests/test_services.py -v`
- [ ] Confirm: `ImportError` or `ModuleNotFoundError` on `apps.invitations.services` — tests are red as expected.

---

### Step 2.3: Implement serializers, tasks, and services

- [ ] Create `backend/apps/invitations/serializers.py` with the full content below:

```python
from rest_framework import serializers


class InviteOrgAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)


class ValidateInviteResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.CharField()
    organisation_name = serializers.CharField(allow_null=True)


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data
```

- [ ] Create `backend/apps/invitations/tasks.py` with the full content below:

```python
from smtplib import SMTPException
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, autoretry_for=(SMTPException,), max_retries=3, default_retry_delay=60)
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
        org_name = invite.organisation.name if invite.organisation else 'Clarisal'
        invited_by_name = invite.invited_by.full_name if invite.invited_by else 'the platform admin'

        subject = f"You've been invited to join {org_name} on Clarisal"
        body = (
            f"Hi {invite.email},\n\n"
            f"{invited_by_name} has invited you to join {org_name} on Clarisal "
            f"as {invite.role}.\n\n"
            f"Click the link below to set your password and get started:\n\n"
            f"{invite_url}\n\n"
            f"This link expires in 48 hours.\n\n"
            f"If you weren't expecting this invitation, you can safely ignore this email.\n\n"
            f"— The Clarisal Team"
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
```

- [ ] Create `backend/apps/invitations/services.py` with the full content below:

```python
import secrets
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers as drf_serializers
from apps.accounts.models import User, UserRole
from apps.organisations.models import Organisation, OrganisationStatus
from apps.organisations.services import transition_organisation_state
from .models import Invitation, InvitationRole, InvitationStatus


def create_org_admin_invitation(organisation, email, first_name, last_name, invited_by):
    from .tasks import send_invite_email

    expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)

    with transaction.atomic():
        # Revoke any existing pending invitations for this email + org
        Invitation.objects.filter(
            email=email,
            organisation=organisation,
            role=InvitationRole.ORG_ADMIN,
            status=InvitationStatus.PENDING,
        ).update(status=InvitationStatus.REVOKED)

        # Create or get user (may already exist if re-inviting)
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': UserRole.ORG_ADMIN,
                'organisation': organisation,
                'is_active': False,
            },
        )
        if not user.is_active:
            user.first_name = first_name
            user.last_name = last_name
            user.organisation = organisation
            user.role = UserRole.ORG_ADMIN
            user.save(update_fields=['first_name', 'last_name', 'organisation', 'role'])

        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32),
            email=email,
            organisation=organisation,
            role=InvitationRole.ORG_ADMIN,
            invited_by=invited_by,
            user=user,
            status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=expiry_hours),
        )

    transaction.on_commit(lambda: send_invite_email.delay(str(invite.id)))
    return user, invite


def validate_invite_token(token):
    try:
        invite = Invitation.objects.select_related('organisation', 'user').get(token=token)
    except Invitation.DoesNotExist:
        raise drf_serializers.ValidationError({'token': 'Invitation not found.'})

    if not invite.is_valid:
        if invite.is_expired:
            raise drf_serializers.ValidationError({'token': 'This invitation has expired.'})
        raise drf_serializers.ValidationError({'token': f'This invitation is {invite.status}.'})

    return invite


def accept_invitation(token, password):
    from rest_framework_simplejwt.tokens import RefreshToken

    invite = validate_invite_token(token)
    user = invite.user

    with transaction.atomic():
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=['password', 'is_active', 'updated_at'])

        invite.status = InvitationStatus.ACCEPTED
        invite.save(update_fields=['status'])

        # Transition org PAID → ACTIVE when org admin onboards
        if (invite.role == InvitationRole.ORG_ADMIN
                and invite.organisation
                and invite.organisation.status == OrganisationStatus.PAID):
            transition_organisation_state(
                invite.organisation,
                OrganisationStatus.ACTIVE,
                transitioned_by=user,
                note='Org admin accepted invitation',
            )

    # Generate JWT tokens with custom claims
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['org_id'] = str(user.organisation_id) if user.organisation_id else None
    refresh['email'] = user.email

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'org_id': str(user.organisation_id) if user.organisation_id else None,
        },
    }
```

---

### Step 2.4: Run tests — expect PASS

- [ ] Run: `docker compose exec backend pytest apps/invitations/tests/test_services.py -v`
- [ ] Confirm: All tests pass (green).

---

### Step 2.5: Commit

- [ ] `git add backend/apps/invitations/serializers.py backend/apps/invitations/tasks.py backend/apps/invitations/services.py backend/apps/invitations/tests/test_services.py`
- [ ] `git commit -m "feat(invitations): add service layer, Celery email task, and serializers"`

---

## Task 3: CT Organisation API (ViewSet + custom endpoints)

**Files:**
- `backend/apps/organisations/views.py` — create
- `backend/apps/organisations/urls.py` — create
- `backend/clarisal/urls.py` — modify: add `/api/ct/` include
- `backend/apps/organisations/tests/test_views.py` — create

---

### Step 3.1: Write failing tests

- [ ] Create `backend/apps/organisations/tests/test_views.py` with the full content below:

```python
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.organisations.models import Organisation, OrganisationStatus


@pytest.fixture
def ct_client(db):
    user = User.objects.create_superuser(
        email='ct@test.com', password='pass123!',
        first_name='Control', last_name='Tower', role=UserRole.CONTROL_TOWER,
    )
    client = APIClient()
    response = client.post('/api/auth/login/', {'email': 'ct@test.com', 'password': 'pass123!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client, user


@pytest.fixture
def org(db):
    ct_user = User.objects.create_superuser(
        email='ct2@test.com', password='pass123!', role=UserRole.CONTROL_TOWER,
    )
    return Organisation.objects.create(name='Test Corp', licence_count=10, created_by=ct_user)


@pytest.mark.django_db
class TestOrganisationListCreate:
    def test_list_returns_paginated_orgs(self, ct_client, org):
        client, _ = ct_client
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_create_org(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {
            'name': 'New Org', 'licence_count': 5, 'email': 'org@test.com',
        }, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'New Org'
        assert response.data['status'] == OrganisationStatus.PENDING

    def test_create_requires_name_and_licence_count(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {'name': 'Org'}, format='json')
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 401

    def test_non_ct_user_returns_403(self, db):
        user = User.objects.create_user(email='org@test.com', password='pass', role=UserRole.ORG_ADMIN)
        client = APIClient()
        response = client.post('/api/auth/login/', {'email': 'org@test.com', 'password': 'pass'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestOrganisationActivate:
    def test_pending_to_paid(self, ct_client, org):
        client, _ = ct_client
        response = client.post(f'/api/ct/organisations/{org.id}/activate/')
        assert response.status_code == 200
        assert response.data['status'] == OrganisationStatus.PAID

    def test_invalid_transition_returns_400(self, ct_client, org):
        client, _ = ct_client
        # PENDING cannot go to SUSPENDED
        response = client.post(f'/api/ct/organisations/{org.id}/suspend/')
        assert response.status_code == 400
```

---

### Step 3.2: Run tests — expect FAIL

- [ ] Run: `docker compose exec backend pytest apps/organisations/tests/test_views.py -v`
- [ ] Confirm: `404` or `ImportError` — tests are red because views and urls don't exist yet.

---

### Step 3.3: Implement views, urls, and wire to main urls

- [ ] Create `backend/apps/organisations/views.py` with the full content below:

```python
from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsControlTowerUser
from .models import Organisation, OrganisationStatus
from .repositories import get_organisations, get_organisation_by_id, get_org_admins
from .serializers import (
    OrganisationListSerializer, OrganisationDetailSerializer,
    CreateOrganisationSerializer, UpdateOrganisationSerializer,
    LicenceUpdateSerializer, OrgAdminSerializer, CTDashboardStatsSerializer,
)
from .services import (
    create_organisation, transition_organisation_state,
    update_licence_count, get_ct_dashboard_stats,
)


class OrganisationListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request):
        qs = get_organisations()
        search = request.query_params.get('search')
        status_filter = request.query_params.get('status')
        if search:
            qs = qs.filter(name__icontains=search)
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = OrganisationListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateOrganisationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = create_organisation(**serializer.validated_data, created_by=request.user)
        return Response(OrganisationDetailSerializer(org).data, status=status.HTTP_201_CREATED)


class OrganisationDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        return Response(OrganisationDetailSerializer(org).data)

    def patch(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = UpdateOrganisationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(org, attr, value)
        org.save()
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationActivateView(APIView):
    """Mark organisation payment received (PENDING → PAID)."""
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        note = request.data.get('note', '')
        try:
            transition_organisation_state(org, OrganisationStatus.PAID, request.user, note=note)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationSuspendView(APIView):
    """Suspend an active organisation."""
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        note = request.data.get('note', '')
        try:
            transition_organisation_state(org, OrganisationStatus.SUSPENDED, request.user, note=note)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationLicencesView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        return Response({'total_count': org.licence_count, 'used_count': 0})

    def patch(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = LicenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_licence_count(org, serializer.validated_data['licence_count'])
        return Response({'total_count': org.licence_count, 'used_count': 0})


class OrganisationAdminsView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        admins = get_org_admins(org)
        return Response(OrgAdminSerializer(admins, many=True).data)


class CTDashboardStatsView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request):
        stats = get_ct_dashboard_stats()
        return Response(CTDashboardStatsSerializer(stats).data)
```

- [ ] Create `backend/apps/organisations/urls.py` with the full content below:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.CTDashboardStatsView.as_view(), name='ct-dashboard'),
    path('organisations/', views.OrganisationListCreateView.as_view(), name='org-list-create'),
    path('organisations/<uuid:pk>/', views.OrganisationDetailView.as_view(), name='org-detail'),
    path('organisations/<uuid:pk>/activate/', views.OrganisationActivateView.as_view(), name='org-activate'),
    path('organisations/<uuid:pk>/suspend/', views.OrganisationSuspendView.as_view(), name='org-suspend'),
    path('organisations/<uuid:pk>/licences/', views.OrganisationLicencesView.as_view(), name='org-licences'),
    path('organisations/<uuid:pk>/admins/', views.OrganisationAdminsView.as_view(), name='org-admins'),
]
```

- [ ] Modify `backend/clarisal/urls.py` — add the CT include after the existing `api/auth/` line. The resulting file must be:

```python
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'clarisal-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/ct/', include('apps.organisations.urls')),
]
```

---

### Step 3.4: Run tests — expect PASS

- [ ] Run: `docker compose exec backend pytest apps/organisations/tests/test_views.py -v`
- [ ] Confirm: All tests pass (green).

---

### Step 3.5: Commit

- [ ] `git add backend/apps/organisations/views.py backend/apps/organisations/urls.py backend/clarisal/urls.py backend/apps/organisations/tests/test_views.py`
- [ ] `git commit -m "feat(organisations): add CT API views, urls, and wire to main router"`

---

## Task 4: CT Invite Admin API + Auth Invite Endpoints

**Files:**
- `backend/apps/invitations/views.py` — create
- `backend/apps/organisations/urls.py` — modify: add invite routes
- `backend/apps/accounts/urls.py` — modify: add validate and accept endpoints
- `backend/apps/invitations/tests/test_views.py` — create

---

### Step 4.1: Write failing tests

- [ ] Create `backend/apps/invitations/tests/test_views.py` with the full content below:

```python
import pytest
import secrets
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.organisations.models import Organisation, OrganisationStatus
from apps.invitations.models import Invitation, InvitationRole, InvitationStatus
from unittest.mock import patch


@pytest.fixture
def ct_client(db):
    user = User.objects.create_superuser(
        email='ct@test.com', password='pass123!', role=UserRole.CONTROL_TOWER,
    )
    client = APIClient()
    r = client.post('/api/auth/login/', {'email': 'ct@test.com', 'password': 'pass123!'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
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
                f'/api/ct/organisations/{paid_org.id}/admins/invite/',
                {'email': 'admin@acme.com', 'first_name': 'Alice', 'last_name': 'Smith'},
                format='json',
            )
        assert response.status_code == 201
        assert response.data['email'] == 'admin@acme.com'

    def test_invite_to_pending_org_returns_400(self, ct_client):
        client, ct = ct_client
        org = Organisation.objects.create(name='Pending Org', licence_count=5, created_by=ct, status=OrganisationStatus.PENDING)
        response = client.post(
            f'/api/ct/organisations/{org.id}/admins/invite/',
            {'email': 'a@b.com', 'first_name': 'A', 'last_name': 'B'},
            format='json',
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestValidateInviteToken:
    def test_valid_token_returns_invite_info(self, db):
        ct = User.objects.create_superuser(email='ct@t.com', password='pass', role=UserRole.CONTROL_TOWER)
        org = Organisation.objects.create(name='Org', licence_count=5, created_by=ct)
        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32), email='a@b.com',
            organisation=org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        client = APIClient()
        response = client.get(f'/api/auth/invite/validate/{invite.token}/')
        assert response.status_code == 200
        assert response.data['email'] == 'a@b.com'

    def test_invalid_token_returns_400(self):
        client = APIClient()
        response = client.get('/api/auth/invite/validate/bad-token/')
        assert response.status_code == 400


@pytest.mark.django_db
class TestAcceptInvite:
    def test_accept_activates_user_and_returns_tokens(self, db):
        ct = User.objects.create_superuser(email='ct@t.com', password='pass', role=UserRole.CONTROL_TOWER)
        org = Organisation.objects.create(name='Org', licence_count=5, created_by=ct, status=OrganisationStatus.PAID)
        user = User.objects.create(email='admin@org.com', role=UserRole.ORG_ADMIN, organisation=org, is_active=False)
        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32), email='admin@org.com',
            organisation=org, role=InvitationRole.ORG_ADMIN,
            invited_by=ct, user=user, status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=48),
        )
        client = APIClient()
        response = client.post('/api/auth/invite/accept/', {
            'token': invite.token,
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
        }, format='json')
        assert response.status_code == 200
        assert 'access' in response.data
        user.refresh_from_db()
        assert user.is_active
```

---

### Step 4.2: Run tests — expect FAIL

- [ ] Run: `docker compose exec backend pytest apps/invitations/tests/test_views.py -v`
- [ ] Confirm: `404` on all endpoints — tests are red because views and urls don't exist yet.

---

### Step 4.3: Implement invitation views and wire urls

- [ ] Create `backend/apps/invitations/views.py` with the full content below:

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsControlTowerUser
from apps.organisations.models import Organisation
from apps.organisations.repositories import get_org_admins
from apps.organisations.serializers import OrgAdminSerializer
from .serializers import InviteOrgAdminSerializer, AcceptInviteSerializer
from .services import create_org_admin_invitation, validate_invite_token, accept_invitation


class InviteOrgAdminView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        if org.status not in ('PAID', 'ACTIVE'):
            return Response(
                {'error': 'Organisation must be in PAID or ACTIVE status to invite admins.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = InviteOrgAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, invite = create_org_admin_invitation(
            organisation=org,
            email=serializer.validated_data['email'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            invited_by=request.user,
        )
        return Response({
            'user_id': str(user.id),
            'email': invite.email,
            'status': invite.status,
            'expires_at': invite.expires_at,
        }, status=status.HTTP_201_CREATED)


class ResendOrgAdminInviteView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, uid):
        from apps.accounts.models import User, UserRole
        org = get_object_or_404(Organisation, id=pk)
        user = get_object_or_404(User, id=uid, organisation=org, role=UserRole.ORG_ADMIN)
        _, invite = create_org_admin_invitation(
            organisation=org,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            invited_by=request.user,
        )
        return Response({'email': invite.email, 'status': invite.status, 'expires_at': invite.expires_at})


class ValidateInviteTokenView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        from rest_framework import serializers as drf_serializers
        try:
            invite = validate_invite_token(token)
        except drf_serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'email': invite.email,
            'role': invite.role,
            'organisation_name': invite.organisation.name if invite.organisation else None,
        })


class AcceptInviteView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        from rest_framework import serializers as drf_serializers
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = accept_invitation(
                token=serializer.validated_data['token'],
                password=serializer.validated_data['password'],
            )
        except drf_serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
```

- [ ] Modify `backend/apps/organisations/urls.py` — add the invite routes. The resulting file must be:

```python
from django.urls import path
from . import views
from apps.invitations.views import InviteOrgAdminView, ResendOrgAdminInviteView

urlpatterns = [
    path('dashboard/', views.CTDashboardStatsView.as_view(), name='ct-dashboard'),
    path('organisations/', views.OrganisationListCreateView.as_view(), name='org-list-create'),
    path('organisations/<uuid:pk>/', views.OrganisationDetailView.as_view(), name='org-detail'),
    path('organisations/<uuid:pk>/activate/', views.OrganisationActivateView.as_view(), name='org-activate'),
    path('organisations/<uuid:pk>/suspend/', views.OrganisationSuspendView.as_view(), name='org-suspend'),
    path('organisations/<uuid:pk>/licences/', views.OrganisationLicencesView.as_view(), name='org-licences'),
    path('organisations/<uuid:pk>/admins/', views.OrganisationAdminsView.as_view(), name='org-admins'),
    path('organisations/<uuid:pk>/admins/invite/', InviteOrgAdminView.as_view(), name='org-invite-admin'),
    path('organisations/<uuid:pk>/admins/<uuid:uid>/resend-invite/', ResendOrgAdminInviteView.as_view(), name='org-resend-invite'),
]
```

- [ ] Modify `backend/apps/accounts/urls.py` — add validate and accept endpoints. The resulting file must be:

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, MeView
from apps.invitations.views import ValidateInviteTokenView, AcceptInviteView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('invite/validate/<str:token>/', ValidateInviteTokenView.as_view(), name='invite-validate'),
    path('invite/accept/', AcceptInviteView.as_view(), name='invite-accept'),
]
```

---

### Step 4.4: Run tests — expect PASS

- [ ] Run: `docker compose exec backend pytest apps/invitations/tests/test_views.py -v`
- [ ] Confirm: All tests pass (green).

---

### Step 4.5: Commit

- [ ] `git add backend/apps/invitations/views.py backend/apps/organisations/urls.py backend/apps/accounts/urls.py backend/apps/invitations/tests/test_views.py`
- [ ] `git commit -m "feat(invitations): add CT invite admin API and public invite accept/validate endpoints"`

---

## Task 5: Frontend Types + API Layer + Hooks

**Files:**
- `frontend/src/types/organisation.ts` — create
- `frontend/src/lib/api/organisations.ts` — create
- `frontend/src/lib/api/invitations.ts` — create
- `frontend/src/hooks/useCtOrganisations.ts` — create

Note: The existing `frontend/src/lib/api.ts` exports `api` as default. The new files at `frontend/src/lib/api/organisations.ts` and `frontend/src/lib/api/invitations.ts` are new files in a subdirectory — they import from `@/lib/api` which resolves to `api.ts`. No existing file is modified.

---

### Step 5.1: Write failing test (TypeScript build check)

- [ ] Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
- [ ] Record the current baseline error count (likely 0 from Phase 1).

---

### Step 5.2: Run baseline — confirm it passes

- [ ] Confirm: `npx tsc --noEmit` exits 0 (no type errors before changes).

---

### Step 5.3: Implement types, API layer, and hooks

- [ ] Create `frontend/src/types/organisation.ts` with the full content below:

```typescript
export type OrganisationStatus = 'PENDING' | 'PAID' | 'ACTIVE' | 'SUSPENDED'

export interface OrganisationListItem {
  id: string
  name: string
  slug: string
  status: OrganisationStatus
  licence_count: number
  created_at: string
}

export interface StateTransition {
  id: string
  from_status: OrganisationStatus
  to_status: OrganisationStatus
  note: string
  transitioned_by_email: string
  created_at: string
}

export interface Organisation {
  id: string
  name: string
  slug: string
  status: OrganisationStatus
  licence_count: number
  address: string
  phone: string
  email: string
  logo_url: string | null
  created_by_email: string
  created_at: string
  updated_at: string
  state_transitions: StateTransition[]
}

export interface OrgAdmin {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  is_active: boolean
  is_onboarding_email_sent: boolean
}

export interface CtDashboardStats {
  total_organisations: number
  active_organisations: number
  pending_organisations: number
  paid_organisations: number
  suspended_organisations: number
  total_employees: number
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
```

- [ ] Create `frontend/src/lib/api/organisations.ts` with the full content below:

```typescript
import api from '@/lib/api'
import type {
  Organisation, OrganisationListItem, OrgAdmin,
  CtDashboardStats, PaginatedResponse,
} from '@/types/organisation'

export async function fetchCtStats(): Promise<CtDashboardStats> {
  const { data } = await api.get('/ct/dashboard/')
  return data
}

export async function fetchOrganisations(params?: {
  search?: string
  status?: string
  page?: number
}): Promise<PaginatedResponse<OrganisationListItem>> {
  const { data } = await api.get('/ct/organisations/', { params })
  return data
}

export async function fetchOrganisation(id: string): Promise<Organisation> {
  const { data } = await api.get(`/ct/organisations/${id}/`)
  return data
}

export async function createOrganisation(payload: {
  name: string
  licence_count: number
  address?: string
  phone?: string
  email?: string
}): Promise<Organisation> {
  const { data } = await api.post('/ct/organisations/', payload)
  return data
}

export async function updateOrganisation(id: string, payload: {
  name?: string
  address?: string
  phone?: string
  email?: string
}): Promise<Organisation> {
  const { data } = await api.patch(`/ct/organisations/${id}/`, payload)
  return data
}

export async function activateOrganisation(id: string, note?: string): Promise<Organisation> {
  const { data } = await api.post(`/ct/organisations/${id}/activate/`, { note: note ?? '' })
  return data
}

export async function suspendOrganisation(id: string, note?: string): Promise<Organisation> {
  const { data } = await api.post(`/ct/organisations/${id}/suspend/`, { note: note ?? '' })
  return data
}

export async function fetchOrgLicences(id: string): Promise<{ total_count: number; used_count: number }> {
  const { data } = await api.get(`/ct/organisations/${id}/licences/`)
  return data
}

export async function updateOrgLicences(id: string, licence_count: number): Promise<{ total_count: number; used_count: number }> {
  const { data } = await api.patch(`/ct/organisations/${id}/licences/`, { licence_count })
  return data
}

export async function fetchOrgAdmins(id: string): Promise<OrgAdmin[]> {
  const { data } = await api.get(`/ct/organisations/${id}/admins/`)
  return data
}

export async function inviteOrgAdmin(id: string, payload: {
  email: string
  first_name: string
  last_name: string
}): Promise<{ user_id: string; email: string; status: string; expires_at: string }> {
  const { data } = await api.post(`/ct/organisations/${id}/admins/invite/`, payload)
  return data
}

export async function resendOrgAdminInvite(orgId: string, userId: string): Promise<void> {
  await api.post(`/ct/organisations/${orgId}/admins/${userId}/resend-invite/`)
}
```

- [ ] Create `frontend/src/lib/api/invitations.ts` with the full content below:

```typescript
import api from '@/lib/api'

export async function validateInviteToken(token: string): Promise<{
  email: string
  role: string
  organisation_name: string | null
}> {
  const { data } = await api.get(`/auth/invite/validate/${token}/`)
  return data
}

export async function acceptInvite(payload: {
  token: string
  password: string
  confirm_password: string
}): Promise<{
  access: string
  refresh: string
  user: { id: string; email: string; role: string; org_id: string | null }
}> {
  const { data } = await api.post('/auth/invite/accept/', payload)
  return data
}
```

- [ ] Create `frontend/src/hooks/useCtOrganisations.ts` with the full content below:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCtStats, fetchOrganisations, fetchOrganisation,
  createOrganisation, updateOrganisation,
  activateOrganisation, suspendOrganisation,
  fetchOrgAdmins, inviteOrgAdmin, updateOrgLicences,
} from '@/lib/api/organisations'

export function useCtStats() {
  return useQuery({ queryKey: ['ct', 'stats'], queryFn: fetchCtStats })
}

export function useOrganisations(params?: { search?: string; status?: string; page?: number }) {
  return useQuery({
    queryKey: ['ct', 'organisations', params],
    queryFn: () => fetchOrganisations(params),
  })
}

export function useOrganisation(id: string) {
  return useQuery({
    queryKey: ['ct', 'organisations', id],
    queryFn: () => fetchOrganisation(id),
    enabled: !!id,
  })
}

export function useCreateOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createOrganisation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations'] }),
  })
}

export function useUpdateOrganisation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof updateOrganisation>[1]) => updateOrganisation(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] }),
  })
}

export function useActivateOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => activateOrganisation(id, note),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
    },
  })
}

export function useSuspendOrganisation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) => suspendOrganisation(id, note),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['ct', 'organisations', id] })
      qc.invalidateQueries({ queryKey: ['ct', 'stats'] })
    },
  })
}

export function useOrgAdmins(orgId: string) {
  return useQuery({
    queryKey: ['ct', 'organisations', orgId, 'admins'],
    queryFn: () => fetchOrgAdmins(orgId),
    enabled: !!orgId,
  })
}

export function useInviteOrgAdmin(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof inviteOrgAdmin>[1]) => inviteOrgAdmin(orgId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId, 'admins'] }),
  })
}

export function useUpdateOrgLicences(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (count: number) => updateOrgLicences(orgId, count),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ct', 'organisations', orgId] }),
  })
}
```

---

### Step 5.4: Run TypeScript check — expect PASS

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 — no type errors.

---

### Step 5.5: Commit

- [ ] `git add frontend/src/types/organisation.ts frontend/src/lib/api/organisations.ts frontend/src/lib/api/invitations.ts frontend/src/hooks/useCtOrganisations.ts`
- [ ] `git commit -m "feat(frontend): add organisation types, API layer, and TanStack Query hooks"`

---

## Task 6: CT Dashboard (real data) + Organisations List Page

**Files:**
- `frontend/src/pages/ct/DashboardPage.tsx` — modify (replace placeholder with real data)
- `frontend/src/pages/ct/OrganisationsPage.tsx` — create

---

### Step 6.1: Write failing test (TypeScript build check)

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 (baseline still clean before changes).

---

### Step 6.2: Confirm baseline passes

- [ ] Confirm: No errors in current state.

---

### Step 6.3: Implement Dashboard and Organisations pages

- [ ] Replace `frontend/src/pages/ct/DashboardPage.tsx` entirely with the full content below:

```tsx
import { useCtStats, useOrganisations } from '@/hooks/useCtOrganisations'
import { Link } from 'react-router-dom'
import { Building2, Users, Clock, CheckCircle } from 'lucide-react'
import type { CtDashboardStats } from '@/types/organisation'

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number | undefined; icon: typeof Building2; color: string
}) {
  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
      </div>
      <p className="mt-3 text-3xl font-bold text-foreground">
        {value === undefined ? (
          <span className="inline-block h-8 w-16 animate-pulse rounded bg-muted" />
        ) : value}
      </p>
    </div>
  )
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-blue-100 text-blue-800',
  ACTIVE: 'bg-green-100 text-green-800',
  SUSPENDED: 'bg-red-100 text-red-800',
}

export function CTDashboardPage() {
  const { data: stats } = useCtStats()
  const { data: recent } = useOrganisations({ page: 1 })

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">Platform overview</p>
        </div>
        <Link
          to="/ct/organisations/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          New Organisation
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Organisations" value={stats?.total_organisations} icon={Building2} color="bg-primary" />
        <StatCard label="Active" value={stats?.active_organisations} icon={CheckCircle} color="bg-green-500" />
        <StatCard label="Pending Payment" value={stats?.pending_organisations} icon={Clock} color="bg-yellow-500" />
        <StatCard label="Total Employees" value={stats?.total_employees} icon={Users} color="bg-purple-500" />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-medium text-foreground mb-4">Recent Organisations</h2>
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          {!recent ? (
            <div className="divide-y">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-4 w-48 animate-pulse rounded bg-muted" />
                  <div className="h-5 w-16 animate-pulse rounded bg-muted" />
                </div>
              ))}
            </div>
          ) : recent.results.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground text-sm">
              No organisations yet.{' '}
              <Link to="/ct/organisations/new" className="text-primary hover:underline">Create one</Link>.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Licences</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {recent.results.slice(0, 5).map((org) => (
                  <tr key={org.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <Link to={`/ct/organisations/${org.id}`} className="font-medium text-foreground hover:text-primary">
                        {org.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[org.status] ?? 'bg-gray-100 text-gray-800'}`}>
                        {org.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{org.licence_count}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] Create `frontend/src/pages/ct/OrganisationsPage.tsx` with the full content below:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Plus } from 'lucide-react'
import { useOrganisations } from '@/hooks/useCtOrganisations'
import type { OrganisationStatus } from '@/types/organisation'

const STATUS_COLORS: Record<OrganisationStatus, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-blue-100 text-blue-800',
  ACTIVE: 'bg-green-100 text-green-800',
  SUSPENDED: 'bg-red-100 text-red-800',
}

const STATUSES: Array<OrganisationStatus | ''> = ['', 'PENDING', 'PAID', 'ACTIVE', 'SUSPENDED']

export function OrganisationsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<OrganisationStatus | ''>('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useOrganisations({
    search: search || undefined,
    status: statusFilter || undefined,
    page,
  })

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Organisations</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${data.count} total` : 'Loading…'}
          </p>
        </div>
        <Link
          to="/ct/organisations/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          New Organisation
        </Link>
      </div>

      <div className="mt-6 flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search organisations…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as OrganisationStatus | ''); setPage(1) }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s || 'All statuses'}</option>
          ))}
        </select>
      </div>

      <div className="mt-4 rounded-xl border bg-card shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="divide-y">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 p-4">
                <div className="h-4 w-48 animate-pulse rounded bg-muted" />
                <div className="h-5 w-16 animate-pulse rounded bg-muted" />
                <div className="h-4 w-12 animate-pulse rounded bg-muted" />
              </div>
            ))}
          </div>
        ) : data?.results.length === 0 ? (
          <div className="p-16 text-center">
            <p className="text-muted-foreground text-sm">No organisations found.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Licences</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {data?.results.map((org) => (
                <tr key={org.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium text-foreground">{org.name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[org.status]}`}>
                      {org.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{org.licence_count}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(org.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/ct/organisations/${org.id}`}
                      className="text-sm text-primary hover:underline"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && data.count > 20 && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>Page {page}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={!data.previous}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={!data.next}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

### Step 6.4: Run TypeScript check — expect PASS

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 — no type errors.

---

### Step 6.5: Commit

- [ ] `git add frontend/src/pages/ct/DashboardPage.tsx frontend/src/pages/ct/OrganisationsPage.tsx`
- [ ] `git commit -m "feat(frontend/ct): replace dashboard placeholder with real data; add organisations list page"`

---

## Task 7: CT New Organisation + Organisation Detail Page

**Files:**
- `frontend/src/pages/ct/NewOrganisationPage.tsx` — create
- `frontend/src/pages/ct/OrganisationDetailPage.tsx` — create

---

### Step 7.1: Write failing test (TypeScript build check)

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 (baseline still clean before changes).

---

### Step 7.2: Confirm baseline passes

- [ ] Confirm: No errors.

---

### Step 7.3: Implement New Organisation and Detail pages

- [ ] Create `frontend/src/pages/ct/NewOrganisationPage.tsx` with the full content below:

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateOrganisation } from '@/hooks/useCtOrganisations'
import { cn } from '@/lib/utils'

export function NewOrganisationPage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending } = useCreateOrganisation()
  const [form, setForm] = useState({ name: '', licence_count: 1, address: '', phone: '', email: '' })
  const [error, setError] = useState<string | null>(null)

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [field]: field === 'licence_count' ? Number(e.target.value) : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const org = await mutateAsync(form)
      navigate(`/ct/organisations/${org.id}`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { name?: string[] } } }
      setError(e.response?.data?.name?.[0] ?? 'Failed to create organisation.')
    }
  }

  const field = (id: string, label: string, type = 'text', required = false) => (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-foreground mb-1.5">
        {label}{required && <span className="text-destructive ml-1">*</span>}
      </label>
      <input
        id={id} type={type} required={required}
        value={String(form[id as keyof typeof form])}
        onChange={set(id)}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
      />
    </div>
  )

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">New Organisation</h1>
        <p className="mt-1 text-sm text-muted-foreground">Create a new tenant organisation.</p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
        {field('name', 'Organisation name', 'text', true)}
        {field('licence_count', 'Licence count', 'number', true)}
        {field('email', 'Contact email', 'email')}
        {field('phone', 'Phone')}
        {field('address', 'Address')}

        {error && (
          <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending}
            className={cn(
              'rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
              'hover:opacity-90 disabled:opacity-60',
            )}
          >
            {isPending ? 'Creating…' : 'Create Organisation'}
          </button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] Create `frontend/src/pages/ct/OrganisationDetailPage.tsx` with the full content below:

```tsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import {
  useOrganisation, useActivateOrganisation, useSuspendOrganisation,
  useOrgAdmins, useInviteOrgAdmin, useUpdateOrgLicences,
} from '@/hooks/useCtOrganisations'
import { cn } from '@/lib/utils'
import type { OrganisationStatus } from '@/types/organisation'

const STATUS_COLORS: Record<OrganisationStatus, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-blue-100 text-blue-800',
  ACTIVE: 'bg-green-100 text-green-800',
  SUSPENDED: 'bg-red-100 text-red-800',
}

type Tab = 'info' | 'licences' | 'admins' | 'history'

function InviteAdminModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const [form, setForm] = useState({ email: '', first_name: '', last_name: '' })
  const [error, setError] = useState<string | null>(null)
  const { mutateAsync, isPending } = useInviteOrgAdmin(orgId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await mutateAsync(form)
      onClose()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } }
      setError(e.response?.data?.error ?? 'Failed to send invite.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-foreground mb-4">Invite Organisation Admin</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          {(['email', 'first_name', 'last_name'] as const).map((field) => (
            <div key={field}>
              <label className="block text-sm font-medium text-foreground mb-1.5 capitalize">
                {field.replace('_', ' ')}
              </label>
              <input
                type={field === 'email' ? 'email' : 'text'}
                required
                value={form[field]}
                onChange={(e) => setForm(f => ({ ...f, [field]: e.target.value }))}
                className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          ))}
          {error && (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border px-4 py-2 text-sm">Cancel</button>
            <button
              type="submit" disabled={isPending}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
            >
              {isPending ? 'Sending…' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function OrganisationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('info')
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const { data: org, isLoading } = useOrganisation(id!)
  const { data: admins } = useOrgAdmins(id!)
  const { mutateAsync: activate } = useActivateOrganisation()
  const { mutateAsync: suspend } = useSuspendOrganisation()
  const { mutateAsync: updateLicences, isPending: updatingLicences } = useUpdateOrgLicences(id!)
  const [newLicenceCount, setNewLicenceCount] = useState<number | null>(null)

  if (isLoading || !org) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="h-48 w-full animate-pulse rounded bg-muted" />
      </div>
    )
  }

  const handleActivate = async () => {
    setActionError(null)
    try { await activate({ id: id! }) } catch { setActionError('Could not activate. Check org status.') }
  }

  const handleSuspend = async () => {
    if (!confirm('Suspend this organisation? Admins will lose access.')) return
    setActionError(null)
    try { await suspend({ id: id! }) } catch { setActionError('Could not suspend.') }
  }

  const handleLicenceUpdate = async () => {
    if (newLicenceCount === null) return
    await updateLicences(newLicenceCount)
    setNewLicenceCount(null)
  }

  const TABS: Array<{ id: Tab; label: string }> = [
    { id: 'info', label: 'Info' },
    { id: 'licences', label: 'Licences' },
    { id: 'admins', label: 'Admins' },
    { id: 'history', label: 'History' },
  ]

  return (
    <div>
      {showInviteModal && <InviteAdminModal orgId={id!} onClose={() => setShowInviteModal(false)} />}

      <button onClick={() => navigate(-1)} className="mb-4 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{org.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[org.status]}`}>
              {org.status}
            </span>
            <span className="text-sm text-muted-foreground">/{org.slug}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {org.status === 'PENDING' && (
            <button onClick={handleActivate}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">
              Mark Paid
            </button>
          )}
          {org.status === 'ACTIVE' && (
            <button onClick={handleSuspend}
              className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700">
              Suspend
            </button>
          )}
          {(org.status === 'PAID' || org.status === 'ACTIVE') && (
            <button onClick={() => setShowInviteModal(true)}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90">
              Invite Admin
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="mt-3 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
          {actionError}
        </div>
      )}

      <div className="mt-6 border-b">
        <div className="flex gap-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                tab === t.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        {tab === 'info' && (
          <div className="rounded-xl border bg-card p-6 shadow-sm space-y-3">
            {[
              ['Name', org.name],
              ['Email', org.email || '—'],
              ['Phone', org.phone || '—'],
              ['Address', org.address || '—'],
              ['Created by', org.created_by_email],
              ['Created', new Date(org.created_at).toLocaleDateString()],
            ].map(([label, value]) => (
              <div key={label} className="flex gap-4 py-2 border-b last:border-0">
                <span className="w-32 shrink-0 text-sm font-medium text-muted-foreground">{label}</span>
                <span className="text-sm text-foreground">{value}</span>
              </div>
            ))}
          </div>
        )}

        {tab === 'licences' && (
          <div className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-6">
              <div>
                <p className="text-sm text-muted-foreground">Total licences</p>
                <p className="text-3xl font-bold text-foreground">{org.licence_count}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number" min={1}
                value={newLicenceCount ?? org.licence_count}
                onChange={(e) => setNewLicenceCount(Number(e.target.value))}
                className="w-32 rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                onClick={handleLicenceUpdate}
                disabled={updatingLicences || newLicenceCount === null}
                className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {updatingLicences ? 'Saving…' : 'Update'}
              </button>
            </div>
          </div>
        )}

        {tab === 'admins' && (
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
            {!admins || admins.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                No admins yet.{' '}
                {(org.status === 'PAID' || org.status === 'ACTIVE') && (
                  <button onClick={() => setShowInviteModal(true)} className="text-primary hover:underline">
                    Invite one
                  </button>
                )}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Email</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {admins.map((admin) => (
                    <tr key={admin.id}>
                      <td className="px-4 py-3 font-medium">{admin.full_name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{admin.email}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${admin.is_active ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {admin.is_active ? 'Active' : 'Pending'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === 'history' && (
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
            {org.state_transitions.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">No state changes yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">From</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">To</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">By</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Note</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">When</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {org.state_transitions.map((t) => (
                    <tr key={t.id}>
                      <td className="px-4 py-3 text-muted-foreground">{t.from_status}</td>
                      <td className="px-4 py-3 font-medium">{t.to_status}</td>
                      <td className="px-4 py-3 text-muted-foreground">{t.transitioned_by_email}</td>
                      <td className="px-4 py-3 text-muted-foreground">{t.note || '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {new Date(t.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

---

### Step 7.4: Run TypeScript check — expect PASS

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 — no type errors.

---

### Step 7.5: Commit

- [ ] `git add frontend/src/pages/ct/NewOrganisationPage.tsx frontend/src/pages/ct/OrganisationDetailPage.tsx`
- [ ] `git commit -m "feat(frontend/ct): add new organisation form and organisation detail page with tabs"`

---

## Task 8: Wire Routes + Update InviteAcceptPage + E2E Verification

**Files:**
- `frontend/src/routes/index.tsx` — modify: add CT organisation routes
- `frontend/src/pages/auth/InviteAcceptPage.tsx` — modify: wire to real `acceptInvite` API, auto-login after accept

---

### Step 8.1: Write failing test (TypeScript build check)

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 (baseline before adding new imports).

---

### Step 8.2: Confirm baseline passes

- [ ] Confirm: No errors.

---

### Step 8.3: Wire routes and update InviteAcceptPage

- [ ] Modify `frontend/src/routes/index.tsx` — replace the CT section to add the three new organisation routes. The resulting file must be:

```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { CTLayout } from '@/components/layouts/CTLayout'
import { OrgLayout } from '@/components/layouts/OrgLayout'
import { EmployeeLayout } from '@/components/layouts/EmployeeLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { InviteAcceptPage } from '@/pages/auth/InviteAcceptPage'
import { RequestPasswordResetPage } from '@/pages/auth/RequestPasswordResetPage'
import { CTDashboardPage } from '@/pages/ct/DashboardPage'
import { OrganisationsPage } from '@/pages/ct/OrganisationsPage'
import { NewOrganisationPage } from '@/pages/ct/NewOrganisationPage'
import { OrganisationDetailPage } from '@/pages/ct/OrganisationDetailPage'
import { OrgDashboardPage } from '@/pages/org/DashboardPage'
import { EmployeeDashboardPage } from '@/pages/employee/DashboardPage'

export const router = createBrowserRouter([
  // Public auth routes
  {
    path: '/auth/login',
    element: <LoginPage />,
  },
  {
    path: '/auth/invite/:token',
    element: <InviteAcceptPage />,
  },
  {
    path: '/auth/reset-password',
    element: <RequestPasswordResetPage />,
  },

  // Control Tower routes
  {
    element: <ProtectedRoute allowedRoles={['CONTROL_TOWER']} />,
    children: [
      {
        element: <CTLayout />,
        children: [
          { path: '/ct/dashboard', element: <CTDashboardPage /> },
          { path: '/ct/organisations', element: <OrganisationsPage /> },
          { path: '/ct/organisations/new', element: <NewOrganisationPage /> },
          { path: '/ct/organisations/:id', element: <OrganisationDetailPage /> },
        ],
      },
    ],
  },

  // Organisation Admin routes
  {
    element: <ProtectedRoute allowedRoles={['ORG_ADMIN']} />,
    children: [
      {
        element: <OrgLayout />,
        children: [
          { path: '/org/dashboard', element: <OrgDashboardPage /> },
          // Phase 3: Locations, departments, employees routes will be added here
        ],
      },
    ],
  },

  // Employee routes
  {
    element: <ProtectedRoute allowedRoles={['EMPLOYEE']} />,
    children: [
      {
        element: <EmployeeLayout />,
        children: [
          { path: '/me/dashboard', element: <EmployeeDashboardPage /> },
          // Phase 4: Profile, education, documents routes will be added here
        ],
      },
    ],
  },

  // Root redirect
  { path: '/', element: <Navigate to="/auth/login" replace /> },
  { path: '*', element: <Navigate to="/auth/login" replace /> },
])
```

- [ ] Modify `frontend/src/pages/auth/InviteAcceptPage.tsx` — update `handleSubmit` to call `acceptInvite` from the new invitations API and auto-redirect to the role-appropriate dashboard after accepting. The resulting file must be:

```tsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '@/lib/api'
import { acceptInvite } from '@/lib/api/invitations'
import { cn } from '@/lib/utils'

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [tokenValid, setTokenValid] = useState<boolean | null>(null)
  const [inviteInfo, setInviteInfo] = useState<{ email: string; role: string } | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    api.get(`/auth/invite/validate/${token}/`)
      .then((res) => {
        setTokenValid(true)
        setInviteInfo(res.data)
      })
      .catch(() => setTokenValid(false))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setError('')
    setIsLoading(true)
    try {
      const result = await acceptInvite({ token: token!, password, confirm_password: confirmPassword })
      localStorage.setItem('access_token', result.access)
      localStorage.setItem('refresh_token', result.refresh)
      const roleRoutes: Record<string, string> = {
        CONTROL_TOWER: '/ct/dashboard',
        ORG_ADMIN: '/org/dashboard',
        EMPLOYEE: '/me/dashboard',
      }
      navigate(roleRoutes[result.user.role] ?? '/auth/login', { replace: true })
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: string; token?: string[] } } }
      setError(
        axiosError.response?.data?.error ??
        axiosError.response?.data?.token?.[0] ??
        'Failed to set password. The link may have expired.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  if (tokenValid === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-white border-t-transparent" />
      </div>
    )
  }

  if (tokenValid === false) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Invitation Expired</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            This invitation link is invalid or has expired. Please contact your administrator to resend the invite.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">Clarisal</h1>
          <p className="mt-2 text-sm text-white/60">Set up your account</p>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Create your password</h2>
          {inviteInfo && (
            <p className="mt-1 text-sm text-muted-foreground">
              Setting up account for <strong>{inviteInfo.email}</strong>
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">New password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Minimum 8 characters"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Confirm password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Repeat your password"
              />
            </div>

            {error && (
              <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                'transition-opacity hover:opacity-90',
                isLoading && 'opacity-60 cursor-not-allowed'
              )}
            >
              {isLoading ? 'Setting password…' : 'Set password & sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

---

### Step 8.4: Run TypeScript check — expect PASS

- [ ] Run: `cd frontend && npx tsc --noEmit`
- [ ] Confirm: Exits 0 — no type errors.

---

### Step 8.5: Run full backend test suite

- [ ] Run: `docker compose exec backend pytest apps/ -v`
- [ ] Confirm: All tests pass across all apps.

---

### Step 8.6: Build frontend

- [ ] Run: `cd frontend && npm run build`
- [ ] Confirm: Build exits 0 with no errors.

---

### Step 8.7: Commit

- [ ] `git add frontend/src/routes/index.tsx frontend/src/pages/auth/InviteAcceptPage.tsx`
- [ ] `git commit -m "feat(frontend): wire CT routes and update InviteAcceptPage for auto-login after invite accept"`

---

## Self-Review Checklist

### Spec coverage — all 13 Phase 2 items

| Item | Covered in |
|---|---|
| Organisation CRUD | Task 1 (services), Task 3 (views + urls), Task 6/7 (UI) |
| State machine PENDING→PAID→ACTIVE→SUSPENDED | Task 1 `transition_organisation_state` + `VALID_TRANSITIONS` dict |
| State transition audit record | Task 1 `OrganisationStateTransition.objects.create` in service |
| Licence management (CRUD) | Task 1 `update_licence_count`, Task 3 `OrganisationLicencesView`, Task 7 licences tab |
| Org admin invitation creation | Task 2 `create_org_admin_invitation`, Task 4 `InviteOrgAdminView` |
| Invitation revoke on resend | Task 2 service: `Invitation.objects.filter(...).update(status=REVOKED)` |
| Celery email task with retry | Task 2 `tasks.py` with `autoretry_for`, `max_retries=3` |
| Invite email idempotency | Task 2 `tasks.py`: `if invite.email_sent: return` |
| Invite validate + accept endpoints | Task 4 `ValidateInviteTokenView`, `AcceptInviteView` wired to `/api/auth/` |
| Auto org PAID→ACTIVE on admin onboard | Task 2 `accept_invitation` calls `transition_organisation_state` |
| CT Dashboard (real data) | Task 5 `useCtStats` hook + `fetchCtStats` API fn, Task 6 `CTDashboardPage` |
| CT Org list page with search/filter/pagination | Task 6 `OrganisationsPage` |
| CT Org detail page (info/licences/admins/history tabs) | Task 7 `OrganisationDetailPage` |
| CT New Organisation page | Task 7 `NewOrganisationPage` |
| CT Invite Admin modal | Task 7 `InviteAdminModal` inside `OrganisationDetailPage` |
| InviteAcceptPage auto-login | Task 8 `InviteAcceptPage` updated to call `acceptInvite` + store tokens + navigate |
| All routes wired | Task 8 `routes/index.tsx` updated |

### Placeholder scan

Confirmed: No TBD / TODO / placeholder / "implement here" strings in any code block above.

### Type consistency — method names cross-task

| Function | Defined in | Called in |
|---|---|---|
| `create_organisation` | Task 1 `services.py` | Task 3 `views.py` `OrganisationListCreateView.post` |
| `transition_organisation_state` | Task 1 `services.py` | Task 3 `OrganisationActivateView`, `OrganisationSuspendView`; Task 2 `accept_invitation` |
| `update_licence_count` | Task 1 `services.py` | Task 3 `OrganisationLicencesView.patch` |
| `get_ct_dashboard_stats` | Task 1 `services.py` | Task 3 `CTDashboardStatsView.get` |
| `create_org_admin_invitation` | Task 2 `services.py` | Task 4 `InviteOrgAdminView.post`, `ResendOrgAdminInviteView.post` |
| `validate_invite_token` | Task 2 `services.py` | Task 4 `ValidateInviteTokenView.get`, `accept_invitation` internals |
| `accept_invitation` | Task 2 `services.py` | Task 4 `AcceptInviteView.post` |
| `send_invite_email` | Task 2 `tasks.py` | Task 2 `services.py` `transaction.on_commit` callback |
| `fetchCtStats` | Task 5 `api/organisations.ts` | Task 5 `useCtStats` hook |
| `fetchOrganisations` | Task 5 `api/organisations.ts` | Task 5 `useOrganisations` hook |
| `fetchOrganisation` | Task 5 `api/organisations.ts` | Task 5 `useOrganisation` hook |
| `createOrganisation` | Task 5 `api/organisations.ts` | Task 5 `useCreateOrganisation` hook |
| `activateOrganisation` | Task 5 `api/organisations.ts` | Task 5 `useActivateOrganisation` hook |
| `suspendOrganisation` | Task 5 `api/organisations.ts` | Task 5 `useSuspendOrganisation` hook |
| `fetchOrgAdmins` | Task 5 `api/organisations.ts` | Task 5 `useOrgAdmins` hook |
| `inviteOrgAdmin` | Task 5 `api/organisations.ts` | Task 5 `useInviteOrgAdmin` hook |
| `updateOrgLicences` | Task 5 `api/organisations.ts` | Task 5 `useUpdateOrgLicences` hook |
| `acceptInvite` | Task 5 `api/invitations.ts` | Task 8 `InviteAcceptPage.handleSubmit` |
| `get_organisations` | Task 1 `repositories.py` | Task 3 `OrganisationListCreateView.get` |
| `get_org_admins` | Task 1 `repositories.py` | Task 3 `OrganisationAdminsView.get`, Task 4 `InviteOrgAdminView` (import) |
| `useCtStats` | Task 5 `hooks/useCtOrganisations.ts` | Task 6 `CTDashboardPage` |
| `useOrganisations` | Task 5 `hooks/useCtOrganisations.ts` | Task 6 `CTDashboardPage`, `OrganisationsPage` |
| `useOrganisation` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `OrganisationDetailPage` |
| `useCreateOrganisation` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `NewOrganisationPage` |
| `useActivateOrganisation` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `OrganisationDetailPage` |
| `useSuspendOrganisation` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `OrganisationDetailPage` |
| `useOrgAdmins` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `OrganisationDetailPage` |
| `useInviteOrgAdmin` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `InviteAdminModal` |
| `useUpdateOrgLicences` | Task 5 `hooks/useCtOrganisations.ts` | Task 7 `OrganisationDetailPage` |
