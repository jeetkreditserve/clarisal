import calendar
import math
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.approvals.models import ApprovalRequestKind
from apps.approvals.services import cancel_approval_run, create_approval_run
from apps.audit.services import log_audit_event

from .models import (
    CarryForwardMode,
    DaySession,
    Holiday,
    HolidayCalendar,
    HolidayCalendarLocation,
    HolidayCalendarStatus,
    LeaveBalance,
    LeaveBalanceEntryType,
    LeaveBalanceLedgerEntry,
    LeaveCreditFrequency,
    LeaveCycle,
    LeaveCycleType,
    LeaveEncashmentRequest,
    LeaveEncashmentStatus,
    LeavePlan,
    LeavePlanRule,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
    OnDutyDurationType,
    OnDutyPolicy,
    OnDutyRequest,
    OnDutyRequestStatus,
)
from .repositories import (
    get_leave_balance_record,
    get_leave_request_total_units,
    get_total_days_to_encash,
    list_leave_requests_in_range,
    list_overlapping_leave_requests,
)

ZERO = Decimal('0.00')


def _decimal(value):
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _get_single_day_half_session(start_date, end_date, start_session, end_session):
    if start_date != end_date:
        return None
    if start_session != end_session:
        return None
    if start_session not in [DaySession.FIRST_HALF, DaySession.SECOND_HALF]:
        return None
    return start_session


def _leave_requests_overlap(existing_request, start_date, end_date, start_session, end_session):
    requested_half_session = _get_single_day_half_session(start_date, end_date, start_session, end_session)
    existing_half_session = _get_single_day_half_session(
        existing_request.start_date,
        existing_request.end_date,
        existing_request.start_session,
        existing_request.end_session,
    )
    if (
        requested_half_session
        and existing_half_session
        and start_date == end_date == existing_request.start_date == existing_request.end_date
        and requested_half_session != existing_half_session
    ):
        return False
    return True


def get_org_operations_guard(organisation):
    from apps.organisations.services import get_org_operations_guard as org_guard

    return org_guard(organisation)


def get_default_leave_cycle(organisation):
    return LeaveCycle.objects.filter(organisation=organisation, is_default=True, is_active=True).first()


def upsert_leave_cycle(organisation, actor=None, cycle=None, **fields):
    with transaction.atomic():
        target_is_default = fields.get('is_default', cycle.is_default if cycle is not None else False)
        if target_is_default:
            LeaveCycle.objects.filter(organisation=organisation).exclude(id=getattr(cycle, 'id', None)).update(is_default=False)
        if cycle is None:
            cycle = LeaveCycle.objects.create(
                organisation=organisation,
                created_by=actor,
                **fields,
            )
        else:
            for attr, value in fields.items():
                setattr(cycle, attr, value)
            cycle.save()

    log_audit_event(actor, 'leave_cycle.upserted', organisation=organisation, target=cycle)
    return cycle


def _upsert_leave_plan_relations(leave_plan, leave_types=None, rules=None):
    if leave_types is not None:
        keep_ids = []
        for payload in leave_types:
            record_id = payload.pop('id', None)
            payload['annual_entitlement'] = _decimal(payload.get('annual_entitlement', 0))
            if payload.get('carry_forward_cap') is not None:
                payload['carry_forward_cap'] = _decimal(payload['carry_forward_cap'])
            if payload.get('max_balance') is not None:
                payload['max_balance'] = _decimal(payload['max_balance'])
            if payload.get('attachment_after_days') is not None:
                payload['attachment_after_days'] = _decimal(payload['attachment_after_days'])
            if record_id:
                leave_type = leave_plan.leave_types.get(id=record_id)
                for attr, value in payload.items():
                    setattr(leave_type, attr, value)
                leave_type.save()
            else:
                leave_type = LeaveType.objects.create(leave_plan=leave_plan, **payload)
            keep_ids.append(leave_type.id)
        leave_plan.leave_types.exclude(id__in=keep_ids).delete()

    if rules is not None:
        keep_ids = []
        for payload in rules:
            record_id = payload.pop('id', None)
            if record_id:
                rule = leave_plan.rules.get(id=record_id)
                for attr, value in payload.items():
                    setattr(rule, attr, value)
                rule.save()
            else:
                rule = LeavePlanRule.objects.create(leave_plan=leave_plan, **payload)
            keep_ids.append(rule.id)
        leave_plan.rules.exclude(id__in=keep_ids).delete()


