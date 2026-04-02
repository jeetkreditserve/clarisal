import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalWorkflow
from apps.employees.models import Employee, EmployeeStatus
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
class TestEmployeeWorkflowAssignments:
    def test_employee_detail_exposes_and_updates_workflow_assignments(self, org_admin_client):
        client, organisation = org_admin_client
        leave_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Leave Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        od_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='OD Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ON_DUTY,
            is_active=True,
        )
        regularization_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Regularization Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
            is_active=True,
        )
        employee_user = User.objects.create_user(
            email='employee@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP001',
        )

        response = client.get(f'/api/org/employees/{employee.id}/')
        assert response.status_code == 200
        assert response.data['leave_approval_workflow_id'] is None
        assert response.data['effective_approval_workflows']['leave']['workflow_id'] == str(leave_workflow.id)
        assert response.data['effective_approval_workflows']['leave']['source'] == 'DEFAULT'

        patch_response = client.patch(
            f'/api/org/employees/{employee.id}/',
            {
                'leave_approval_workflow_id': str(leave_workflow.id),
                'on_duty_approval_workflow_id': str(od_workflow.id),
                'attendance_regularization_approval_workflow_id': str(regularization_workflow.id),
            },
            format='json',
        )

        assert patch_response.status_code == 200
        assert patch_response.data['leave_approval_workflow_id'] == str(leave_workflow.id)
        assert patch_response.data['on_duty_approval_workflow_id'] == str(od_workflow.id)
        assert patch_response.data['attendance_regularization_approval_workflow_id'] == str(regularization_workflow.id)
        assert patch_response.data['effective_approval_workflows']['leave']['source'] == 'ASSIGNMENT'
