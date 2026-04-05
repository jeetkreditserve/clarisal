from datetime import date, time
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalRun,
    ApprovalRunStatus,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.employees.models import Employee, EmployeeStatus
from apps.timeoff.models import (
    DaySession,
    LeaveRequestStatus,
    OnDutyDurationType,
    OnDutyRequestStatus,
)
from apps.timeoff.services import (
    create_leave_request,
    create_on_duty_request,
    upsert_on_duty_policy,
    withdraw_leave_request,
    withdraw_on_duty_request,
)
from apps.timeoff.tests.test_services import _create_employee, _create_leave_type, _create_organisation


def _create_default_workflow(organisation, request_kind):
    approver_user = User.objects.create_user(
        email=f'{request_kind.lower()}-approver-{organisation.id}@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    approver_employee = Employee.objects.create(
        organisation=organisation,
        user=approver_user,
        employee_code=f'{request_kind[:3]}APR',
        designation='Approver',
        status=EmployeeStatus.ACTIVE,
    )
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name=f'{request_kind} Workflow',
        is_default=True,
        default_request_kind=request_kind,
        is_active=True,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=workflow,
        name=f'{request_kind} Rule',
        request_kind=request_kind,
        priority=100,
        is_active=True,
    )
    stage = ApprovalStage.objects.create(workflow=workflow, name='Review', sequence=1)
    ApprovalStageApprover.objects.create(
        stage=stage,
        approver_type=ApprovalApproverType.SPECIFIC_EMPLOYEE,
        approver_employee=approver_employee,
    )
    return workflow


@pytest.mark.django_db
def test_create_leave_request_allows_complementary_half_day_requests_same_day():
    organisation = _create_organisation('Half Day Org')
    employee = _create_employee(organisation, email='half-day@test.com')
    _create_default_workflow(organisation, ApprovalRequestKind.LEAVE)
    leave_type = _create_leave_type(organisation, code='HD')

    first_request = create_leave_request(
        employee,
        leave_type,
        date(2026, 5, 20),
        date(2026, 5, 20),
        DaySession.FIRST_HALF,
        DaySession.FIRST_HALF,
        reason='Morning leave',
        actor=employee.user,
    )
    second_request = create_leave_request(
        employee,
        leave_type,
        date(2026, 5, 20),
        date(2026, 5, 20),
        DaySession.SECOND_HALF,
        DaySession.SECOND_HALF,
        reason='Afternoon leave',
        actor=employee.user,
    )

    assert first_request.total_units == Decimal('0.50')
    assert second_request.total_units == Decimal('0.50')
    assert ApprovalRun.objects.filter(object_id=first_request.id).exists()
    assert ApprovalRun.objects.filter(object_id=second_request.id).exists()


@pytest.mark.django_db
def test_create_leave_request_rejects_same_day_overlap():
    organisation = _create_organisation('Overlap Org')
    employee = _create_employee(organisation, email='overlap@test.com')
    _create_default_workflow(organisation, ApprovalRequestKind.LEAVE)
    leave_type = _create_leave_type(organisation, code='OVR')

    create_leave_request(
        employee,
        leave_type,
        date(2026, 6, 10),
        date(2026, 6, 10),
        DaySession.FIRST_HALF,
        DaySession.FIRST_HALF,
        reason='Existing leave',
        actor=employee.user,
    )

    with pytest.raises(ValueError, match='already exists'):
        create_leave_request(
            employee,
            leave_type,
            date(2026, 6, 10),
            date(2026, 6, 10),
            DaySession.FIRST_HALF,
            DaySession.FIRST_HALF,
            reason='Duplicate leave',
            actor=employee.user,
        )


@pytest.mark.django_db
def test_withdraw_leave_request_cancels_approval_run():
    organisation = _create_organisation('Withdraw Leave Org')
    employee = _create_employee(organisation, email='withdraw-leave@test.com')
    _create_default_workflow(organisation, ApprovalRequestKind.LEAVE)
    leave_type = _create_leave_type(organisation, code='WDL')
    leave_request = create_leave_request(
        employee,
        leave_type,
        date(2026, 7, 10),
        date(2026, 7, 11),
        DaySession.FULL_DAY,
        DaySession.FULL_DAY,
        reason='Trip',
        actor=employee.user,
    )

    withdraw_leave_request(leave_request, actor=employee.user)
    approval_run = ApprovalRun.objects.get(object_id=leave_request.id)

    leave_request.refresh_from_db()

    assert leave_request.status == LeaveRequestStatus.WITHDRAWN
    assert approval_run.status == ApprovalRunStatus.CANCELLED


@pytest.mark.django_db
def test_create_on_duty_request_validates_time_range_and_half_day_units():
    organisation = _create_organisation('On Duty Org')
    employee = _create_employee(organisation, email='on-duty@test.com')
    _create_default_workflow(organisation, ApprovalRequestKind.ON_DUTY)
    policy = upsert_on_duty_policy(organisation, name='Default Policy', is_default=True, is_active=True)

    with pytest.raises(ValueError, match='required for time-range'):
        create_on_duty_request(
            employee,
            policy,
            date(2026, 8, 12),
            date(2026, 8, 12),
            OnDutyDurationType.TIME_RANGE,
            purpose='Client visit',
            actor=employee.user,
        )

    request = create_on_duty_request(
        employee,
        policy,
        date(2026, 8, 12),
        date(2026, 8, 12),
        OnDutyDurationType.FIRST_HALF,
        purpose='Client visit',
        actor=employee.user,
    )

    assert request.total_units == Decimal('0.50')

    with pytest.raises(ValueError, match='only be provided for time-range'):
        create_on_duty_request(
            employee,
            policy,
            date(2026, 8, 13),
            date(2026, 8, 13),
            OnDutyDurationType.FULL_DAY,
            purpose='Errand',
            start_time=time(9, 0),
            end_time=time(11, 0),
            actor=employee.user,
        )


@pytest.mark.django_db
def test_withdraw_on_duty_request_cancels_approval_run():
    organisation = _create_organisation('Withdraw On Duty Org')
    employee = _create_employee(organisation, email='withdraw-on-duty@test.com')
    _create_default_workflow(organisation, ApprovalRequestKind.ON_DUTY)
    policy = upsert_on_duty_policy(organisation, name='Travel Policy', is_default=True, is_active=True)
    request = create_on_duty_request(
        employee,
        policy,
        date(2026, 9, 3),
        date(2026, 9, 3),
        OnDutyDurationType.TIME_RANGE,
        purpose='Vendor meeting',
        start_time=time(10, 0),
        end_time=time(12, 0),
        actor=employee.user,
    )

    withdraw_on_duty_request(request, actor=employee.user)
    approval_run = ApprovalRun.objects.get(object_id=request.id)

    request.refresh_from_db()

    assert request.status == OnDutyRequestStatus.WITHDRAWN
    assert approval_run.status == ApprovalRunStatus.CANCELLED
