from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.assets.services import assign_asset_to_employee, create_asset_category, create_asset_item
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


@pytest.fixture
def asset_view_setup(db):
    organisation = Organisation.objects.create(
        name='Acme Assets',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    org_admin_user = User.objects.create_user(
        email='assets-admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=org_admin_user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    employee_user = User.objects.create_user(
        email='assets-employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP300',
        designation='Engineer',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 4, 1),
    )
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        created_by=org_admin_user,
    )
    mark_licence_batch_paid(batch, paid_by=org_admin_user, paid_at=date(2026, 4, 1))

    category = create_asset_category(
        organisation=organisation,
        name='Laptops',
        actor=org_admin_user,
    )
    asset = create_asset_item(
        organisation=organisation,
        name='MacBook Pro',
        asset_tag='LAP-300',
        category=category,
        actor=org_admin_user,
    )
    assignment = assign_asset_to_employee(
        asset=asset,
        employee=employee,
        actor=org_admin_user,
        notes='Return to IT on exit.',
    )

    org_admin_client = APIClient()
    org_admin_client.force_authenticate(user=org_admin_user)
    admin_session = org_admin_client.session
    admin_session['active_workspace_kind'] = 'ADMIN'
    admin_session['active_admin_org_id'] = str(organisation.id)
    admin_session.save()

    employee_client = APIClient()
    employee_client.force_authenticate(user=employee_user)
    employee_session = employee_client.session
    employee_session['active_workspace_kind'] = 'EMPLOYEE'
    employee_session['active_employee_org_id'] = str(organisation.id)
    employee_session.save()

    return {
        'assignment': assignment,
        'employee_client': employee_client,
    }


@pytest.mark.django_db
class TestAssetViews:
    def test_employee_can_list_and_acknowledge_own_assets_via_canonical_routes(self, asset_view_setup):
        employee_client = asset_view_setup['employee_client']
        assignment = asset_view_setup['assignment']

        list_response = employee_client.get('/api/v1/me/assets/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['asset_name'] == 'MacBook Pro'
        assert list_response.data[0]['acknowledged_at'] is None

        acknowledge_response = employee_client.post(f'/api/v1/me/assets/{assignment.id}/acknowledge/')

        assert acknowledge_response.status_code == 200
        assert acknowledge_response.data['id'] == str(assignment.id)
        assert acknowledge_response.data['acknowledged_at'] is not None

    def test_legacy_my_assets_alias_remains_available(self, asset_view_setup):
        employee_client = asset_view_setup['employee_client']

        response = employee_client.get('/api/v1/me/my/assets/')

        assert response.status_code == 200
        assert response.data[0]['asset_name'] == 'MacBook Pro'