def create_leave_plan(organisation, actor=None, leave_types=None, rules=None, **fields):
    with transaction.atomic():
        if fields.get('is_default'):
            LeavePlan.objects.filter(organisation=organisation).update(is_default=False)
        leave_plan = LeavePlan.objects.create(organisation=organisation, created_by=actor, **fields)
        _upsert_leave_plan_relations(leave_plan, leave_types=leave_types or [], rules=rules or [])
    log_audit_event(actor, 'leave_plan.created', organisation=organisation, target=leave_plan)
    return leave_plan


def update_leave_plan(leave_plan, actor=None, leave_types=None, rules=None, **fields):
    with transaction.atomic():
        target_is_default = fields.get('is_default', leave_plan.is_default)
        if target_is_default:
            LeavePlan.objects.filter(organisation=leave_plan.organisation).exclude(id=leave_plan.id).update(is_default=False)
        for attr, value in fields.items():
            setattr(leave_plan, attr, value)
        leave_plan.save()
        _upsert_leave_plan_relations(leave_plan, leave_types=leave_types, rules=rules)
    log_audit_event(actor, 'leave_plan.updated', organisation=leave_plan.organisation, target=leave_plan)
    return leave_plan


def _rule_matches_employee(rule, employee):
    if not rule.is_active:
        return False
    if rule.department_id and employee.department_id != rule.department_id:
        return False
    if rule.office_location_id and employee.office_location_id != rule.office_location_id:
        return False
    if rule.specific_employee_id and employee.id != rule.specific_employee_id:
        return False
    if rule.employment_type and employee.employment_type != rule.employment_type:
        return False
    if rule.designation and (employee.designation or '').strip().lower() != rule.designation.strip().lower():
        return False
    return True


def resolve_employee_leave_plan(employee):
    if hasattr(employee, 'leave_plan_assignment'):
        return employee.leave_plan_assignment.leave_plan

    plans = LeavePlan.objects.filter(organisation=employee.organisation, is_active=True).select_related('leave_cycle').prefetch_related('rules', 'leave_types')
    matching = []
    for plan in plans:
        for rule in plan.rules.all():
            if _rule_matches_employee(rule, employee):
                matching.append((rule.priority, plan.priority, plan))
                break
    if matching:
        matching.sort(key=lambda item: (item[0], item[1], item[2].name))
        return matching[0][2]
    return plans.filter(is_default=True).first()


def get_cycle_window(leave_cycle, employee, as_of=None):
    today = as_of or timezone.localdate()
    if leave_cycle.cycle_type == LeaveCycleType.EMPLOYEE_JOINING_DATE:
        if not employee.date_of_joining:
            start = today
        else:
            join = employee.date_of_joining
            start = date(today.year, join.month, join.day)
            if start > today:
                start = date(today.year - 1, join.month, join.day)
        end = start.replace(year=start.year + 1) - timedelta(days=1)
        return start, end

    if leave_cycle.cycle_type == LeaveCycleType.FINANCIAL_YEAR:
        start_month, start_day = 4, 1
    else:
        start_month = leave_cycle.start_month
        start_day = leave_cycle.start_day
    start = date(today.year, start_month, start_day)
    if start > today:
        start = date(today.year - 1, start_month, start_day)
    end = date(start.year + 1, start_month, start_day) - timedelta(days=1)
    return start, end


