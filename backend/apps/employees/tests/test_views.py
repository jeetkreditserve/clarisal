from datetime import date, datetime, time

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
)
from apps.approvals.services import create_approval_run
from apps.attendance.models import (
    AttendanceDay,
    AttendanceDayStatus,
    AttendancePunch,
    AttendancePunchActionType,
    AttendancePunchSource,
)
from apps.departments.models import Department
from apps.employees.models import (
    CustomFieldDefinition,
    CustomFieldPlacement,
    CustomFieldType,
    Employee,
    EmployeeOffboardingProcess,
    EmployeeStatus,
    ExitInterview,
    OffboardingProcessStatus,
    OffboardingTaskStatus,
)
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid
from apps.timeoff.models import LeaveBalance, LeaveCycle, LeavePlan, LeaveRequest, LeaveRequestStatus, LeaveType


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
    def test_custom_field_definitions_and_values_can_be_managed(self, org_admin_client):
        client, organisation = org_admin_client
        employee_user = User.objects.create_user(
            email='custom-fields@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-CF',
        )
        field_definition = CustomFieldDefinition.objects.create(
            organisation=organisation,
            name='Shirt size',
            field_key='shirt_size',
            field_type=CustomFieldType.TEXT,
            placement=CustomFieldPlacement.CUSTOM,
            is_required=False,
            display_order=1,
            dropdown_options=[],
        )

        definition_response = client.get('/api/v1/org/custom-fields/?placement=CUSTOM')
        assert definition_response.status_code == 200
        assert definition_response.data[0]['id'] == str(field_definition.id)

        update_response = client.put(
            f'/api/v1/org/employees/{employee.id}/custom-fields/',
            {
                'custom_fields': [
                    {
                        'field_definition_id': str(field_definition.id),
                        'value_text': 'L',
                    },
                ],
            },
            format='json',
        )

        assert update_response.status_code == 200
        assert str(update_response.data[0]['field_definition']) == str(field_definition.id)
        assert update_response.data[0]['display_value'] == 'L'

        value_response = client.get(f'/api/v1/org/employees/{employee.id}/custom-fields/')
        assert value_response.status_code == 200
        assert value_response.data[0]['field_name'] == 'Shirt size'
        assert value_response.data[0]['value_text'] == 'L'

    def test_custom_field_definition_rejects_invalid_field_key(self, org_admin_client):
        client, _organisation = org_admin_client

        response = client.post(
            '/api/v1/org/custom-fields/',
            {
                'name': 'Shirt size',
                'field_key': 'Shirt Size',
                'field_type': 'TEXT',
                'placement': 'CUSTOM',
                'is_required': False,
                'display_order': 1,
                'dropdown_options': [],
                'placeholder': '',
                'help_text': '',
                'is_active': True,
            },
            format='json',
        )

        assert response.status_code == 400
        assert 'field_key' in response.data

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
        expense_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Expense Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.EXPENSE_CLAIM,
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

        response = client.get(f'/api/v1/org/employees/{employee.id}/')
        assert response.status_code == 200
        assert response.data['leave_approval_workflow_id'] is None
        assert response.data['effective_approval_workflows']['leave']['workflow_id'] == str(leave_workflow.id)
        assert response.data['effective_approval_workflows']['leave']['source'] == 'DEFAULT'
        assert response.data['effective_approval_workflows']['expense_claim']['workflow_id'] == str(expense_workflow.id)
        assert response.data['effective_approval_workflows']['expense_claim']['source'] == 'DEFAULT'

        patch_response = client.patch(
            f'/api/v1/org/employees/{employee.id}/',
            {
                'leave_approval_workflow_id': str(leave_workflow.id),
                'on_duty_approval_workflow_id': str(od_workflow.id),
                'attendance_regularization_approval_workflow_id': str(regularization_workflow.id),
                'expense_approval_workflow_id': str(expense_workflow.id),
            },
            format='json',
        )

        assert patch_response.status_code == 200
        assert patch_response.data['leave_approval_workflow_id'] == str(leave_workflow.id)
        assert patch_response.data['on_duty_approval_workflow_id'] == str(od_workflow.id)
        assert patch_response.data['attendance_regularization_approval_workflow_id'] == str(regularization_workflow.id)
        assert patch_response.data['expense_approval_workflow_id'] == str(expense_workflow.id)
        assert patch_response.data['effective_approval_workflows']['leave']['source'] == 'ASSIGNMENT'
        assert patch_response.data['effective_approval_workflows']['expense_claim']['source'] == 'ASSIGNMENT'

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
            f'/api/v1/org/employees/{employee.id}/end-employment/',
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
        assert response.data['offboarding']['fnf_settlement_id'] is not None
        assert response.data['offboarding']['fnf_status'] == 'DRAFT'
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
            f'/api/v1/org/employees/{employee.id}/offboarding/tasks/{tasks[0].id}/',
            {'status': OffboardingTaskStatus.COMPLETED},
            format='json',
        )
        assert task_response.status_code == 200
        assert task_response.data['completed_required_task_count'] == 1

        client.patch(
            f'/api/v1/org/employees/{employee.id}/offboarding/tasks/{tasks[1].id}/',
            {'status': OffboardingTaskStatus.WAIVED},
            format='json',
        )
        complete_response = client.post(f'/api/v1/org/employees/{employee.id}/offboarding/complete/')
        assert complete_response.status_code == 200
        assert complete_response.data['status'] == OffboardingProcessStatus.COMPLETED

    def test_employee_exit_interview_endpoint_upserts_flat_summary(self, org_admin_client):
        client, organisation = org_admin_client
        interviewer_user = User.objects.create_user(
            email='interviewer@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Asha',
            last_name='Rao',
        )
        interviewer = Employee.objects.create(
            organisation=organisation,
            user=interviewer_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-INT',
        )
        employee_user = User.objects.create_user(
            email='exit@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Priya',
            last_name='Sharma',
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status=EmployeeStatus.RESIGNED,
            employee_code='EMP-EXIT',
        )
        EmployeeOffboardingProcess.objects.create(
            organisation=organisation,
            employee=employee,
            status=OffboardingProcessStatus.IN_PROGRESS,
            exit_status=EmployeeStatus.RESIGNED,
            date_of_exit=date(2026, 4, 30),
            exit_reason='Personal',
        )

        response = client.patch(
            f'/api/v1/org/employees/{employee.id}/exit-interview/',
            {
                'interview_date': '2026-04-29',
                'exit_reason': 'Career growth',
                'interviewer_id': str(interviewer.id),
                'overall_satisfaction': 4,
                'would_recommend_org': True,
                'feedback': 'Supportive team.',
                'areas_of_improvement': 'Faster promotion cycles.',
            },
            format='json',
        )

        assert response.status_code == 200
        assert response.data['interview_date'] == '2026-04-29'
        assert response.data['exit_reason'] == 'Career growth'
        assert response.data['interviewer_id'] == str(interviewer.id)
        assert response.data['interviewer_name'] == 'Asha Rao'
        assert response.data['overall_satisfaction'] == 4
        assert response.data['would_recommend_org'] is True
        assert response.data['feedback'] == 'Supportive team.'
        assert response.data['areas_of_improvement'] == 'Faster promotion cycles.'

        interview = ExitInterview.objects.get(process__employee=employee)
        detail_response = client.get(f'/api/v1/org/employees/{employee.id}/exit-interview/')

        assert detail_response.status_code == 200
        assert detail_response.data['id'] == str(interview.id)
        assert detail_response.data['feedback'] == 'Supportive team.'


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

        response = client.get('/api/v1/me/offboarding/')

        assert response.status_code == 200
        assert response.data['id'] == str(process.id)
        assert response.data['tasks'][0]['code'] == 'EXIT_COMMUNICATION'


