from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.timeoff.tests.test_services import (
    _create_employee,
    _create_leave_approval_workflow,
    _create_leave_type,
)


def _create_organisation(name='Timeoff View Org'):
    return Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def timeoff_view_setup(db):
    organisation = _create_organisation()
    org_admin_user = User.objects.create_user(
        email='timeoff-admin@test.com',
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
    employee = _create_employee(organisation, email='timeoff-employee@test.com')
    _create_leave_approval_workflow(organisation)

    org_admin_client = APIClient()
    org_admin_client.force_authenticate(user=org_admin_user)
    org_admin_session = org_admin_client.session
    org_admin_session['active_workspace_kind'] = 'ADMIN'
    org_admin_session['active_admin_org_id'] = str(organisation.id)
    org_admin_session.save()

    employee_client = APIClient()
    employee_client.force_authenticate(user=employee.user)
    employee_session = employee_client.session
    employee_session['active_workspace_kind'] = 'EMPLOYEE'
    employee_session['active_employee_org_id'] = str(organisation.id)
    employee_session.save()

    return {
        'organisation': organisation,
        'org_admin_client': org_admin_client,
        'org_admin_user': org_admin_user,
        'employee': employee,
        'employee_client': employee_client,
    }


@pytest.mark.django_db
class TestLeaveEncashmentViews:
    def test_employee_can_create_and_list_leave_encashments(self, timeoff_view_setup):
        from apps.timeoff.models import LeaveBalance

        employee = timeoff_view_setup['employee']
        employee_client = timeoff_view_setup['employee_client']
        leave_type = _create_leave_type(timeoff_view_setup['organisation'], code='EC')
        leave_type.allows_encashment = True
        leave_type.save(update_fields=['allows_encashment', 'modified_at'])
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            opening_balance=Decimal('0.00'),
            credited_amount=Decimal('10.00'),
            used_amount=Decimal('0.00'),
            pending_amount=Decimal('0.00'),
            carried_forward_amount=Decimal('0.00'),
        )

        create_response = employee_client.post(
            '/api/v1/me/leave-encashments/',
            {
                'leave_type_id': str(leave_type.id),
                'cycle_start': '2026-01-01',
                'cycle_end': '2026-12-31',
                'days_to_encash': '5.00',
            },
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['status'] == 'PENDING'

        list_response = employee_client.get('/api/v1/me/leave-encashments/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['days_to_encash'] == '5.00'

    def test_org_admin_can_list_leave_encashments(self, timeoff_view_setup):
        from apps.timeoff.models import LeaveBalance
        from apps.timeoff.services import create_leave_encashment_request

        employee = timeoff_view_setup['employee']
        org_admin_client = timeoff_view_setup['org_admin_client']
        leave_type = _create_leave_type(timeoff_view_setup['organisation'], code='OA')
        leave_type.allows_encashment = True
        leave_type.save(update_fields=['allows_encashment', 'modified_at'])
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            opening_balance=Decimal('0.00'),
            credited_amount=Decimal('10.00'),
            used_amount=Decimal('0.00'),
            pending_amount=Decimal('0.00'),
            carried_forward_amount=Decimal('0.00'),
        )
        create_leave_encashment_request(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            days_to_encash=Decimal('4.00'),
            actor=employee.user,
        )

        response = org_admin_client.get('/api/v1/org/leave-encashments/')

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['employee_id'] == str(employee.id)
