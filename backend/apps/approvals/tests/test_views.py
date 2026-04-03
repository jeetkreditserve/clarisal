from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalRequestKind
from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationMembership, OrganisationMembershipStatus, OrganisationStatus
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


@pytest.fixture
def org_admin_client(db):
    today = timezone.localdate()
    organisation = Organisation.objects.create(
        name='Acme Corp',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='admin@test.com',
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
    paid_batch = create_licence_batch(
        organisation=organisation,
        quantity=5,
        price_per_licence_per_month=Decimal('100.00'),
        start_date=today - timedelta(days=7),
        end_date=today + timedelta(days=30),
        created_by=user,
    )
    mark_licence_batch_paid(paid_batch, paid_by=user, paid_at=today - timedelta(days=1))
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()
    return client, organisation


@pytest.mark.django_db
class TestApprovalWorkflowApi:
    def test_create_accepts_attendance_regularization_defaults(self, org_admin_client):
        client, organisation = org_admin_client

        response = client.post(
            f'/api/org/approvals/workflows/',
            {
                'name': 'Attendance Regularization Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
                'is_active': True,
                'rules': [
                    {
                        'name': 'Default regularization rule',
                        'request_kind': ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
                        'priority': 100,
                        'is_active': True,
                    }
                ],
                'stages': [
                    {
                        'name': 'Manager review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'PRIMARY_ORG_ADMIN',
                        'approvers': [{'approver_type': 'REPORTING_MANAGER'}],
                    }
                ],
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.data['default_request_kind'] == ApprovalRequestKind.ATTENDANCE_REGULARIZATION

    def test_create_accepts_payroll_processing_defaults(self, org_admin_client):
        client, organisation = org_admin_client

        response = client.post(
            f'/api/org/approvals/workflows/',
            {
                'name': 'Payroll Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': ApprovalRequestKind.PAYROLL_PROCESSING,
                'is_active': True,
                'rules': [
                    {
                        'name': 'Default payroll rule',
                        'request_kind': ApprovalRequestKind.PAYROLL_PROCESSING,
                        'priority': 100,
                        'is_active': True,
                    }
                ],
                'stages': [
                    {
                        'name': 'Primary admin review',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'NONE',
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )

        assert response.status_code == 201
        assert response.data['default_request_kind'] == ApprovalRequestKind.PAYROLL_PROCESSING