def _periods_elapsed(start_date, end_date, frequency):
    if frequency == LeaveCreditFrequency.YEARLY:
        return 1
    if frequency == LeaveCreditFrequency.MONTHLY:
        return max(1, (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1)
    if frequency == LeaveCreditFrequency.QUARTERLY:
        months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        return max(1, math.ceil(months / 3))
    if frequency == LeaveCreditFrequency.HALF_YEARLY:
        months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        return max(1, math.ceil(months / 6))
    return 0


def _compute_credit_for_period(employee, leave_type, cycle_start, cycle_end):
    annual = _decimal(leave_type.annual_entitlement)
    if leave_type.credit_frequency == LeaveCreditFrequency.MANUAL:
        return Decimal('0.00')
    if leave_type.credit_frequency == LeaveCreditFrequency.YEARLY:
        if leave_type.prorate_on_join and employee.date_of_joining and cycle_start <= employee.date_of_joining <= cycle_end:
            total_days = (cycle_end - cycle_start).days + 1
            remaining_days = (cycle_end - employee.date_of_joining).days + 1
            return _decimal(annual * Decimal(remaining_days) / Decimal(total_days))
        return annual

    periods_per_year = {
        LeaveCreditFrequency.MONTHLY: Decimal('12'),
        LeaveCreditFrequency.QUARTERLY: Decimal('4'),
        LeaveCreditFrequency.HALF_YEARLY: Decimal('2'),
    }[leave_type.credit_frequency]
    periods_elapsed = Decimal(_periods_elapsed(cycle_start, timezone.localdate(), leave_type.credit_frequency))
    entitlement = annual / periods_per_year * periods_elapsed
    if leave_type.prorate_on_join and employee.date_of_joining and cycle_start <= employee.date_of_joining <= cycle_end:
        total_days = (cycle_end - cycle_start).days + 1
        worked_days = (cycle_end - employee.date_of_joining).days + 1
        entitlement = entitlement * Decimal(worked_days) / Decimal(total_days)
    return _decimal(entitlement)


def _calculate_period_credit_amount(leave_type):
    annual = _decimal(leave_type.annual_entitlement)
    if leave_type.credit_frequency == LeaveCreditFrequency.MANUAL:
        return ZERO
    if leave_type.credit_frequency == LeaveCreditFrequency.YEARLY:
        return annual
    if leave_type.credit_frequency == LeaveCreditFrequency.MONTHLY:
        return _decimal(annual / Decimal('12'))
    if leave_type.credit_frequency == LeaveCreditFrequency.QUARTERLY:
        return _decimal(annual / Decimal('4'))
    if leave_type.credit_frequency == LeaveCreditFrequency.HALF_YEARLY:
        return _decimal(annual / Decimal('2'))
    return ZERO


def _leave_request_units(start_date, end_date, start_session, end_session):
    days = Decimal((end_date - start_date).days + 1)
    if start_date == end_date and start_session != DaySession.FULL_DAY and end_session != DaySession.FULL_DAY:
        return Decimal('0.50')
    if start_session != DaySession.FULL_DAY:
        days -= Decimal('0.50')
    if end_session != DaySession.FULL_DAY:
        days -= Decimal('0.50')
    return _decimal(days)


def get_or_create_leave_balance(employee, leave_type, as_of=None):
    cycle_start, cycle_end = get_cycle_window(leave_type.leave_plan.leave_cycle, employee, as_of=as_of)
    balance, created = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        defaults={
            'opening_balance': Decimal('0.00'),
            'credited_amount': Decimal('0.00'),
            'used_amount': Decimal('0.00'),
            'pending_amount': Decimal('0.00'),
            'carried_forward_amount': Decimal('0.00'),
        },
    )

    credited = _compute_credit_for_period(employee, leave_type, cycle_start, cycle_end)
    used_total = get_leave_request_total_units(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        status=LeaveRequestStatus.APPROVED,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
    )
    pending_total = get_leave_request_total_units(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        status=LeaveRequestStatus.PENDING,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
    )
    used = _decimal(used_total or Decimal('0.00'))
    pending = _decimal(pending_total or Decimal('0.00'))
    capped_credited = _decimal(credited)
    if leave_type.max_balance is not None:
        max_credit_total = _decimal(
            leave_type.max_balance
            - balance.opening_balance
            - balance.carried_forward_amount
            + used
            + pending
        )
        capped_credited = max(ZERO, min(capped_credited, max_credit_total))
    balance.credited_amount = capped_credited
    balance.used_amount = _decimal(used)
    balance.pending_amount = _decimal(pending)
    balance.save(update_fields=['credited_amount', 'used_amount', 'pending_amount', 'modified_at'])
    if created:
        LeaveBalanceLedgerEntry.objects.create(
            leave_balance=balance,
            entry_type=LeaveBalanceEntryType.CREDIT,
            amount=balance.credited_amount,
            effective_date=cycle_start,
        )
    return balance


