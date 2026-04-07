from datetime import date
from decimal import Decimal

import pytest

from apps.attendance.models import WFHRequest
from apps.timeoff.models import (
    CarryForwardMode,
    CompOffAccrual,
    CompOffStatus,
    DaySession,
    LeaveBalance,
    LeaveBalanceEntryType,
    LeaveBalanceLedgerEntry,
    LeaveCycle,
    LeaveCycleType,
    LeavePlan,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
    LeaveWithoutPayEntry,
)
from apps.timeoff.services import get_employee_calendar_month, get_lwp_days_for_period, process_cycle_end_lapse
from apps.timeoff.tests.test_services import _create_employee, _create_leave_type, _create_organisation


@pytest.mark.django_db
def test_employee_calendar_month_includes_wfh_comp_off_and_lwp_entries():
    organisation = _create_organisation('Workforce Calendar Org')
    employee = _create_employee(organisation, email='calendar-workforce@test.com')
    WFHRequest.objects.create(
        employee=employee,
        start_date=date(2026, 5, 6),
        end_date=date(2026, 5, 6),
        session='FULL_DAY',
        reason='Remote day',
        status='APPROVED',
    )
    CompOffAccrual.objects.create(
        employee=employee,
        accrual_date=date(2026, 5, 7),
        units=Decimal('1.00'),
        expires_on=date(2026, 8, 31),
        status='APPROVED',
        reason='Weekend support',
    )
    LeaveWithoutPayEntry.objects.create(
        employee=employee,
        entry_date=date(2026, 5, 8),
        units=Decimal('1.00'),
        reason='Unpaid day',
        source='MANUAL',
        status='APPROVED',
    )

    calendar = get_employee_calendar_month(employee, calendar_month='2026-05')
    entries_by_date = {item['date']: item['entries'] for item in calendar['days']}

    assert entries_by_date['2026-05-06'][0]['kind'] == 'WFH'
    assert entries_by_date['2026-05-07'][0]['kind'] == 'COMP_OFF'
    assert entries_by_date['2026-05-08'][0]['kind'] == 'LWP'


@pytest.mark.django_db
def test_comp_off_accrual_credits_leave_balance():
    """Creating a CompOffAccrual with APPROVED status makes units available."""
    organisation = _create_organisation('CompOff Accrual Org')
    employee = _create_employee(organisation, email='compoff-accrual@test.com')

    accrual = CompOffAccrual.objects.create(
        employee=employee,
        accrual_date=date(2026, 5, 10),
        units=Decimal('1.00'),
        expires_on=date(2026, 8, 31),
        status=CompOffStatus.APPROVED,
        reason='Worked on weekend',
    )

    accrual.refresh_from_db()
    assert accrual.status == CompOffStatus.APPROVED
    assert accrual.units == Decimal('1.00')

    # Verify the accrual is retrievable for the employee
    employee_accruals = CompOffAccrual.objects.filter(
        employee=employee,
        status=CompOffStatus.APPROVED,
    )
    assert employee_accruals.count() == 1
    assert employee_accruals.first().units == Decimal('1.00')


