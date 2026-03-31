import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@calrisal.com',
        password='TestPass@123',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )


@pytest.fixture
def workforce_user(db):
    ct = User.objects.create_superuser(
        email='seed-ct@calrisal.com',
        password='SeedPass@123',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )
    organisation = Organisation.objects.create(
        name='Northstar Labs',
        licence_count=10,
        created_by=ct,
        status='ACTIVE',
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='ops@northstar.com',
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
    return user, organisation


@pytest.mark.django_db
class TestLogin:
    def test_control_tower_login_returns_user_and_session(self, api_client, ct_user):
        response = api_client.post(
            '/api/auth/control-tower/login/',
            {
                'email': 'ct@calrisal.com',
                'password': 'TestPass@123',
            },
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'user' in data
        assert 'sessionid' in ''.join(response.cookies.keys()) or 'calrisal_sessionid' in ''.join(response.cookies.keys())
        assert data['user']['role'] == UserRole.CONTROL_TOWER
        assert data['user']['account_type'] == AccountType.CONTROL_TOWER
        assert data['user']['email'] == 'ct@calrisal.com'

    def test_workforce_login_returns_memberships_and_default_route(self, api_client, workforce_user):
        response = api_client.post(
            '/api/auth/login/',
            {
                'email': 'ops@northstar.com',
                'password': 'TestPass@123',
            },
            format='json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['user']['account_type'] == AccountType.WORKFORCE
        assert data['user']['role'] == UserRole.ORG_ADMIN
        assert data['user']['default_route'] == '/org/dashboard'
        assert len(data['user']['admin_organisations']) == 1
        assert data['user']['organisation_name'] == 'Northstar Labs'

    def test_workforce_login_rejects_control_tower_credentials(self, api_client, ct_user):
        response = api_client.post(
            '/api/auth/login/',
            {
                'email': 'ct@calrisal.com',
                'password': 'TestPass@123',
            },
            format='json',
        )
        assert response.status_code == 401

    def test_me_returns_current_user(self, api_client, ct_user):
        api_client.post(
            '/api/auth/control-tower/login/',
            {
                'email': 'ct@calrisal.com',
                'password': 'TestPass@123',
            },
            format='json',
        )
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 200
        assert response.json()['email'] == 'ct@calrisal.com'

    def test_logout_clears_session(self, api_client, ct_user):
        api_client.post(
            '/api/auth/control-tower/login/',
            {
                'email': 'ct@calrisal.com',
                'password': 'TestPass@123',
            },
            format='json',
        )
        response = api_client.post('/api/auth/logout/', {}, format='json')
        assert response.status_code == 204
        me_response = api_client.get('/api/auth/me/')
        assert me_response.status_code == 403

    def test_same_email_can_authenticate_separately_for_control_tower_and_workforce(self, db):
        control_tower = User.objects.create_superuser(
            email='shared@calrisal.com',
            password='ControlTower@123',
            role=UserRole.CONTROL_TOWER,
            is_active=True,
        )
        organisation = Organisation.objects.create(
            name='Shared Org',
            licence_count=5,
            created_by=control_tower,
            status='ACTIVE',
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        workforce = User.objects.create_user(
            email='shared@calrisal.com',
            password='Workforce@123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            user=workforce,
            organisation=organisation,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )

        ct_client = APIClient()
        ct_response = ct_client.post(
            '/api/auth/control-tower/login/',
            {'email': 'shared@calrisal.com', 'password': 'ControlTower@123'},
            format='json',
        )
        assert ct_response.status_code == 200
        assert ct_response.json()['user']['account_type'] == AccountType.CONTROL_TOWER

        workforce_client = APIClient()
        workforce_response = workforce_client.post(
            '/api/auth/login/',
            {'email': 'shared@calrisal.com', 'password': 'Workforce@123'},
            format='json',
        )
        assert workforce_response.status_code == 200
        assert workforce_response.json()['user']['account_type'] == AccountType.WORKFORCE
        assert workforce_response.json()['user']['organisation_name'] == 'Shared Org'

    def test_workforce_user_can_have_multiple_admin_and_employee_workspaces(self, api_client, db):
        control_tower = User.objects.create_superuser(
            email='seed-ct@calrisal.com',
            password='SeedPass@123',
            role=UserRole.CONTROL_TOWER,
            is_active=True,
        )
        admin_org = Organisation.objects.create(
            name='Northstar Labs',
            licence_count=10,
            created_by=control_tower,
            status='ACTIVE',
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        employee_org = Organisation.objects.create(
            name='Bluebird Works',
            licence_count=10,
            created_by=control_tower,
            status='ACTIVE',
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        user = User.objects.create_user(
            email='hybrid@northstar.com',
            password='HybridPass@123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            user=user,
            organisation=admin_org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        OrganisationMembership.objects.create(
            user=user,
            organisation=employee_org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        Employee.objects.create(
            user=user,
            organisation=admin_org,
            employee_code='EMP001',
            status=EmployeeStatus.ACTIVE,
        )
        Employee.objects.create(
            user=user,
            organisation=employee_org,
            employee_code='EMP002',
            status=EmployeeStatus.ACTIVE,
        )

        response = api_client.post(
            '/api/auth/login/',
            {'email': 'hybrid@northstar.com', 'password': 'HybridPass@123'},
            format='json',
        )

        assert response.status_code == 200
        data = response.json()['user']
        assert data['default_route'] == '/org/dashboard'
        assert len(data['admin_organisations']) == 2
        assert len(data['employee_workspaces']) == 2
        assert data['has_org_admin_access'] is True
        assert data['has_employee_access'] is True
