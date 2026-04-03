from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.approvals.models import (
    ApprovalApproverType,
    ApprovalRequestKind,
    ApprovalStage,
    ApprovalStageApprover,
    ApprovalWorkflow,
    ApprovalWorkflowRule,
)
from apps.timeoff.models import (
    CarryForwardMode,
    LeaveBalance,
    LeaveBalanceEntryType,
    LeaveBalanceLedgerEntry,
    LeaveCycle,
    LeaveCycleType,
    LeavePlan,
    LeaveType,
)

ZERO = Decimal('0.00')


def _create_organisation(name='Timeoff Org'):
    return Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


def _create_employee(organisation, email='timeoff.employee@test.com'):
    user = User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code=email.split('@')[0].upper()[:8],
        designation='Engineer',
        status=EmployeeStatus.ACTIVE,
        date_of_joining=date(2025, 1, 1),
    )


def _create_leave_type(
    organisation,
    *,
    code='AL',
    carry_forward_mode=CarryForwardMode.NONE,
    carry_forward_cap=None,
):
    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
    )
    plan = LeavePlan.objects.create(
        organisation=organisation,
        leave_cycle=cycle,
        name='Default Leave Plan',
        is_default=True,
        is_active=True,
    )
    return LeaveType.objects.create(
        leave_plan=plan,
        code=code,
        name=f'{code} Leave',
        annual_entitlement=Decimal('12.00'),
        carry_forward_mode=carry_forward_mode,
        carry_forward_cap=carry_forward_cap,
    )


def _create_leave_approval_workflow(organisation):
    approver_user = User.objects.create_user(
        email=f'approver-{organisation.id}@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    approver_employee = Employee.objects.create(
        organisation=organisation,
        user=approver_user,
        employee_code=f'APR{str(organisation.id).replace("-", "")[:5]}',
        designation='HR Manager',
        status=EmployeeStatus.ACTIVE,
    )
    workflow = ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Leave Workflow',
        is_default=True,
        default_request_kind=ApprovalRequestKind.LEAVE,
        is_active=True,
    )
    ApprovalWorkflowRule.objects.create(
        workflow=workflow,
        name='Leave Rule',
        request_kind=ApprovalRequestKind.LEAVE,
        priority=100,
        is_active=True,
    )
    stage = ApprovalStage.objects.create(
        workflow=workflow,
        name='Manager Review',
        sequence=1,
    )
    ApprovalStageApprover.objects.create(
        stage=stage,
        approver_type=ApprovalApproverType.SPECIFIC_EMPLOYEE,
        approver_employee=approver_employee,
    )
    return workflow


def _create_balance(employee, leave_type, *, cycle_start, cycle_end, available_amount):
    return LeaveBalance.objects.create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        opening_balance=ZERO,
        credited_amount=available_amount,
        used_amount=ZERO,
        pending_amount=ZERO,
        carried_forward_amount=ZERO,
    )


