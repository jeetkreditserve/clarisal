from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
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
def org_admin_client(db):
    organisation = Organisation.objects.create(
        name='Probation Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='probation-admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month=100,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 12, 31),
        created_by=user,
    )
    mark_licence_batch_paid(batch, paid_by=user, paid_at=date(2026, 4, 1))
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()
    return client, organisation


@pytest.mark.django_db
class TestProbationEndDateField:
    def test_employee_has_probation_end_date_field(self, org_admin_client):
        _, organisation = org_admin_client
        user = User.objects.create_user(
            email='probation-field@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        probation_end_date = date.today() + timedelta(days=90)

        employee = Employee.objects.create(
            organisation=organisation,
            user=user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-PROB-001',
            probation_end_date=probation_end_date,
        )

        employee.refresh_from_db()
        assert employee.probation_end_date == probation_end_date

    def test_probation_end_date_nullable(self, org_admin_client):
        _, organisation = org_admin_client
        user = User.objects.create_user(
            email='probation-null@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )

        employee = Employee.objects.create(
            organisation=organisation,
            user=user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-PROB-002',
        )

        assert employee.probation_end_date is None


@pytest.mark.django_db
class TestEmployeeProbationCompleteView:
    def test_probation_complete_clears_probation_end_date(self, org_admin_client):
        client, organisation = org_admin_client
        user = User.objects.create_user(
            email='probation-employee@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-PROB-003',
            probation_end_date=date.today() - timedelta(days=1),
        )

        response = client.post(f'/api/org/employees/{employee.id}/probation-complete/')

        assert response.status_code == 200
        employee.refresh_from_db()
        assert employee.probation_end_date is None
        assert response.data['probation_end_date'] is None

    def test_probation_complete_returns_404_for_other_org(self, org_admin_client):
        client, _ = org_admin_client
        other_organisation = Organisation.objects.create(
            name='Other Probation Org',
            status=OrganisationStatus.ACTIVE,
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        other_user = User.objects.create_user(
            email='other-probation@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        other_employee = Employee.objects.create(
            organisation=other_organisation,
            user=other_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-PROB-004',
        )

        response = client.post(f'/api/org/employees/{other_employee.id}/probation-complete/')

        assert response.status_code == 404
