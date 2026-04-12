from celery import shared_task
from django.utils import timezone


@shared_task(name="timeoff.run_leave_lapse_for_all_active_cycles")
def run_leave_lapse_for_all_active_cycles():
    """Expire unused leave for all active leave balances whose cycle has ended,
    and enforce capped carry-forward rules where configured."""
    from apps.timeoff import services as timeoff_services
    from apps.timeoff.models import CarryForwardMode, LeaveBalance

    today = timezone.localdate()

    # Find all active employees' leave balances where:
    # - the cycle has ended (cycle_end < today)
    # - the leave type has carry_forward_mode = NONE
    ended_balances = LeaveBalance.objects.filter(
        cycle_end__lt=today,
        leave_type__carry_forward_mode=CarryForwardMode.NONE,
        employee__status="ACTIVE",
    ).select_related('employee', 'leave_type')

    for balance in ended_balances:
        timeoff_services.process_cycle_end_lapse(balance.employee, balance)

    capped_balances = LeaveBalance.objects.filter(
        cycle_end__lt=today,
        leave_type__carry_forward_mode=CarryForwardMode.CAPPED,
        employee__status="ACTIVE",
    ).select_related('employee', 'leave_type', 'leave_type__leave_plan__leave_cycle')

    for balance in capped_balances:
        timeoff_services.process_cycle_end_cap(balance.employee, balance)