@pytest.mark.django_db
def test_leave_lapse_expires_none_carry_forward_leaves():
    """process_cycle_end_lapse creates an EXPIRY ledger entry and reduces credited_amount."""
    organisation = _create_organisation('Lapse Org')
    employee = _create_employee(organisation, email='lapse@test.com')

    # Set up leave cycle, plan and leave type with NONE carry-forward
    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='2025 Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
    )
    plan = LeavePlan.objects.create(
        organisation=organisation,
        leave_cycle=cycle,
        name='Default Plan',
        is_default=True,
        is_active=True,
    )
    leave_type = LeaveType.objects.create(
        leave_plan=plan,
        code='AL',
        name='Annual Leave',
        annual_entitlement=Decimal('12.00'),
        carry_forward_mode=CarryForwardMode.NONE,
    )

    # Create a LeaveBalance for a cycle that has ended (yesterday-ish)
    cycle_start = date(2025, 1, 1)
    cycle_end = date(2025, 12, 31)
    balance = LeaveBalance.objects.create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        opening_balance=Decimal('0.00'),
        credited_amount=Decimal('5.00'),
        used_amount=Decimal('0.00'),
        pending_amount=Decimal('0.00'),
        carried_forward_amount=Decimal('0.00'),
    )

    # Call the lapse service
    process_cycle_end_lapse(employee, balance)

    # Verify EXPIRY ledger entry was created
    expiry_entries = LeaveBalanceLedgerEntry.objects.filter(
        leave_balance=balance,
        entry_type=LeaveBalanceEntryType.EXPIRY,
    )
    assert expiry_entries.count() == 1
    expiry_entry = expiry_entries.first()
    assert expiry_entry.amount == Decimal('5.00')
    assert expiry_entry.effective_date == cycle_end

    # Verify balance.credited_amount is reduced to 0
    balance.refresh_from_db()
    assert balance.credited_amount == Decimal('0.00')


@pytest.mark.django_db
def test_leave_lapse_idempotent_no_double_expiry():
    """Calling process_cycle_end_lapse twice does not create a second EXPIRY entry."""
    organisation = _create_organisation('Lapse Idempotent Org')
    employee = _create_employee(organisation, email='lapse-idempotent@test.com')

    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='2025 CY',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
    )
    plan = LeavePlan.objects.create(
        organisation=organisation,
        leave_cycle=cycle,
        name='Plan',
        is_default=True,
        is_active=True,
    )
    leave_type = LeaveType.objects.create(
        leave_plan=plan,
        code='SL',
        name='Sick Leave',
        annual_entitlement=Decimal('6.00'),
        carry_forward_mode=CarryForwardMode.NONE,
    )
    balance = LeaveBalance.objects.create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=date(2025, 1, 1),
        cycle_end=date(2025, 12, 31),
        opening_balance=Decimal('0.00'),
        credited_amount=Decimal('3.00'),
        used_amount=Decimal('0.00'),
        pending_amount=Decimal('0.00'),
        carried_forward_amount=Decimal('0.00'),
    )

    process_cycle_end_lapse(employee, balance)
    process_cycle_end_lapse(employee, balance)  # second call should be a no-op

    expiry_count = LeaveBalanceLedgerEntry.objects.filter(
        leave_balance=balance,
        entry_type=LeaveBalanceEntryType.EXPIRY,
    ).count()
    assert expiry_count == 1


@pytest.mark.django_db
def test_get_lwp_days_for_period_counts_approved_lop_leave_requests():
    """get_lwp_days_for_period returns total units for approved LOP leave requests in a period."""
    organisation = _create_organisation('LWP Period Org')
    employee = _create_employee(organisation, email='lwp-period@test.com')

    # Create a leave type flagged as loss-of-pay
    leave_type = _create_leave_type(organisation, code='LOP')
    leave_type.is_loss_of_pay = True
    leave_type.save(update_fields=['is_loss_of_pay', 'modified_at'])

    # Create an approved LOP leave request within the period
    LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=date(2026, 5, 5),
        end_date=date(2026, 5, 6),
        start_session=DaySession.FULL_DAY,
        end_session=DaySession.FULL_DAY,
        total_units=Decimal('2.00'),
        status=LeaveRequestStatus.APPROVED,
    )
    # A PENDING request that should not be counted
    LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 10),
        start_session=DaySession.FULL_DAY,
        end_session=DaySession.FULL_DAY,
        total_units=Decimal('1.00'),
        status=LeaveRequestStatus.PENDING,
    )

    period_start = date(2026, 5, 1)
    period_end = date(2026, 5, 31)

    lwp_days = get_lwp_days_for_period(employee, period_start, period_end)

    assert lwp_days == Decimal('2.00')
