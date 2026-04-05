from datetime import date
from decimal import Decimal

import pytest

from apps.timeoff.models import (
    DaySession,
    LeaveBalanceEntryType,
    LeaveCreditFrequency,
    LeaveCycle,
    LeaveCycleType,
    LeaveRequest,
    LeaveRequestStatus,
)
from apps.timeoff.services import (
    _calculate_period_credit_amount,
    _compute_credit_for_period,
    _leave_request_units,
    _periods_elapsed,
    credit_leave_for_period,
    get_employee_leave_balances,
    get_or_create_leave_balance,
)
from apps.timeoff.tests.test_services import _create_employee, _create_leave_type, _create_organisation


@pytest.mark.parametrize(
    ('frequency', 'expected'),
    [
        (LeaveCreditFrequency.YEARLY, 1),
        (LeaveCreditFrequency.MONTHLY, 6),
        (LeaveCreditFrequency.QUARTERLY, 2),
        (LeaveCreditFrequency.HALF_YEARLY, 1),
        ('UNSUPPORTED', 0),
    ],
)
def test_periods_elapsed_returns_expected_counts(frequency, expected):
    assert _periods_elapsed(date(2026, 1, 1), date(2026, 6, 30), frequency) == expected


@pytest.mark.django_db
def test_compute_credit_for_period_prorates_yearly_entitlement_on_join():
    organisation = _create_organisation('Credit Proration Org')
    employee = _create_employee(organisation, email='credit-proration@test.com')
    employee.date_of_joining = date(2026, 7, 1)
    employee.save(update_fields=['date_of_joining', 'modified_at'])
    leave_type = _create_leave_type(organisation, code='YR')
    leave_type.credit_frequency = LeaveCreditFrequency.YEARLY
    leave_type.annual_entitlement = Decimal('12.00')
    leave_type.prorate_on_join = True
    leave_type.save(update_fields=['credit_frequency', 'annual_entitlement', 'prorate_on_join', 'modified_at'])

    credit = _compute_credit_for_period(employee, leave_type, date(2026, 1, 1), date(2026, 12, 31))

    assert credit == Decimal('6.05')


@pytest.mark.parametrize(
    ('frequency', 'expected'),
    [
        (LeaveCreditFrequency.MANUAL, Decimal('0.00')),
        (LeaveCreditFrequency.YEARLY, Decimal('24.00')),
        (LeaveCreditFrequency.MONTHLY, Decimal('2.00')),
        (LeaveCreditFrequency.QUARTERLY, Decimal('6.00')),
        (LeaveCreditFrequency.HALF_YEARLY, Decimal('12.00')),
    ],
)
@pytest.mark.django_db
def test_calculate_period_credit_amount_matches_frequency(frequency, expected):
    organisation = _create_organisation(f'Credit Amount Org {frequency}')
    leave_type = _create_leave_type(organisation, code=freq_to_code(frequency))
    leave_type.annual_entitlement = Decimal('24.00')
    leave_type.credit_frequency = frequency
    leave_type.save(update_fields=['annual_entitlement', 'credit_frequency', 'modified_at'])

    assert _calculate_period_credit_amount(leave_type) == expected


def freq_to_code(frequency):
    return str(frequency).replace('_', '')[:8]


@pytest.mark.parametrize(
    ('start_date', 'end_date', 'start_session', 'end_session', 'expected'),
    [
        (date(2026, 5, 1), date(2026, 5, 1), DaySession.FIRST_HALF, DaySession.FIRST_HALF, Decimal('0.50')),
        (date(2026, 5, 1), date(2026, 5, 3), DaySession.FIRST_HALF, DaySession.FULL_DAY, Decimal('2.50')),
        (date(2026, 5, 1), date(2026, 5, 3), DaySession.FULL_DAY, DaySession.SECOND_HALF, Decimal('2.50')),
    ],
)
def test_leave_request_units_handle_half_day_edges(start_date, end_date, start_session, end_session, expected):
    assert _leave_request_units(start_date, end_date, start_session, end_session) == expected