@transaction.atomic
def credit_leave_for_period(*, employee, leave_type, cycle_start, cycle_end, credit_date=None, actor=None):
    credit_amount = _calculate_period_credit_amount(leave_type)
    if credit_amount <= ZERO:
        return None

    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        defaults={
            'opening_balance': ZERO,
            'credited_amount': ZERO,
            'used_amount': ZERO,
            'pending_amount': ZERO,
            'carried_forward_amount': ZERO,
        },
    )

    if leave_type.max_balance is not None:
        current_total = (
            balance.opening_balance
            + balance.carried_forward_amount
            + balance.credited_amount
            - balance.used_amount
            - balance.pending_amount
        )
        available_capacity = _decimal(leave_type.max_balance - current_total)
        if available_capacity <= ZERO:
            return balance
        credit_amount = min(credit_amount, available_capacity)

    balance.credited_amount = _decimal(balance.credited_amount + credit_amount)
    balance.save(update_fields=['credited_amount', 'modified_at'])
    LeaveBalanceLedgerEntry.objects.create(
        leave_balance=balance,
        entry_type=LeaveBalanceEntryType.CREDIT,
        amount=credit_amount,
        effective_date=credit_date or date.today(),
        note=f'Periodic credit ({leave_type.credit_frequency})',
        created_by=actor,
    )
    return balance


def get_employee_leave_balances(employee):
    leave_plan = resolve_employee_leave_plan(employee)
    if leave_plan is None:
        return []
    balances = []
    for leave_type in leave_plan.leave_types.filter(is_active=True).order_by('name'):
        balance = get_or_create_leave_balance(employee, leave_type)
        available = balance.opening_balance + balance.carried_forward_amount + balance.credited_amount - balance.used_amount - balance.pending_amount
        balances.append(
            {
                'leave_type_id': str(leave_type.id),
                'leave_type_name': leave_type.name,
                'color': leave_type.color,
                'available': _decimal(available),
                'credited': balance.credited_amount,
                'used': balance.used_amount,
                'pending': balance.pending_amount,
            }
        )
    return balances


@transaction.atomic
def process_cycle_end_carry_forward(
    *,
    employee,
    leave_type,
    old_cycle_start,
    old_cycle_end,
    new_cycle_start,
    new_cycle_end,
    actor=None,
):
    old_balance = get_leave_balance_record(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        cycle_start=old_cycle_start,
        cycle_end=old_cycle_end,
    )
    available_to_carry = ZERO
    if old_balance is not None:
        available_to_carry = max(
            ZERO,
            old_balance.opening_balance
            + old_balance.carried_forward_amount
            + old_balance.credited_amount
            - old_balance.used_amount
            - old_balance.pending_amount,
        )

    if leave_type.carry_forward_mode == CarryForwardMode.NONE:
        carry_forward_amount = ZERO
    elif leave_type.carry_forward_mode == CarryForwardMode.UNLIMITED:
        carry_forward_amount = _decimal(available_to_carry)
    else:
        cap = _decimal(leave_type.carry_forward_cap or ZERO)
        carry_forward_amount = min(_decimal(available_to_carry), cap)

    new_balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=new_cycle_start,
        cycle_end=new_cycle_end,
        defaults={
            'opening_balance': ZERO,
            'credited_amount': ZERO,
            'used_amount': ZERO,
            'pending_amount': ZERO,
            'carried_forward_amount': ZERO,
        },
    )
    new_balance.carried_forward_amount = carry_forward_amount
    new_balance.save(update_fields=['carried_forward_amount', 'modified_at'])
    LeaveBalanceLedgerEntry.objects.update_or_create(
        leave_balance=new_balance,
        entry_type=LeaveBalanceEntryType.CARRY_FORWARD,
        effective_date=new_cycle_start,
        defaults={
            'amount': carry_forward_amount,
            'note': f'Carry forward from {old_cycle_start.isoformat()} to {old_cycle_end.isoformat()}',
            'created_by': actor,
        },
    )
    return new_balance


