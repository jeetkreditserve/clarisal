from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import User, UserRole
from apps.approvals.models import (
    ApprovalAction,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.approvals.services import approve_action, reject_action, resolve_workflow
from apps.departments.models import Department
from apps.employees.models import Employee, EmployeeStatus
from apps.locations.models import OfficeLocation
from apps.notifications.models import Notification, NotificationKind
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.timeoff.models import LeaveCycle, LeaveCycleType, LeavePlan, LeaveType


@pytest.fixture
def organisation(db):
    ct_user = User.objects.create_superuser(
        email='ct@test.com',
        password='pass123!',
        role=UserRole.CONTROL_TOWER,
    )
    org = Organisation.objects.create(
        name='Acme Corp',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    admin = User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    org.primary_admin_user = admin
    org.save(update_fields=['primary_admin_user', 'modified_at'])
    return org


@pytest.fixture
def reporting_manager(organisation):
    user = User.objects.create_user(
        email='manager@test.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        status=EmployeeStatus.ACTIVE,
        employee_code='MGR001',
    )


@pytest.fixture
def employee(organisation, reporting_manager):
    user = User.objects.create_user(
        email='employee@test.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        status=EmployeeStatus.ACTIVE,
        employee_code='EMP001',
        reporting_to=reporting_manager,
    )


@pytest.fixture
def department(organisation):
    return Department.objects.create(organisation=organisation, name='Engineering')


@pytest.fixture
def location(organisation):
    return OfficeLocation.objects.create(
        organisation=organisation,
        name='Bengaluru HQ',
        address='123 Main St',
        city='Bengaluru',
        state='Karnataka',
        country='India',
        pincode='560001',
        is_remote=False,
        is_active=True,
    )


@pytest.fixture
def leave_type(organisation):
    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Default Cycle',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
        is_active=True,
    )
    plan = LeavePlan.objects.create(
        organisation=organisation,
        leave_cycle=cycle,
        name='Default Plan',
        is_default=True,
        is_active=True,
    )
    return LeaveType.objects.create(
        leave_plan=plan,
        code='CL',
        name='Casual Leave',
        annual_entitlement='12.00',
        credit_frequency='YEARLY',
    )


@pytest.mark.django_db
class TestResolveWorkflow:
    def test_prefers_assignment_then_rule_then_request_type_default(
        self,
        organisation,
        employee,
        reporting_manager,
        department,
        location,
        leave_type,
    ):
        assigned_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Assigned Leave Workflow',
            is_active=True,
        )
        rule_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Department Leave Workflow',
            is_active=True,
        )
        default_leave_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default Leave Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        default_od_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default OD Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ON_DUTY,
            is_active=True,
        )
        default_regularization_workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default Regularization Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
            is_active=True,
        )

        ApprovalWorkflowRule.objects.create(
            workflow=rule_workflow,
            name='Engineering leave rule',
            request_kind=ApprovalRequestKind.LEAVE,
            department=department,
            office_location=location,
            priority=100,
            is_active=True,
        )

        employee.department = department
        employee.office_location = location
        employee.leave_approval_workflow = assigned_workflow
        employee.on_duty_approval_workflow = default_od_workflow
        employee.attendance_regularization_approval_workflow = default_regularization_workflow
        employee.save(
            update_fields=[
                'department',
                'office_location',
                'leave_approval_workflow',
                'on_duty_approval_workflow',
                'attendance_regularization_approval_workflow',
                'modified_at',
            ]
        )

        other_user = User.objects.create_user(
            email='other@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        other_employee = Employee.objects.create(
            organisation=organisation,
            user=other_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP002',
            department=department,
            office_location=location,
        )

        unresolved_user = User.objects.create_user(
            email='unresolved@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        unresolved_employee = Employee.objects.create(
            organisation=organisation,
            user=unresolved_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP003',
        )

        assert resolve_workflow(employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) == assigned_workflow
        assert resolve_workflow(other_employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) == rule_workflow
        assert resolve_workflow(unresolved_employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) == default_leave_workflow
        assert resolve_workflow(employee, ApprovalRequestKind.ON_DUTY) == default_od_workflow
        assert resolve_workflow(employee, ApprovalRequestKind.ATTENDANCE_REGULARIZATION) == default_regularization_workflow


