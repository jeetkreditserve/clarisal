from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import AccountType, User, UserRole
from apps.accounts.permissions import ApprovalActionsAllowed, BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.employees.models import Employee, EmployeeOnboardingStatus, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


def _attach_session(request, **values):
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    for key, value in values.items():
        request.session[key] = value
    request.session.save()
    return request


def _activate_paid_licences(organisation, actor):
    today = timezone.localdate()
    batch = create_licence_batch(
        organisation=organisation,
        quantity=5,
        price_per_licence_per_month=Decimal('100.00'),
        start_date=today - timedelta(days=7),
        end_date=today + timedelta(days=30),
        created_by=actor,
    )
    mark_licence_batch_paid(batch, paid_by=actor, paid_at=today - timedelta(days=1))
    return batch


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@clarisal.com',
        password='TestPass@123',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(
        name='Northstar Labs',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def org_admin_user(organisation):
    user = User.objects.create_user(
        email='admin@northstar.com',
        password='TestPass@123',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    return user


@pytest.fixture
def employee_user(organisation):
    user = User.objects.create_user(
        email='employee@northstar.com',
        password='TestPass@123',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code='EMP-001',
        status=EmployeeStatus.ACTIVE,
        onboarding_status=EmployeeOnboardingStatus.COMPLETE,
    )
    return user


@pytest.mark.django_db
class TestAccountPermissions:
    def test_is_org_admin_allows_active_admin_membership(self, request_factory, organisation, org_admin_user):
        request = _attach_session(
            request_factory.get('/api/v1/org/approvals/workflows/'),
            active_workspace_kind='ADMIN',
            active_admin_org_id=str(organisation.id),
        )
        request.user = org_admin_user

        assert IsOrgAdmin().has_permission(request, object()) is True

    def test_is_org_admin_rejects_workforce_user_without_admin_membership(self, request_factory, organisation):
        user = User.objects.create_user(
            email='employee-only@northstar.com',
            password='TestPass@123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        request = _attach_session(
            request_factory.get('/api/v1/org/approvals/workflows/'),
            active_workspace_kind='ADMIN',
            active_admin_org_id=str(organisation.id),
        )
        request.user = user

        assert IsOrgAdmin().has_permission(request, object()) is False

    def test_belongs_to_active_org_rejects_suspended_access(self, request_factory, organisation, org_admin_user):
        organisation.access_state = OrganisationAccessState.SUSPENDED
        organisation.save(update_fields=['access_state', 'modified_at'])
        request = _attach_session(
            request_factory.get('/api/v1/org/approvals/workflows/'),
            active_workspace_kind='ADMIN',
            active_admin_org_id=str(organisation.id),
        )
        request.user = org_admin_user

        assert BelongsToActiveOrg().has_permission(request, object()) is False

    def test_org_admin_mutation_allowed_blocks_when_licences_are_expired(self, request_factory, organisation, org_admin_user):
        request = _attach_session(
            request_factory.post('/api/v1/org/approvals/workflows/'),
            active_workspace_kind='ADMIN',
            active_admin_org_id=str(organisation.id),
        )
        request.user = org_admin_user

        assert OrgAdminMutationAllowed().has_permission(request, object()) is False

    def test_org_admin_mutation_allowed_allows_when_paid_batch_is_active(self, request_factory, organisation, org_admin_user):
        _activate_paid_licences(organisation, org_admin_user)
        request = _attach_session(
            request_factory.post('/api/v1/org/approvals/workflows/'),
            active_workspace_kind='ADMIN',
            active_admin_org_id=str(organisation.id),
        )
        request.user = org_admin_user

        assert OrgAdminMutationAllowed().has_permission(request, object()) is True

    def test_approval_actions_allowed_uses_employee_workspace(self, request_factory, organisation, employee_user):
        _activate_paid_licences(organisation, employee_user)
        request = _attach_session(
            request_factory.post('/api/v1/me/approvals/action/approve/'),
            active_workspace_kind='EMPLOYEE',
            active_employee_org_id=str(organisation.id),
        )
        request.user = employee_user

        assert ApprovalActionsAllowed().has_permission(request, object()) is True

    def test_approval_actions_allowed_blocks_employee_workspace_without_paid_licences(self, request_factory, organisation, employee_user):
        request = _attach_session(
            request_factory.post('/api/v1/me/approvals/action/approve/'),
            active_workspace_kind='EMPLOYEE',
            active_employee_org_id=str(organisation.id),
        )
        request.user = employee_user

        assert ApprovalActionsAllowed().has_permission(request, object()) is False