def validate_leave_balance(*, employee, leave_type, requested_units, cycle_start=None, cycle_end=None, as_of=None):
    if leave_type.is_loss_of_pay:
        return

    if cycle_start is not None and cycle_end is not None:
        balance = get_leave_balance_record(
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
        )
    else:
        balance = get_or_create_leave_balance(employee, leave_type, as_of=as_of)

    available = ZERO
    if balance is not None:
        available = (
            balance.opening_balance
            + balance.carried_forward_amount
            + balance.credited_amount
            - balance.used_amount
            - balance.pending_amount
        )

    if _decimal(requested_units) > _decimal(available):
        raise ValueError(
            f'Insufficient leave balance. Available: {_decimal(available)} days, '
            f'Requested: {_decimal(requested_units)} days.'
        )


@transaction.atomic
def create_leave_encashment_request(*, employee, leave_type, cycle_start, cycle_end, days_to_encash, actor=None):
    if not leave_type.allows_encashment:
        raise ValueError(f"Leave type '{leave_type.name}' does not allow encashment.")

    balance = get_leave_balance_record(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
    )
    available = ZERO
    if balance is not None:
        available = (
            balance.opening_balance
            + balance.carried_forward_amount
            + balance.credited_amount
            - balance.used_amount
            - balance.pending_amount
        )
    if _decimal(days_to_encash) > _decimal(available):
        raise ValueError(
            f'Cannot encash {_decimal(days_to_encash)} days. Available balance: {_decimal(available)} days.'
        )

    if leave_type.max_encashment_days_per_year is not None:
        already_encashed = get_total_days_to_encash(
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            statuses=[
                LeaveEncashmentStatus.PENDING,
                LeaveEncashmentStatus.APPROVED,
                LeaveEncashmentStatus.PAID,
            ],
        )
        if _decimal(already_encashed) + _decimal(days_to_encash) > _decimal(leave_type.max_encashment_days_per_year):
            raise ValueError(f'Exceeds annual encashment limit of {leave_type.max_encashment_days_per_year} days.')

    encashment_request = LeaveEncashmentRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        days_to_encash=_decimal(days_to_encash),
        status=LeaveEncashmentStatus.PENDING,
    )
    approval_run = create_approval_run(
        encashment_request,
        ApprovalRequestKind.LEAVE,
        requester=employee,
        actor=actor,
        leave_type=leave_type,
        subject_label=f'{leave_type.name} encashment',
    )
    encashment_request.approval_run = approval_run
    encashment_request.save(update_fields=['approval_run', 'modified_at'])
    return encashment_request