@pytest.mark.django_db
class TestCarryForwardCapEnforcement:
    def test_carry_forward_none_produces_zero_balance_in_new_cycle(self):
        from apps.timeoff.services import process_cycle_end_carry_forward

        organisation = _create_organisation('Carry None Org')
        employee = _create_employee(organisation, email='none@test.com')
        leave_type = _create_leave_type(organisation, carry_forward_mode=CarryForwardMode.NONE)
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2025, 1, 1),
            cycle_end=date(2025, 12, 31),
            available_amount=Decimal('5.00'),
        )

        process_cycle_end_carry_forward(
            employee=employee,
            leave_type=leave_type,
            old_cycle_start=date(2025, 1, 1),
            old_cycle_end=date(2025, 12, 31),
            new_cycle_start=date(2026, 1, 1),
            new_cycle_end=date(2026, 12, 31),
        )

        new_balance = LeaveBalance.objects.get(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )
        assert new_balance.carried_forward_amount == ZERO

    def test_carry_forward_capped_respects_cap(self):
        from apps.timeoff.services import process_cycle_end_carry_forward

        organisation = _create_organisation('Carry Cap Org')
        employee = _create_employee(organisation, email='cap@test.com')
        leave_type = _create_leave_type(
            organisation,
            code='CL',
            carry_forward_mode=CarryForwardMode.CAPPED,
            carry_forward_cap=Decimal('5.00'),
        )
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2025, 1, 1),
            cycle_end=date(2025, 12, 31),
            available_amount=Decimal('10.00'),
        )

        process_cycle_end_carry_forward(
            employee=employee,
            leave_type=leave_type,
            old_cycle_start=date(2025, 1, 1),
            old_cycle_end=date(2025, 12, 31),
            new_cycle_start=date(2026, 1, 1),
            new_cycle_end=date(2026, 12, 31),
        )

        new_balance = LeaveBalance.objects.get(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )
        assert new_balance.carried_forward_amount == Decimal('5.00')

    def test_carry_forward_unlimited_carries_full_balance(self):
        from apps.timeoff.services import process_cycle_end_carry_forward

        organisation = _create_organisation('Carry Unlimited Org')
        employee = _create_employee(organisation, email='unlimited@test.com')
        leave_type = _create_leave_type(
            organisation,
            code='UL',
            carry_forward_mode=CarryForwardMode.UNLIMITED,
        )
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2025, 1, 1),
            cycle_end=date(2025, 12, 31),
            available_amount=Decimal('45.00'),
        )

        process_cycle_end_carry_forward(
            employee=employee,
            leave_type=leave_type,
            old_cycle_start=date(2025, 1, 1),
            old_cycle_end=date(2025, 12, 31),
            new_cycle_start=date(2026, 1, 1),
            new_cycle_end=date(2026, 12, 31),
        )

        new_balance = LeaveBalance.objects.get(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )
        assert new_balance.carried_forward_amount == Decimal('45.00')

    def test_carry_forward_creates_ledger_entry(self):
        from apps.timeoff.services import process_cycle_end_carry_forward

        organisation = _create_organisation('Carry Ledger Org')
        employee = _create_employee(organisation, email='ledger@test.com')
        leave_type = _create_leave_type(
            organisation,
            code='LG',
            carry_forward_mode=CarryForwardMode.CAPPED,
            carry_forward_cap=Decimal('5.00'),
        )
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2025, 1, 1),
            cycle_end=date(2025, 12, 31),
            available_amount=Decimal('8.00'),
        )

        process_cycle_end_carry_forward(
            employee=employee,
            leave_type=leave_type,
            old_cycle_start=date(2025, 1, 1),
            old_cycle_end=date(2025, 12, 31),
            new_cycle_start=date(2026, 1, 1),
            new_cycle_end=date(2026, 12, 31),
        )

        ledger_entry = LeaveBalanceLedgerEntry.objects.filter(
            leave_balance__employee=employee,
            leave_balance__leave_type=leave_type,
            leave_balance__cycle_start=date(2026, 1, 1),
            leave_balance__cycle_end=date(2026, 12, 31),
            entry_type=LeaveBalanceEntryType.CARRY_FORWARD,
        ).first()
        assert ledger_entry is not None
        assert ledger_entry.amount == Decimal('5.00')


@pytest.mark.django_db
class TestMaxBalanceEnforcement:
    def test_credit_does_not_exceed_max_balance(self):
        from apps.timeoff.services import credit_leave_for_period

        organisation = _create_organisation('Max Balance Org')
        employee = _create_employee(organisation, email='max@test.com')
        leave_type = _create_leave_type(
            organisation,
            code='MB',
            carry_forward_mode=CarryForwardMode.NONE,
        )
        leave_type.annual_entitlement = Decimal('24.00')
        leave_type.credit_frequency = 'MONTHLY'
        leave_type.max_balance = Decimal('15.00')
        leave_type.save(update_fields=['annual_entitlement', 'credit_frequency', 'max_balance', 'modified_at'])
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            available_amount=Decimal('13.00'),
        )

        credit_leave_for_period(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )

        balance = LeaveBalance.objects.get(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )
        assert balance.credited_amount == Decimal('15.00')

    def test_credit_denied_when_already_at_max_balance(self):
        from apps.timeoff.services import credit_leave_for_period

        organisation = _create_organisation('Maxed Out Org')
        employee = _create_employee(organisation, email='maxed@test.com')
        leave_type = _create_leave_type(organisation, code='MX')
        leave_type.annual_entitlement = Decimal('12.00')
        leave_type.credit_frequency = 'MONTHLY'
        leave_type.max_balance = Decimal('10.00')
        leave_type.save(update_fields=['annual_entitlement', 'credit_frequency', 'max_balance', 'modified_at'])
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            available_amount=Decimal('10.00'),
        )

        credit_leave_for_period(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )

        balance = LeaveBalance.objects.get(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )
        assert balance.credited_amount == Decimal('10.00')

    def test_max_balance_none_means_no_cap(self):
        from apps.timeoff.services import credit_leave_for_period

        organisation = _create_organisation('No Cap Org')
        employee = _create_employee(organisation, email='nocap@test.com')
        leave_type = _create_leave_type(organisation, code='NC')
        leave_type.annual_entitlement = Decimal('24.00')
        leave_type.credit_frequency = 'MONTHLY'
        leave_type.max_balance = None
        leave_type.save(update_fields=['annual_entitlement', 'credit_frequency', 'max_balance', 'modified_at'])
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            available_amount=Decimal('20.00'),
        )

        credit_leave_for_period(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )

        balance = LeaveBalance.objects.get(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
        )
        assert balance.credited_amount == Decimal('22.00')


