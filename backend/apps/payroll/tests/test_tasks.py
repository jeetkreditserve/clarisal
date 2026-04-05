from datetime import date
from unittest.mock import MagicMock, patch

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
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.payroll.services import create_payroll_run

from .test_service_setup import _attach_registered_and_billing_addresses


def _create_active_organisation(name='Async Payroll Org'):
    organisation = Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    _attach_registered_and_billing_addresses(organisation)
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    return organisation


@pytest.fixture
def async_payroll_setup(db):
    organisation = _create_active_organisation()
    org_admin_user = User.objects.create_user(
        email='async-payroll-admin@test.com',
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
    client = APIClient()
    client.force_authenticate(user=org_admin_user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()
    pay_run = create_payroll_run(
        organisation,
        period_year=2026,
        period_month=4,
        actor=org_admin_user,
        requester_user=org_admin_user,
    )
    return {
        'client': client,
        'organisation': organisation,
        'org_admin_user': org_admin_user,
        'pay_run': pay_run,
    }


@pytest.mark.django_db
class TestOrgPayrollRunCalculateViewAsync:
    @patch('apps.payroll.tasks.calculate_pay_run_task.delay')
    def test_calculate_returns_202_with_task_id(self, mock_delay, async_payroll_setup):
        mock_delay.return_value.id = 'celery-task-uuid-abc'

        response = async_payroll_setup['client'].post(
            f"/api/org/payroll/runs/{async_payroll_setup['pay_run'].id}/calculate/"
        )

        assert response.status_code == 202
        assert response.data['task_id'] == 'celery-task-uuid-abc'
        mock_delay.assert_called_once_with(
            str(async_payroll_setup['pay_run'].id),
            str(async_payroll_setup['org_admin_user'].id),
        )

    @patch('apps.payroll.views.AsyncResult')
    def test_calculation_status_polling_returns_pending(self, mock_async_result, async_payroll_setup):
        mock_result = MagicMock()
        mock_result.state = 'PENDING'
        mock_result.successful.return_value = False
        mock_result.failed.return_value = False
        mock_async_result.return_value = mock_result

        response = async_payroll_setup['client'].get(
            f"/api/org/payroll/runs/{async_payroll_setup['pay_run'].id}/calculation-status/?task_id=celery-task-uuid-abc"
        )

        assert response.status_code == 200
        assert response.data['state'] == 'PENDING'
        assert response.data['task_id'] == 'celery-task-uuid-abc'