@transaction.atomic
def finalize_leave_encashment(encashment_request):
    balance = LeaveBalance.objects.select_for_update().get(
        employee=encashment_request.employee,
        leave_type=encashment_request.leave_type,
        cycle_start=encashment_request.cycle_start,
        cycle_end=encashment_request.cycle_end,
    )
    ledger_note = f'Leave encashment - request {encashment_request.id}'
    if balance.ledger_entries.filter(
        entry_type=LeaveBalanceEntryType.DEBIT,
        note=ledger_note,
    ).exists():
        return encashment_request

    balance.used_amount = _decimal(balance.used_amount + encashment_request.days_to_encash)
    balance.save(update_fields=['used_amount', 'modified_at'])
    LeaveBalanceLedgerEntry.objects.create(
        leave_balance=balance,
        entry_type=LeaveBalanceEntryType.DEBIT,
        amount=encashment_request.days_to_encash,
        effective_date=date.today(),
        note=ledger_note,
    )
    return encashment_request


def create_leave_request(employee, leave_type, start_date, end_date, start_session, end_session, reason='', actor=None):
    if end_date < start_date:
        raise ValueError('End date cannot be before start date.')
    overlapping_requests = list_overlapping_leave_requests(
        employee_id=employee.id,
        start_date=start_date,
        end_date=end_date,
    )
    for existing_request in overlapping_requests:
        if _leave_requests_overlap(existing_request, start_date, end_date, start_session, end_session):
            raise ValueError('A leave request already exists for the selected dates.')
    total_units = _leave_request_units(start_date, end_date, start_session, end_session)
    validate_leave_balance(employee=employee, leave_type=leave_type, requested_units=total_units, as_of=start_date)

    leave_request = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        start_session=start_session,
        end_session=end_session,
        total_units=total_units,
        reason=reason,
        status=LeaveRequestStatus.PENDING,
    )
    create_approval_run(
        leave_request,
        ApprovalRequestKind.LEAVE,
        requester=employee,
        actor=actor,
        leave_type=leave_type,
        subject_label=f'{leave_type.name}: {start_date.isoformat()} to {end_date.isoformat()}',
    )
    get_or_create_leave_balance(employee, leave_type)
    log_audit_event(actor or employee.user, 'leave.request.created', organisation=employee.organisation, target=leave_request)
    return leave_request


def withdraw_leave_request(leave_request, actor=None):
    if leave_request.status not in [LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]:
        raise ValueError('Only pending or approved leave requests can be withdrawn.')
    leave_request.status = LeaveRequestStatus.WITHDRAWN
    leave_request.save(update_fields=['status', 'modified_at'])
    from apps.approvals.models import ApprovalRun

    approval_run = ApprovalRun.objects.filter(
        content_type__app_label='timeoff',
        content_type__model='leaverequest',
        object_id=leave_request.id,
    ).first()
    if approval_run:
        cancel_approval_run(approval_run, actor=actor, subject_status=LeaveRequestStatus.WITHDRAWN)
    get_or_create_leave_balance(leave_request.employee, leave_request.leave_type)
    log_audit_event(actor, 'leave.request.withdrawn', organisation=leave_request.employee.organisation, target=leave_request)
    return leave_request


def upsert_on_duty_policy(organisation, actor=None, policy=None, **fields):
    with transaction.atomic():
        target_is_default = fields.get('is_default', policy.is_default if policy is not None else False)
        if target_is_default:
            OnDutyPolicy.objects.filter(organisation=organisation).exclude(id=getattr(policy, 'id', None)).update(is_default=False)
        if policy is None:
            policy = OnDutyPolicy.objects.create(organisation=organisation, created_by=actor, **fields)
        else:
            for attr, value in fields.items():
                setattr(policy, attr, value)
            policy.save()
    log_audit_event(actor, 'on_duty_policy.upserted', organisation=organisation, target=policy)
    return policy