@pytest.mark.django_db
def test_get_or_create_leave_balance_creates_ledger_updates_totals_and_caps_credit():
    organisation = _create_organisation('Balance Org')
    employee = _create_employee(organisation, email='balance@test.com')
    leave_type = _create_leave_type(organisation, code='BAL')
    leave_type.annual_entitlement = Decimal('12.00')
    leave_type.credit_frequency = LeaveCreditFrequency.YEARLY
    leave_type.max_balance = Decimal('8.00')
    leave_type.save(update_fields=['annual_entitlement', 'credit_frequency', 'max_balance', 'modified_at'])

    LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=date(2026, 2, 10),
        end_date=date(2026, 2, 11),
        start_session=DaySession.FULL_DAY,
        end_session=DaySession.FULL_DAY,
        total_units=Decimal('2.00'),
        reason='Approved leave',
        status=LeaveRequestStatus.APPROVED,
    )
    LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=date(2026, 3, 3),
        end_date=date(2026, 3, 3),
        start_session=DaySession.FULL_DAY,
        end_session=DaySession.FULL_DAY,
        total_units=Decimal('1.00'),
        reason='Pending leave',
        status=LeaveRequestStatus.PENDING,
    )

    balance = get_or_create_leave_balance(employee, leave_type, as_of=date(2026, 6, 1))
    repeated = get_or_create_leave_balance(employee, leave_type, as_of=date(2026, 6, 1))

    assert balance == repeated
    assert balance.credited_amount == Decimal('11.00')
    assert balance.used_amount == Decimal('2.00')
    assert balance.pending_amount == Decimal('1.00')
    assert balance.ledger_entries.filter(entry_type=LeaveBalanceEntryType.CREDIT).count() == 1


@pytest.mark.django_db
def test_get_or_create_leave_balance_uses_employee_joining_cycle_window():
    organisation = _create_organisation('Joining Window Org')
    employee = _create_employee(organisation, email='joining-window@test.com')
    employee.date_of_joining = date(2024, 8, 20)
    employee.save(update_fields=['date_of_joining', 'modified_at'])
    leave_type = _create_leave_type(organisation, code='ANN')
    leave_type.leave_plan.leave_cycle.cycle_type = LeaveCycleType.EMPLOYEE_JOINING_DATE
    leave_type.leave_plan.leave_cycle.save(update_fields=['cycle_type', 'modified_at'])

    balance = get_or_create_leave_balance(employee, leave_type, as_of=date(2026, 5, 15))

    assert balance.cycle_start == date(2025, 8, 20)
    assert balance.cycle_end == date(2026, 8, 19)


@pytest.mark.django_db
def test_credit_leave_for_period_returns_none_for_manual_frequency():
    organisation = _create_organisation('Manual Credit Org')
    employee = _create_employee(organisation, email='manual-credit@test.com')
    leave_type = _create_leave_type(organisation, code='MAN')
    leave_type.credit_frequency = LeaveCreditFrequency.MANUAL
    leave_type.save(update_fields=['credit_frequency', 'modified_at'])

    result = credit_leave_for_period(
        employee=employee,
        leave_type=leave_type,
        cycle_start=date(2026, 1, 1),
        cycle_end=date(2026, 12, 31),
    )

    assert result is None


@pytest.mark.django_db
def test_get_employee_leave_balances_returns_active_balances_sorted_by_name():
    organisation = _create_organisation('Balance Summary Org')
    employee = _create_employee(organisation, email='balance-summary@test.com')
    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
    )
    leave_plan = employee.organisation.leave_plans.create(
        leave_cycle=cycle,
        name='Summary Plan',
        is_default=True,
        is_active=True,
        priority=10,
    )
    annual_leave = leave_plan.leave_types.create(
        code='ANL',
        name='Annual Leave',
        annual_entitlement=Decimal('0.00'),
        credit_frequency=LeaveCreditFrequency.MANUAL,
    )
    sick_leave = leave_plan.leave_types.create(
        code='SCK',
        name='Sick Leave',
        annual_entitlement=Decimal('0.00'),
        credit_frequency=LeaveCreditFrequency.MANUAL,
    )
    leave_plan.leave_types.create(
        code='OLD',
        name='Obsolete Leave',
        annual_entitlement=Decimal('0.00'),
        credit_frequency=LeaveCreditFrequency.MANUAL,
        is_active=False,
    )

    get_or_create_leave_balance(employee, annual_leave, as_of=date(2026, 6, 1))
    sick_balance = get_or_create_leave_balance(employee, sick_leave, as_of=date(2026, 6, 1))
    sick_balance.opening_balance = Decimal('2.00')
    sick_balance.carried_forward_amount = Decimal('1.00')
    sick_balance.save(update_fields=['opening_balance', 'carried_forward_amount', 'modified_at'])

    balances = get_employee_leave_balances(employee)

    assert [balance['leave_type_name'] for balance in balances] == ['Annual Leave', 'Sick Leave']
    assert balances[0]['available'] == Decimal('0.00')
    assert balances[1]['available'] == Decimal('3.00')