@pytest.mark.django_db
class TestManagerSelfServiceViews:
    def _build_team_setup(self, employee_client):
        client, organisation, manager = employee_client
        manager.user.first_name = 'Maya'
        manager.user.last_name = 'Patel'
        manager.user.save(update_fields=['first_name', 'last_name', 'modified_at'])

        engineering = Department.objects.create(organisation=organisation, name='Engineering')

        report_one_user = User.objects.create_user(
            email='report-one@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Rohan',
            last_name='Mehta',
        )
        report_one = Employee.objects.create(
            organisation=organisation,
            user=report_one_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-101',
            department=engineering,
            reporting_to=manager,
        )
        report_two_user = User.objects.create_user(
            email='report-two@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Ananya',
            last_name='Gupta',
        )
        report_two = Employee.objects.create(
            organisation=organisation,
            user=report_two_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-102',
            department=engineering,
            reporting_to=manager,
        )
        outsider_user = User.objects.create_user(
            email='outside@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Ira',
            last_name='Sen',
        )
        outsider = Employee.objects.create(
            organisation=organisation,
            user=outsider_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP-103',
            department=engineering,
        )

        leave_cycle = LeaveCycle.objects.create(
            organisation=organisation,
            name='CY 2026',
            is_default=True,
            is_active=True,
            created_by=manager.user,
        )
        leave_plan = LeavePlan.objects.create(
            organisation=organisation,
            leave_cycle=leave_cycle,
            name='Default Leave Plan',
            is_default=True,
            is_active=True,
            created_by=manager.user,
        )
        annual_leave = LeaveType.objects.create(
            leave_plan=leave_plan,
            code='AL',
            name='Annual Leave',
            annual_entitlement='12.00',
            is_active=True,
        )

        cycle_start = date(date.today().year, 1, 1)
        cycle_end = date(date.today().year, 12, 31)
        LeaveBalance.objects.create(
            employee=report_one,
            leave_type=annual_leave,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            opening_balance='0.00',
            credited_amount='8.00',
            used_amount='1.00',
            pending_amount='0.00',
            carried_forward_amount='0.00',
        )
        LeaveBalance.objects.create(
            employee=report_two,
            leave_type=annual_leave,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            opening_balance='0.00',
            credited_amount='10.00',
            used_amount='2.00',
            pending_amount='0.00',
            carried_forward_amount='0.00',
        )

        target_date = date.today()
        LeaveRequest.objects.create(
            employee=report_one,
            leave_type=annual_leave,
            start_date=target_date,
            end_date=target_date,
            total_units='1.00',
            reason='Medical appointment',
            status=LeaveRequestStatus.PENDING,
        )
        LeaveRequest.objects.create(
            employee=report_one,
            leave_type=annual_leave,
            start_date=target_date,
            end_date=target_date,
            total_units='1.00',
            reason='Approved leave for attendance status',
            status=LeaveRequestStatus.APPROVED,
        )
        LeaveRequest.objects.create(
            employee=outsider,
            leave_type=annual_leave,
            start_date=target_date,
            end_date=target_date,
            total_units='1.00',
            reason='Outside team leave',
            status=LeaveRequestStatus.PENDING,
        )

        AttendanceDay.objects.create(
            organisation=organisation,
            employee=report_one,
            attendance_date=target_date,
            status=AttendanceDayStatus.INCOMPLETE,
            needs_regularization=True,
            raw_punch_count=1,
        )

        return {
            'client': client,
            'organisation': organisation,
            'manager': manager,
            'report_one': report_one,
            'report_two': report_two,
            'outsider': outsider,
            'department': engineering,
            'annual_leave': annual_leave,
            'target_date': target_date,
        }

    def test_manager_can_list_direct_reports_with_team_metrics(self, employee_client):
        setup = self._build_team_setup(employee_client)

        response = setup['client'].get('/api/v1/me/my-team/')

        assert response.status_code == 200
        summary_by_code = {item['employee_code']: item for item in response.data}
        assert set(summary_by_code) == {'EMP-101', 'EMP-102'}
        first_member = summary_by_code['EMP-101']
        assert first_member['name'] == 'Rohan Mehta'
        assert first_member['pending_leave_requests'] == 1
        assert first_member['attendance_deviations_this_month'] == 1
        assert first_member['leave_balance_summary'][0]['leave_type_name'] == 'Annual Leave'
        assert first_member['leave_balance_summary'][0]['available'] > 0

    def test_non_manager_receives_empty_my_team_payload(self, employee_client):
        client, _organisation, _employee = employee_client

        response = client.get('/api/v1/me/my-team/')

        assert response.status_code == 200
        assert response.data == []

    def test_manager_team_leave_endpoint_only_returns_direct_reports(self, employee_client):
        setup = self._build_team_setup(employee_client)

        response = setup['client'].get(
            '/api/v1/me/my-team/leave/',
            {
                'status': LeaveRequestStatus.PENDING,
                'from_date': setup['target_date'].isoformat(),
                'to_date': setup['target_date'].isoformat(),
            },
        )

        assert response.status_code == 200
        assert [item['employee_name'] for item in response.data] == ['Rohan Mehta']
        assert response.data[0]['leave_type_name'] == 'Annual Leave'

    def test_manager_team_attendance_endpoint_only_returns_direct_reports(self, employee_client):
        setup = self._build_team_setup(employee_client)
        target_dt = timezone.make_aware(datetime.combine(setup['target_date'], time(9, 0)))
        AttendancePunch.objects.create(
            organisation=setup['organisation'],
            employee=setup['report_two'],
            action_type=AttendancePunchActionType.CHECK_IN,
            source=AttendancePunchSource.WEB,
            punch_at=target_dt,
        )
        AttendancePunch.objects.create(
            organisation=setup['organisation'],
            employee=setup['report_two'],
            action_type=AttendancePunchActionType.CHECK_OUT,
            source=AttendancePunchSource.WEB,
            punch_at=timezone.make_aware(datetime.combine(setup['target_date'], time(18, 0))),
        )
        AttendancePunch.objects.create(
            organisation=setup['organisation'],
            employee=setup['outsider'],
            action_type=AttendancePunchActionType.CHECK_IN,
            source=AttendancePunchSource.WEB,
            punch_at=target_dt,
        )

        response = setup['client'].get(
            '/api/v1/me/my-team/attendance/',
            {'date': setup['target_date'].isoformat()},
        )

        assert response.status_code == 200
        assert {item['employee_name'] for item in response.data} == {'Rohan Mehta', 'Ananya Gupta'}
        status_by_employee = {item['employee_name']: item['status'] for item in response.data}
        assert status_by_employee['Rohan Mehta'] == AttendanceDayStatus.ON_LEAVE
        assert status_by_employee['Ananya Gupta'] == AttendanceDayStatus.PRESENT

    def test_manager_approval_inbox_scope_only_returns_direct_reports(self, employee_client):
        setup = self._build_team_setup(employee_client)
        workflow = ApprovalWorkflow.objects.create(
            organisation=setup['organisation'],
            name='Manager Scope Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(workflow=workflow, name='Manager review', sequence=1)
        ApprovalStageApprover.objects.create(
            stage=stage,
            approver_type=ApprovalApproverType.SPECIFIC_EMPLOYEE,
            approver_employee=setup['manager'],
        )

        create_approval_run(
            setup['department'],
            ApprovalRequestKind.LEAVE,
            requester=setup['report_one'],
            actor=setup['report_one'].user,
            subject_label='Rohan leave request',
        )
        create_approval_run(
            setup['department'],
            ApprovalRequestKind.LEAVE,
            requester=setup['outsider'],
            actor=setup['outsider'].user,
            subject_label='Ira leave request',
        )

        response = setup['client'].get('/api/v1/me/approvals/inbox/', {'scope': 'my_team'})

        assert response.status_code == 200
        assert [item['subject_label'] for item in response.data] == ['Rohan leave request']