def create_on_duty_request(employee, policy, start_date, end_date, duration_type, purpose, destination='', start_time=None, end_time=None, actor=None):
    if end_date < start_date:
        raise ValueError('End date cannot be before start date.')
    if duration_type == OnDutyDurationType.TIME_RANGE:
        if start_time is None or end_time is None:
            raise ValueError('Start and end time are required for time-range on-duty requests.')
        if start_time >= end_time:
            raise ValueError('Start time must be earlier than end time for time-range on-duty requests.')
    elif start_time is not None or end_time is not None:
        raise ValueError('Start and end time can only be provided for time-range on-duty requests.')
    total_units = Decimal('1.00')
    if duration_type in [DaySession.FIRST_HALF, DaySession.SECOND_HALF]:
        total_units = Decimal('0.50')
    request = OnDutyRequest.objects.create(
        employee=employee,
        policy=policy,
        start_date=start_date,
        end_date=end_date,
        duration_type=duration_type,
        start_time=start_time,
        end_time=end_time,
        total_units=total_units,
        purpose=purpose,
        destination=destination,
        status=OnDutyRequestStatus.PENDING,
    )
    create_approval_run(
        request,
        ApprovalRequestKind.ON_DUTY,
        requester=employee,
        actor=actor,
        subject_label=f'On Duty: {start_date.isoformat()}',
    )
    log_audit_event(actor or employee.user, 'on_duty.request.created', organisation=employee.organisation, target=request)
    return request


def withdraw_on_duty_request(on_duty_request, actor=None):
    if on_duty_request.status not in [OnDutyRequestStatus.PENDING, OnDutyRequestStatus.APPROVED]:
        raise ValueError('Only pending or approved on-duty requests can be withdrawn.')
    on_duty_request.status = OnDutyRequestStatus.WITHDRAWN
    on_duty_request.save(update_fields=['status', 'modified_at'])
    from apps.approvals.models import ApprovalRun

    approval_run = ApprovalRun.objects.filter(
        content_type__app_label='timeoff',
        content_type__model='ondutyrequest',
        object_id=on_duty_request.id,
    ).first()
    if approval_run:
        cancel_approval_run(approval_run, actor=actor, subject_status=OnDutyRequestStatus.WITHDRAWN)
    log_audit_event(actor, 'on_duty.request.withdrawn', organisation=on_duty_request.employee.organisation, target=on_duty_request)
    return on_duty_request


def create_holiday_calendar(organisation, actor=None, holidays=None, location_ids=None, **fields):
    with transaction.atomic():
        if fields.get('is_default'):
            HolidayCalendar.objects.filter(organisation=organisation, year=fields['year']).update(is_default=False)
        calendar_obj = HolidayCalendar.objects.create(organisation=organisation, created_by=actor, **fields)
        for holiday in holidays or []:
            Holiday.objects.create(holiday_calendar=calendar_obj, **holiday)
        for location_id in location_ids or []:
            HolidayCalendarLocation.objects.create(holiday_calendar=calendar_obj, office_location_id=location_id)
    log_audit_event(actor, 'holiday_calendar.created', organisation=organisation, target=calendar_obj)
    return calendar_obj


def update_holiday_calendar(calendar_obj, actor=None, holidays=None, location_ids=None, **fields):
    with transaction.atomic():
        target_is_default = fields.get('is_default', calendar_obj.is_default)
        target_year = fields.get('year', calendar_obj.year)
        if target_is_default:
            HolidayCalendar.objects.filter(organisation=calendar_obj.organisation, year=target_year).exclude(id=calendar_obj.id).update(is_default=False)
        for attr, value in fields.items():
            setattr(calendar_obj, attr, value)
        calendar_obj.save()
        if holidays is not None:
            keep_ids = []
            for holiday_payload in holidays:
                holiday_id = holiday_payload.pop('id', None)
                if holiday_id:
                    holiday = calendar_obj.holidays.get(id=holiday_id)
                    for attr, value in holiday_payload.items():
                        setattr(holiday, attr, value)
                    holiday.save()
                else:
                    holiday = Holiday.objects.create(holiday_calendar=calendar_obj, **holiday_payload)
                keep_ids.append(holiday.id)
            calendar_obj.holidays.exclude(id__in=keep_ids).delete()
        if location_ids is not None:
            calendar_obj.location_assignments.exclude(office_location_id__in=location_ids).delete()
            existing = set(calendar_obj.location_assignments.values_list('office_location_id', flat=True))
            for location_id in location_ids:
                if location_id not in existing:
                    HolidayCalendarLocation.objects.create(holiday_calendar=calendar_obj, office_location_id=location_id)
    log_audit_event(actor, 'holiday_calendar.updated', organisation=calendar_obj.organisation, target=calendar_obj)
    return calendar_obj


