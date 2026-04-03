from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from .models import LeaveBalance, LeaveEncashmentRequest, LeaveRequest

ZERO = Decimal('0.00')


def get_leave_balance_record(*, employee_id, leave_type_id, cycle_start, cycle_end):
    return LeaveBalance.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
    ).first()


def get_leave_request_total_units(*, employee_id, leave_type_id, status, cycle_start, cycle_end) -> Decimal:
    total = LeaveRequest.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        status=status,
        start_date__gte=cycle_start,
        end_date__lte=cycle_end,
    ).aggregate(total=Sum('total_units'))['total']
    return total or ZERO


def list_overlapping_leave_requests(*, employee_id, start_date, end_date):
    return LeaveRequest.objects.filter(
        employee_id=employee_id,
        status__in=['PENDING', 'APPROVED'],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )


def get_total_days_to_encash(*, employee_id, leave_type_id, cycle_start, cycle_end, statuses) -> Decimal:
    total = LeaveEncashmentRequest.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        status__in=statuses,
    ).aggregate(total=Sum('days_to_encash'))['total']
    return total or ZERO


def list_leave_requests_in_range(*, employee_id, start_date, end_date):
    return LeaveRequest.objects.filter(
        employee_id=employee_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).select_related('leave_type')
