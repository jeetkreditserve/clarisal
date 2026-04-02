from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalWorkflow
from apps.employees.models import Employee, EmployeeOffboardingProcess, EmployeeStatus, OffboardingProcessStatus, OffboardingTaskStatus
from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationMembership, OrganisationMembershipStatus, OrganisationStatus
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


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
    batch = create_licence_batch(
        organisation,
        quantity=25,
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


@pytest.fixture
def employee_client(db):
    organisation = Organisation.objects.create(
        name='Employee Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = User.objects.create_user(
        email='employee-self@test.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    employee = Employee.objects.create(
        organisation=organisation,
        user=user,
        status=EmployeeStatus.ACTIVE,
        employee_code='EMPSELF',
    )
    batch = create_licence_batch(
        organisation,
        quantity=5,
        price_per_licence_per_month=100,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 12, 31),
        created_by=user,
    )
    mark_licence_batch_paid(batch, paid_by=user, paid_at=date(2026, 4, 1))
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'EMPLOYEE'
    session['active_employee_id'] = str(employee.id)
    session.save()
    return client, organisation, employee


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

    def test_end_employment_creates_offboarding_process(self, org_admin_client):
        client, organisation = org_admin_client
        employee_user = User.objects.create_user(
            email='active@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP100',
        )

        response = client.post(
            f'/api/org/employees/{employee.id}/end-employment/',
            {
                'status': EmployeeStatus.RESIGNED,
                'date_of_exit': '2026-04-30',
                'exit_reason': 'Personal reasons',
                'exit_notes': 'Collect laptop and disable access',
            },
            format='json',
        )

        assert response.status_code == 200
        assert response.data['status'] == EmployeeStatus.RESIGNED
        assert response.data['offboarding']['status'] == OffboardingProcessStatus.IN_PROGRESS
        assert response.data['offboarding']['exit_reason'] == 'Personal reasons'
        assert len(response.data['offboarding']['tasks']) >= 6

    def test_offboarding_tasks_can_be_updated_and_completed(self, org_admin_client):
        client, organisation = org_admin_client
        employee_user = User.objects.create_user(
            email='active-two@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP101',
        )
        process = EmployeeOffboardingProcess.objects.create(
            organisation=organisation,
            employee=employee,
            status=OffboardingProcessStatus.IN_PROGRESS,
            exit_status=EmployeeStatus.RESIGNED,
            date_of_exit=date(2026, 4, 30),
        )
        tasks = [
            process.tasks.create(code=f'TASK_{index}', title=f'Task {index}', owner='ORG_ADMIN', status=OffboardingTaskStatus.PENDING)
            for index in range(1, 3)
        ]

        task_response = client.patch(
            f'/api/org/employees/{employee.id}/offboarding/tasks/{tasks[0].id}/',
            {'status': OffboardingTaskStatus.COMPLETED},
            format='json',
        )
        assert task_response.status_code == 200
        assert task_response.data['completed_required_task_count'] == 1

        client.patch(
            f'/api/org/employees/{employee.id}/offboarding/tasks/{tasks[1].id}/',
            {'status': OffboardingTaskStatus.WAIVED},
            format='json',
        )
        complete_response = client.post(f'/api/org/employees/{employee.id}/offboarding/complete/')
        assert complete_response.status_code == 200
        assert complete_response.data['status'] == OffboardingProcessStatus.COMPLETED


@pytest.mark.django_db
class TestEmployeeOffboardingSelfService:
    def test_employee_can_view_own_offboarding_process(self, employee_client):
        client, organisation, employee = employee_client
        process = EmployeeOffboardingProcess.objects.create(
            organisation=organisation,
            employee=employee,
            status=OffboardingProcessStatus.IN_PROGRESS,
            exit_status=EmployeeStatus.RESIGNED,
            date_of_exit=date(2026, 4, 30),
            exit_reason='Resigned',
        )
        process.tasks.create(code='EXIT_COMMUNICATION', title='Exit communication', owner='EMPLOYEE')

        response = client.get('/api/me/offboarding/')

        assert response.status_code == 200
        assert response.data['id'] == str(process.id)
        assert response.data['tasks'][0]['code'] == 'EXIT_COMMUNICATION'