def publish_holiday_calendar(calendar_obj, actor=None):
    calendar_obj.status = HolidayCalendarStatus.PUBLISHED
    calendar_obj.published_at = timezone.now()
    calendar_obj.save(update_fields=['status', 'published_at', 'modified_at'])
    log_audit_event(actor, 'holiday_calendar.published', organisation=calendar_obj.organisation, target=calendar_obj)
    return calendar_obj


def get_employee_holiday_entries(employee, year, month):
    location_ids = [employee.office_location_id] if employee.office_location_id else []
    base_calendars = HolidayCalendar.objects.filter(
        organisation=employee.organisation,
        status=HolidayCalendarStatus.PUBLISHED,
        year=year,
    ).prefetch_related('holidays', 'location_assignments')
    calendars = []
    for calendar_obj in base_calendars:
        assigned_locations = set(calendar_obj.location_assignments.values_list('office_location_id', flat=True))
        if not assigned_locations or any(location_id in assigned_locations for location_id in location_ids):
            calendars.append(calendar_obj)
    first_day = date(year, month, 1)
    _, last_day_number = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_number)
    entries = []
    for calendar_obj in calendars:
        for holiday in calendar_obj.holidays.filter(holiday_date__gte=first_day, holiday_date__lte=last_day):
            entries.append(
                {
                    'date': holiday.holiday_date.isoformat(),
                    'kind': 'HOLIDAY',
                    'label': holiday.name,
                    'status': holiday.classification,
                    'color': '#f59e0b' if holiday.classification == 'RESTRICTED' else '#10b981',
                    'session': holiday.session,
                }
            )
    return entries


def get_employee_calendar_month(employee, calendar_month=None):
    if calendar_month:
        year, month = [int(part) for part in calendar_month.split('-')]
        month_anchor = date(year, month, 1)
    else:
        today = timezone.localdate()
        month_anchor = date(today.year, today.month, 1)

    year = month_anchor.year
    month = month_anchor.month
    _, days_in_month = calendar.monthrange(year, month)
    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month)

    day_map = {day: [] for day in range(1, days_in_month + 1)}
    for holiday in get_employee_holiday_entries(employee, year, month):
        day_map[int(holiday['date'].split('-')[2])].append(holiday)

    leave_requests = list_leave_requests_in_range(
        employee_id=employee.id,
        start_date=first_day,
        end_date=last_day,
    )
    for request in leave_requests:
        current = request.start_date
        while current <= request.end_date:
            if current.month == month and current.year == year:
                day_map[current.day].append(
                    {
                        'date': current.isoformat(),
                        'kind': 'LEAVE',
                        'label': request.leave_type.name,
                        'status': request.status,
                        'color': request.leave_type.color,
                        'session': request.start_session if request.start_date == request.end_date else DaySession.FULL_DAY,
                    }
                )
            current += timedelta(days=1)

    on_duty_requests = OnDutyRequest.objects.filter(
        employee=employee,
        start_date__lte=last_day,
        end_date__gte=first_day,
    )
    for request in on_duty_requests:
        current = request.start_date
        while current <= request.end_date:
            if current.month == month and current.year == year:
                day_map[current.day].append(
                    {
                        'date': current.isoformat(),
                        'kind': 'ON_DUTY',
                        'label': 'On Duty',
                        'status': request.status,
                        'color': '#6366f1',
                        'session': request.duration_type,
                    }
                )
            current += timedelta(days=1)

    days = [
        {
            'date': date(year, month, day).isoformat(),
            'entries': day_map[day],
        }
        for day in range(1, days_in_month + 1)
    ]
    return {'month': month_anchor.strftime('%Y-%m'), 'days': days}