def _create_pending_action(*, organisation, requester, approver_user, subject, request_kind, subject_label):
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name=f'{subject_label} Workflow',
        is_active=True,
    )
    stage = ApprovalStage.objects.create(
        workflow=workflow,
        name='Primary review',
        sequence=1,
    )
    return ApprovalAction.objects.create(
        approval_run=ApprovalRun.objects.create(
            organisation=organisation,
            workflow=workflow,
            request_kind=request_kind,
            requested_by=requester,
            requested_by_user=requester.user,
            status=ApprovalRunStatus.PENDING,
            current_stage_sequence=stage.sequence,
            subject_label=subject_label,
            content_type=ContentType.objects.get_for_model(subject.__class__),
            object_id=subject.id,
        ),
        stage=stage,
        approver_user=approver_user,
    )


@pytest.mark.django_db
class TestApprovalNotifications:
    @patch('django.db.transaction.on_commit')
    def test_approve_action_creates_leave_notification_and_queues_email(
        self,
        mock_on_commit,
        organisation,
        employee,
        department,
    ):
        mock_on_commit.side_effect = lambda callback: callback()
        approver_user = User.objects.create_user(
            email='leave-approver@test.com',
            password='pass123!',
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        action = _create_pending_action(
            organisation=organisation,
            requester=employee,
            approver_user=approver_user,
            subject=department,
            request_kind=ApprovalRequestKind.LEAVE,
            subject_label='Annual leave',
        )

        with patch('apps.approvals.services.get_org_operations_guard', return_value={'approval_actions_blocked': False, 'reason': ''}):
            with patch('apps.approvals.services._apply_subject_status'):
                with patch('apps.notifications.tasks.send_approval_outcome_email.delay') as mock_delay:
                    approve_action(action, approver_user)

        action.approval_run.refresh_from_db()
        notification = Notification.objects.get(recipient=employee.user)
        assert action.approval_run.status == ApprovalRunStatus.APPROVED
        assert notification.kind == NotificationKind.LEAVE_APPROVED
        assert notification.title == 'Your leave request has been approved'
        assert 'approved' in notification.body.lower()
        assert notification.object_id == str(department.id)
        mock_delay.assert_called_once()

    @patch('django.db.transaction.on_commit')
    def test_reject_action_creates_regularization_notification_and_queues_email(
        self,
        mock_on_commit,
        organisation,
        employee,
        location,
    ):
        mock_on_commit.side_effect = lambda callback: callback()
        approver_user = User.objects.create_user(
            email='regularization-approver@test.com',
            password='pass123!',
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        action = _create_pending_action(
            organisation=organisation,
            requester=employee,
            approver_user=approver_user,
            subject=location,
            request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
            subject_label='Attendance regularization',
        )

        with patch('apps.approvals.services.get_org_operations_guard', return_value={'approval_actions_blocked': False, 'reason': ''}):
            with patch('apps.approvals.services._apply_subject_status'):
                with patch('apps.notifications.tasks.send_approval_outcome_email.delay') as mock_delay:
                    reject_action(action, approver_user, comment='Missing supporting detail')

        action.approval_run.refresh_from_db()
        notification = Notification.objects.get(recipient=employee.user)
        assert action.approval_run.status == ApprovalRunStatus.REJECTED
        assert notification.kind == NotificationKind.ATTENDANCE_REGULARIZATION_REJECTED
        assert notification.title == 'Your attendance regularization request has been rejected'
        assert 'missing supporting detail' in notification.body.lower()
        mock_delay.assert_called_once()