@pytest.mark.django_db
class TestLeaveBalanceValidation:
    def test_non_lop_leave_overdraw_prevented(self):
        from apps.timeoff.services import validate_leave_balance

        organisation = _create_organisation('Validate Non LOP Org')
        employee = _create_employee(organisation, email='validate@test.com')
        leave_type = _create_leave_type(organisation, code='VL')
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            available_amount=Decimal('5.00'),
        )

        with pytest.raises(ValueError, match='Insufficient leave balance'):
            validate_leave_balance(
                employee=employee,
                leave_type=leave_type,
                cycle_start=date(2026, 1, 1),
                cycle_end=date(2026, 12, 31),
                requested_units=Decimal('6.00'),
            )

    def test_pending_leaves_count_against_available_balance(self):
        from apps.timeoff.services import validate_leave_balance

        organisation = _create_organisation('Validate Pending Org')
        employee = _create_employee(organisation, email='pending@test.com')
        leave_type = _create_leave_type(organisation, code='PD')
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            opening_balance=ZERO,
            credited_amount=Decimal('10.00'),
            used_amount=ZERO,
            pending_amount=Decimal('2.00'),
            carried_forward_amount=ZERO,
        )

        with pytest.raises(ValueError, match='Insufficient leave balance'):
            validate_leave_balance(
                employee=employee,
                leave_type=leave_type,
                cycle_start=date(2026, 1, 1),
                cycle_end=date(2026, 12, 31),
                requested_units=Decimal('9.00'),
            )

    def test_lop_leave_allows_overdraw(self):
        from apps.timeoff.services import validate_leave_balance

        organisation = _create_organisation('Validate LOP Org')
        employee = _create_employee(organisation, email='lop@test.com')
        leave_type = _create_leave_type(organisation, code='LP')
        leave_type.is_loss_of_pay = True
        leave_type.save(update_fields=['is_loss_of_pay', 'modified_at'])
        _create_balance(
            employee,
            leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            available_amount=ZERO,
        )

        validate_leave_balance(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            requested_units=Decimal('5.00'),
        )


@pytest.mark.django_db
class TestLeaveEncashment:
    def test_encashment_request_created_with_pending_approval(self):
        from apps.timeoff.models import LeaveEncashmentStatus
        from apps.timeoff.services import create_leave_encashment_request

        organisation = _create_organisation('Encashment Org')
        employee = _create_employee(organisation, email='encash@test.com')
        _create_leave_approval_workflow(organisation)
        leave_type = _create_leave_type(organisation, code='EN')
        leave_type.allows_encashment = True
        leave_type.save(update_fields=['allows_encashment', 'modified_at'])
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            opening_balance=ZERO,
            credited_amount=Decimal('10.00'),
            used_amount=ZERO,
            pending_amount=ZERO,
            carried_forward_amount=ZERO,
        )

        request = create_leave_encashment_request(
            employee=employee,
            leave_type=leave_type,
            cycle_start=date(2026, 1, 1),
            cycle_end=date(2026, 12, 31),
            days_to_encash=Decimal('5.00'),
            actor=employee.user,
        )

        assert request.status == LeaveEncashmentStatus.PENDING
        assert request.days_to_encash == Decimal('5.00')
        assert request.approval_run is not None
