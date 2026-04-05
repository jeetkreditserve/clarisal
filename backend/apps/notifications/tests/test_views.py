from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.notifications.models import NotificationKind
from apps.notifications.services import create_notification
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


@pytest.fixture
def notification_clients(db):
    organisation = Organisation.objects.create(
        name='Notify API Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    org_admin_user = User.objects.create_user(
        email='notify-admin@test.com',
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
        email='notify-employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP200',
        designation='Analyst',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2026, 4, 1),
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
        'organisation': organisation,
        'org_admin_user': org_admin_user,
        'employee_user': employee_user,
        'org_admin_client': org_admin_client,
        'employee_client': employee_client,
    }


@pytest.mark.django_db
def test_org_admin_can_list_own_notifications(notification_clients):
    org_admin_user = notification_clients['org_admin_user']
    client = notification_clients['org_admin_client']

    create_notification(recipient=org_admin_user, kind=NotificationKind.GENERAL, title='Draft ready')
    create_notification(recipient=org_admin_user, kind=NotificationKind.GENERAL, title='Payroll submitted')

    response = client.get('/api/me/notifications/')

    assert response.status_code == 200
    assert response.data['unread_count'] == 2
    assert len(response.data['results']) == 2


@pytest.mark.django_db
def test_employee_can_mark_notification_read(notification_clients):
    employee_user = notification_clients['employee_user']
    client = notification_clients['employee_client']
    notification = create_notification(recipient=employee_user, kind=NotificationKind.GENERAL, title='Payslip ready')

    response = client.patch(f'/api/me/notifications/{notification.id}/read/')

    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.is_read is True


@pytest.mark.django_db
def test_employee_can_mark_all_notifications_read(notification_clients):
    employee_user = notification_clients['employee_user']
    client = notification_clients['employee_client']

    create_notification(recipient=employee_user, kind=NotificationKind.GENERAL, title='One')
    create_notification(recipient=employee_user, kind=NotificationKind.GENERAL, title='Two')

    response = client.post('/api/me/notifications/mark-all-read/')

    assert response.status_code == 200
    assert response.data['marked_read'] == 2
