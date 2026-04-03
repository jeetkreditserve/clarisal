from unittest.mock import patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware

from apps.accounts.models import AccountType, User, UserRole
from apps.accounts.workspaces import (
    get_default_route,
    get_workspace_state,
    set_active_admin_organisation,
    sync_user_role,
)
from apps.employees.models import Employee, EmployeeOnboardingStatus, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


def _request_with_session(factory, path='/', **session_values):
    request = factory.get(path)
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    for key, value in session_values.items():
        request.session[key] = value
    request.session.save()
    return request


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct-workspaces@clarisal.com',
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


@pytest.mark.django_db
class TestWorkspaceHelpers:
    def test_get_workspace_state_prefers_admin_workspace_when_memberships_exist(self, rf, organisation):
        user = User.objects.create_user(
            email='hybrid@northstar.com',
            password='TestPass@123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            user=user,
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        Employee.objects.create(
            organisation=organisation,
            user=user,
            employee_code='EMP-100',
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.COMPLETE,
        )

        state = get_workspace_state(user, _request_with_session(rf))

        assert state.active_kind == 'ADMIN'
        assert state.active_admin_membership is not None
        assert state.active_admin_membership.organisation_id == organisation.id
        assert state.active_employee is not None

    @patch('apps.organisations.services.is_org_admin_setup_required', return_value=True)
    def test_get_default_route_returns_org_setup_for_admins_requiring_setup(self, _mock_setup_required, rf, organisation):
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

        route = get_default_route(user, _request_with_session(rf))

        assert route == '/org/setup'

    def test_get_default_route_returns_employee_onboarding_for_incomplete_employee(self, rf, organisation):
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
            employee_code='EMP-101',
            status=EmployeeStatus.ACTIVE,
            onboarding_status=EmployeeOnboardingStatus.BASIC_DETAILS_PENDING,
        )

        route = get_default_route(user, _request_with_session(rf))

        assert route == '/me/onboarding'

    def test_set_active_admin_organisation_raises_when_user_has_no_membership(self, rf, organisation):
        user = User.objects.create_user(
            email='outsider@northstar.com',
            password='TestPass@123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        request = _request_with_session(rf)

        with pytest.raises(ValueError, match='administrator access'):
            set_active_admin_organisation(request, user, organisation.id)

    def test_sync_user_role_promotes_user_to_org_admin_when_membership_exists(self, organisation):
        user = User.objects.create_user(
            email='promote@northstar.com',
            password='TestPass@123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            user=user,
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )

        sync_user_role(user)
        user.refresh_from_db()

        assert user.role == UserRole.ORG_ADMIN
