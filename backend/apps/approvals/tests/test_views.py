import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalRequestKind
from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationMembership, OrganisationMembershipStatus, OrganisationStatus


@pytest.fixture
def org_admin_client(db):
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
