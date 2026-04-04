from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.approvals.models import (
    ApprovalAction,
    ApprovalActionAssignmentSource,
    ApprovalActionStatus,
    ApprovalApproverType,
    ApprovalFallbackType,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalStageEscalationPolicy,
    ApprovalStageMode,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.approvals.services import (
    _approval_outcome_kind,
    _get_stage_sla_policy,
    _matches_rule,
    _requester_user_for_context,
    _resolve_escalation_target,
    approve_action,
    cancel_approval_run,
    create_approval_run,
    ensure_default_workflow_configured,
    get_active_approval_delegation,
    get_employee_assigned_workflow,
    get_pending_approval_actions_for_user,
    process_pending_action_escalations,
    reject_action,
    resolve_workflow,
    send_pending_action_reminders,
    upsert_approval_delegation,
)
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
def delegate_employee(organisation):
    user = User.objects.create_user(
        email='delegate@test.com',
        password='pass123!',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        status=EmployeeStatus.ACTIVE,
        employee_code='EMPD01',
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

    def test_ensure_default_workflow_configured_requires_all_defaults(self, organisation):
        ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default Leave Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default OD Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ON_DUTY,
            is_active=True,
        )

        with pytest.raises(ValueError, match='Create and activate a default approval workflow'):
            ensure_default_workflow_configured(organisation)

        ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Default Attendance Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.ATTENDANCE_REGULARIZATION,
            is_active=True,
        )

        ensure_default_workflow_configured(organisation)

    def test_matches_rule_and_assigned_workflow_helpers_cover_mismatch_paths(
        self,
        organisation,
        employee,
        department,
        location,
        leave_type,
    ):
        rule = ApprovalWorkflowRule(
            workflow=ApprovalWorkflow(organisation=organisation, name='Rule Workflow'),
            name='Rule',
            request_kind=ApprovalRequestKind.LEAVE,
            department=department,
            office_location=location,
            specific_employee=employee,
            employment_type='FULL_TIME',
            designation='Engineer',
            leave_type=leave_type,
            is_active=True,
        )
        employee.department = department
        employee.office_location = location
        employee.employment_type = 'FULL_TIME'
        employee.designation = 'Engineer'

        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is True

        rule.is_active = False
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        rule.is_active = True
        rule.request_kind = ApprovalRequestKind.ON_DUTY
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        rule.request_kind = ApprovalRequestKind.LEAVE

        employee.department = None
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        employee.department = department
        employee.office_location = None
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        employee.office_location = location

        other_user = User.objects.create_user(
            email='other-rule@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        other_employee = Employee.objects.create(
            organisation=organisation,
            user=other_user,
            employee_code='EMP-RULE-2',
            status=EmployeeStatus.ACTIVE,
        )
        rule.specific_employee = other_employee
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        rule.specific_employee = employee

        employee.employment_type = 'PART_TIME'
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        employee.employment_type = 'FULL_TIME'
        employee.designation = 'Analyst'
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=leave_type) is False
        employee.designation = 'Engineer'
        assert _matches_rule(rule, employee, ApprovalRequestKind.LEAVE, leave_type=None) is False

        other_org = Organisation.objects.create(
            name='Other Org',
            status=OrganisationStatus.ACTIVE,
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        cross_org_workflow = ApprovalWorkflow.objects.create(organisation=other_org, name='Cross org workflow', is_active=True)
        inactive_workflow = ApprovalWorkflow.objects.create(organisation=organisation, name='Inactive workflow', is_active=False)
        active_workflow = ApprovalWorkflow.objects.create(organisation=organisation, name='Active workflow', is_active=True)

        employee.leave_approval_workflow = cross_org_workflow
        assert get_employee_assigned_workflow(employee, ApprovalRequestKind.LEAVE) is None
        employee.leave_approval_workflow = inactive_workflow
        assert get_employee_assigned_workflow(employee, ApprovalRequestKind.LEAVE) is None
        employee.leave_approval_workflow = active_workflow
        assert get_employee_assigned_workflow(employee, ApprovalRequestKind.LEAVE) == active_workflow


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


@pytest.mark.django_db
class TestApprovalDelegationAndEscalation:
    def test_create_approval_run_assigns_action_to_delegate(self, organisation, employee, reporting_manager, delegate_employee, department):
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Delegated Leave Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(workflow=workflow, name='Manager review', sequence=1)
        ApprovalStageApprover.objects.create(stage=stage, approver_type='REPORTING_MANAGER')

        upsert_approval_delegation(
            organisation,
            delegator_employee=reporting_manager,
            delegate_employee=delegate_employee,
            request_kinds=[ApprovalRequestKind.LEAVE],
            start_date=timezone.localdate(),
            actor=organisation.primary_admin_user,
        )

        approval_run = create_approval_run(
            department,
            ApprovalRequestKind.LEAVE,
            requester=employee,
            actor=employee.user,
            subject_label='Delegated leave',
        )

        action = approval_run.actions.get()
        assert action.approver_user == delegate_employee.user
        assert action.approver_employee == delegate_employee
        assert action.assignment_source == ApprovalActionAssignmentSource.DELEGATED
        assert action.original_approver_user == reporting_manager.user
        assert action.original_approver_employee == reporting_manager

    def test_upsert_approval_delegation_rejects_loops(self, organisation, employee, reporting_manager, delegate_employee):
        upsert_approval_delegation(
            organisation,
            delegator_employee=reporting_manager,
            delegate_employee=delegate_employee,
            request_kinds=[ApprovalRequestKind.LEAVE],
            start_date=timezone.localdate(),
            actor=organisation.primary_admin_user,
        )

        with pytest.raises(ValueError, match='delegation loop'):
            upsert_approval_delegation(
                organisation,
                delegator_employee=delegate_employee,
                delegate_employee=reporting_manager,
                request_kinds=[ApprovalRequestKind.LEAVE],
                start_date=timezone.localdate(),
                actor=organisation.primary_admin_user,
            )

        with pytest.raises(ValueError, match='cannot delegate approval authority to themselves'):
            upsert_approval_delegation(
                organisation,
                delegator_employee=employee,
                delegate_employee=employee,
                request_kinds=[ApprovalRequestKind.LEAVE],
                start_date=timezone.localdate(),
                actor=organisation.primary_admin_user,
            )

    @patch('django.db.transaction.on_commit')
    def test_reminders_and_escalations_follow_stage_sla(self, mock_on_commit, organisation, employee, reporting_manager, delegate_employee, department):
        mock_on_commit.side_effect = lambda callback: callback()
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Escalation Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(workflow=workflow, name='Manager review', sequence=1)
        ApprovalStageApprover.objects.create(stage=stage, approver_type='REPORTING_MANAGER')
        ApprovalStageEscalationPolicy.objects.create(
            stage=stage,
            reminder_after_hours=1,
            escalate_after_hours=2,
            escalation_target_type='SPECIFIC_EMPLOYEE',
            escalation_employee=delegate_employee,
        )

        approval_run = create_approval_run(
            department,
            ApprovalRequestKind.LEAVE,
            requester=employee,
            actor=employee.user,
            subject_label='Escalated leave',
        )
        action = approval_run.actions.get()
        action.created_at = timezone.now() - timedelta(hours=3)
        action.save(update_fields=['created_at'])

        assert send_pending_action_reminders(now=timezone.now()) == 1

        action.refresh_from_db()
        assert action.reminder_sent_at is not None

        escalated = process_pending_action_escalations(now=timezone.now())
        assert escalated == 1

        action.refresh_from_db()
        approval_run.refresh_from_db()
        new_action = approval_run.actions.exclude(id=action.id).get()
        assert action.status == 'CANCELLED'
        assert action.escalated_at is not None
        assert new_action.approver_user == delegate_employee.user
        assert new_action.assignment_source == ApprovalActionAssignmentSource.ESCALATED
        assert new_action.escalated_from_action == action

    def test_delegation_helpers_validate_dates_organisation_scope_and_request_kind(
        self,
        organisation,
        employee,
        reporting_manager,
        delegate_employee,
    ):
        other_org = Organisation.objects.create(
            name='Other Org',
            status=OrganisationStatus.ACTIVE,
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        outsider_user = User.objects.create_user(
            email='outsider@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        outsider = Employee.objects.create(
            organisation=other_org,
            user=outsider_user,
            employee_code='OUT001',
            status=EmployeeStatus.ACTIVE,
        )

        with pytest.raises(ValueError, match='must belong to the active organisation'):
            upsert_approval_delegation(
                organisation,
                delegator_employee=reporting_manager,
                delegate_employee=outsider,
                request_kinds=[ApprovalRequestKind.LEAVE],
                start_date=timezone.localdate(),
                actor=organisation.primary_admin_user,
            )

        with pytest.raises(ValueError, match='end date must be on or after the start date'):
            upsert_approval_delegation(
                organisation,
                delegator_employee=reporting_manager,
                delegate_employee=delegate_employee,
                request_kinds=[ApprovalRequestKind.LEAVE],
                start_date=timezone.localdate(),
                end_date=timezone.localdate() - timedelta(days=1),
                actor=organisation.primary_admin_user,
            )

        delegation = upsert_approval_delegation(
            organisation,
            delegator_employee=reporting_manager,
            delegate_employee=delegate_employee,
            request_kinds=[ApprovalRequestKind.LEAVE],
            start_date=timezone.localdate() - timedelta(days=1),
            actor=organisation.primary_admin_user,
        )
        updated = upsert_approval_delegation(
            organisation,
            delegator_employee=reporting_manager,
            delegate_employee=delegate_employee,
            request_kinds=[ApprovalRequestKind.ON_DUTY],
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=7),
            is_active=False,
            actor=organisation.primary_admin_user,
            delegation=delegation,
        )

        assert updated.request_kinds == [ApprovalRequestKind.ON_DUTY]
        assert updated.is_active is False
        assert get_active_approval_delegation(reporting_manager, ApprovalRequestKind.LEAVE) is None
        assert get_active_approval_delegation(reporting_manager, ApprovalRequestKind.ON_DUTY) is None

        delegation.is_active = True
        delegation.request_kinds = [ApprovalRequestKind.LEAVE]
        delegation.start_date = timezone.localdate() - timedelta(days=1)
        delegation.end_date = timezone.localdate() + timedelta(days=1)
        delegation.save(update_fields=['is_active', 'request_kinds', 'start_date', 'end_date', 'modified_at'])
        assert get_active_approval_delegation(reporting_manager, ApprovalRequestKind.LEAVE) == delegation
        assert _requester_user_for_context(employee) == employee.user
        assert _requester_user_for_context(None) is None

    @patch('django.db.transaction.on_commit')
    def test_approval_action_helpers_cover_validation_any_mode_and_cancellation(
        self,
        mock_on_commit,
        organisation,
        employee,
        reporting_manager,
        department,
    ):
        mock_on_commit.side_effect = lambda callback: callback()
        fallback_user = User.objects.create_user(
            email='fallback@test.com',
            password='pass123!',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        fallback_employee = Employee.objects.create(
            organisation=organisation,
            user=fallback_user,
            employee_code='FALL001',
            status=EmployeeStatus.ACTIVE,
        )
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Any Stage Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        first_stage = ApprovalStage.objects.create(
            workflow=workflow,
            name='First stage',
            sequence=1,
            mode=ApprovalStageMode.ANY,
            fallback_type=ApprovalFallbackType.SPECIFIC_EMPLOYEE,
            fallback_employee=fallback_employee,
        )
        second_stage = ApprovalStage.objects.create(
            workflow=workflow,
            name='Second stage',
            sequence=2,
            mode=ApprovalStageMode.ALL,
        )
        ApprovalStageApprover.objects.create(stage=first_stage, approver_type=ApprovalApproverType.REPORTING_MANAGER)
        ApprovalStageApprover.objects.create(stage=first_stage, approver_type=ApprovalApproverType.PRIMARY_ORG_ADMIN)
        ApprovalStageApprover.objects.create(stage=second_stage, approver_type=ApprovalApproverType.PRIMARY_ORG_ADMIN)

        approval_run = create_approval_run(
            department,
            ApprovalRequestKind.LEAVE,
            requester=employee,
            actor=employee.user,
            subject_label='Any mode leave',
        )
        first_stage_actions = list(approval_run.actions.filter(stage=first_stage).order_by('created_at'))
        manager_action = next(action for action in first_stage_actions if action.approver_user_id == reporting_manager.user_id)
        sibling_action = next(action for action in first_stage_actions if action.id != manager_action.id)

        with pytest.raises(ValueError, match='not allowed to act'):
            approve_action(manager_action, employee.user)

        with patch('apps.approvals.services.get_org_operations_guard', return_value={'approval_actions_blocked': True, 'reason': 'Blocked'}):
            with pytest.raises(ValueError, match='Blocked'):
                approve_action(manager_action, reporting_manager.user)

        with patch('apps.approvals.services.get_org_operations_guard', return_value={'approval_actions_blocked': False, 'reason': ''}):
            with patch('apps.notifications.tasks.send_approval_outcome_email.delay'):
                approve_action(manager_action, reporting_manager.user)

        approval_run.refresh_from_db()
        manager_action.refresh_from_db()
        sibling_action.refresh_from_db()
        next_stage_action = approval_run.actions.get(stage=second_stage)

        assert manager_action.status == ApprovalActionStatus.APPROVED
        assert sibling_action.status == ApprovalActionStatus.SKIPPED
        assert approval_run.current_stage_sequence == 2
        assert next_stage_action.approver_user == organisation.primary_admin_user

        with patch('apps.approvals.services._apply_subject_status') as mock_apply_subject_status:
            cancel_approval_run(approval_run, actor=organisation.primary_admin_user, subject_status=None)
        approval_run.refresh_from_db()
        next_stage_action.refresh_from_db()
        assert approval_run.status == ApprovalRunStatus.CANCELLED
        assert next_stage_action.status == ApprovalActionStatus.CANCELLED
        mock_apply_subject_status.assert_not_called()
        assert cancel_approval_run(approval_run, actor=organisation.primary_admin_user) == approval_run

    @patch('django.db.transaction.on_commit')
    def test_reject_action_and_escalation_helpers_cover_remaining_branches(
        self,
        mock_on_commit,
        organisation,
        employee,
        reporting_manager,
        delegate_employee,
        department,
    ):
        mock_on_commit.side_effect = lambda callback: callback()
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Rejection Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(workflow=workflow, name='Manager review', sequence=1, mode=ApprovalStageMode.ALL)
        ApprovalStageApprover.objects.create(stage=stage, approver_type=ApprovalApproverType.REPORTING_MANAGER)
        ApprovalStageApprover.objects.create(stage=stage, approver_type=ApprovalApproverType.PRIMARY_ORG_ADMIN)
        policy = ApprovalStageEscalationPolicy.objects.create(
            stage=stage,
            reminder_after_hours=None,
            escalate_after_hours=2,
            escalation_target_type=ApprovalFallbackType.PRIMARY_ORG_ADMIN,
            is_active=True,
        )

        approval_run = create_approval_run(
            department,
            ApprovalRequestKind.LEAVE,
            requester=employee,
            actor=employee.user,
            subject_label='Rejectable leave',
        )
        manager_action = approval_run.actions.get(approver_user=reporting_manager.user)
        admin_action = approval_run.actions.get(approver_user=organisation.primary_admin_user)

        with pytest.raises(ValueError, match='not allowed to act'):
            reject_action(manager_action, employee.user, comment='No')

        manager_action.status = ApprovalActionStatus.APPROVED
        manager_action.save(update_fields=['status', 'modified_at'])
        with pytest.raises(ValueError, match='no longer pending'):
            reject_action(manager_action, reporting_manager.user, comment='No')
        manager_action.status = ApprovalActionStatus.PENDING
        manager_action.save(update_fields=['status', 'modified_at'])

        with patch('apps.approvals.services.get_org_operations_guard', return_value={'approval_actions_blocked': True, 'reason': 'Blocked'}):
            with pytest.raises(ValueError, match='Blocked'):
                reject_action(manager_action, reporting_manager.user, comment='No')

        assert _get_stage_sla_policy(stage) == policy
        assert _resolve_escalation_target(admin_action) == (organisation.primary_admin_user, None)
        policy.is_active = False
        policy.save(update_fields=['is_active', 'modified_at'])
        admin_action.refresh_from_db()
        assert _get_stage_sla_policy(stage) is None
        assert _resolve_escalation_target(admin_action) == (None, None)

        with patch('apps.approvals.services.get_org_operations_guard', return_value={'approval_actions_blocked': False, 'reason': ''}):
            with patch('apps.approvals.services._apply_subject_status'):
                with patch('apps.notifications.tasks.send_approval_outcome_email.delay'):
                    reject_action(manager_action, reporting_manager.user, comment='Missing details')

        approval_run.refresh_from_db()
        manager_action.refresh_from_db()
        admin_action.refresh_from_db()
        assert approval_run.status == ApprovalRunStatus.REJECTED
        assert manager_action.status == ApprovalActionStatus.REJECTED
        assert admin_action.status == ApprovalActionStatus.CANCELLED

        assert _approval_outcome_kind(approval_run, ApprovalRunStatus.APPROVED) == NotificationKind.LEAVE_APPROVED
        approval_run.request_kind = ApprovalRequestKind.SALARY_REVISION
        assert _approval_outcome_kind(approval_run, ApprovalRunStatus.APPROVED) == NotificationKind.COMPENSATION_APPROVED
        approval_run.request_kind = ApprovalRequestKind.PAYROLL_PROCESSING
        assert _approval_outcome_kind(approval_run, ApprovalRunStatus.APPROVED) == NotificationKind.GENERAL

    def test_pending_action_queries_reminders_and_escalation_skip_branches(
        self,
        organisation,
        employee,
        reporting_manager,
        delegate_employee,
        department,
    ):
        workflow = ApprovalWorkflow.objects.create(
            organisation=organisation,
            name='Reminder Workflow',
            is_default=True,
            default_request_kind=ApprovalRequestKind.LEAVE,
            is_active=True,
        )
        stage = ApprovalStage.objects.create(workflow=workflow, name='Reminder stage', sequence=1)
        ApprovalStageApprover.objects.create(stage=stage, approver_type=ApprovalApproverType.REPORTING_MANAGER)
        policy = ApprovalStageEscalationPolicy.objects.create(
            stage=stage,
            reminder_after_hours=4,
            escalate_after_hours=6,
            escalation_target_type=ApprovalFallbackType.SPECIFIC_EMPLOYEE,
            escalation_employee=delegate_employee,
            is_active=True,
        )

        approval_run = create_approval_run(
            department,
            ApprovalRequestKind.LEAVE,
            requester=employee,
            actor=employee.user,
            subject_label='Reminder leave',
        )
        action = approval_run.actions.get()
        action.created_at = timezone.now() - timedelta(hours=2)
        action.save(update_fields=['created_at'])

        assert list(get_pending_approval_actions_for_user(reporting_manager.user, organisation=organisation)) == [action]
        assert list(get_pending_approval_actions_for_user(reporting_manager.user)) == [action]
        assert send_pending_action_reminders(now=timezone.now()) == 0
        assert process_pending_action_escalations(now=timezone.now()) == 0

        policy.escalation_target_type = ApprovalFallbackType.PRIMARY_ORG_ADMIN
        policy.escalation_employee = None
        policy.save(update_fields=['escalation_target_type', 'escalation_employee', 'modified_at'])
        action.approver_user = organisation.primary_admin_user
        action.approver_employee = None
        action.save(update_fields=['approver_user', 'approver_employee', 'modified_at'])
        action.created_at = timezone.now() - timedelta(hours=8)
        action.save(update_fields=['created_at'])
        assert process_pending_action_escalations(now=timezone.now()) == 0

        policy.escalation_target_type = ApprovalFallbackType.SPECIFIC_EMPLOYEE
        policy.escalation_employee = delegate_employee
        policy.save(update_fields=['escalation_target_type', 'escalation_employee', 'modified_at'])
        action.approver_user = reporting_manager.user
        action.approver_employee = reporting_manager
        action.save(update_fields=['approver_user', 'approver_employee', 'modified_at'])
        ApprovalAction.objects.create(
            approval_run=approval_run,
            stage=stage,
            approver_user=delegate_employee.user,
            approver_employee=delegate_employee,
            status=ApprovalActionStatus.PENDING,
        )

        assert process_pending_action_escalations(now=timezone.now()) == 1
        action.refresh_from_db()
        assert action.status == ApprovalActionStatus.CANCELLED
