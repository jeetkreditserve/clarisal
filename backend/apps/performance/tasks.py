from datetime import date, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model

from apps.employees.models import Employee, EmployeeStatus

from .models import AppraisalCycle
from .services import auto_advance_review_cycles as auto_advance_review_cycles_service
from .services import schedule_probation_review


@shared_task(name='performance.auto_schedule_probation_reviews')
def auto_schedule_probation_reviews():
    user_model = get_user_model()
    system_user = user_model.objects.filter(is_superuser=True).first()
    if system_user is None:
        return {'status': 'ERROR', 'reason': 'No superuser found for system actor'}

    target_date = date.today() + timedelta(days=7)
    candidates = Employee.objects.filter(
        status=EmployeeStatus.ACTIVE,
        probation_end_date=target_date,
    ).select_related('organisation', 'user', 'reporting_to__user')

    scheduled = 0
    for employee in candidates:
        already_exists = AppraisalCycle.objects.filter(
            organisation=employee.organisation,
            is_probation_review=True,
            reviews__employee=employee,
        ).exists()
        if already_exists:
            continue
        schedule_probation_review(employee, actor=system_user)
        scheduled += 1

    return {'status': 'OK', 'scheduled': scheduled}


@shared_task(name='performance.auto_advance_review_cycles')
def auto_advance_review_cycles():
    user_model = get_user_model()
    system_user = user_model.objects.filter(is_superuser=True).first()
    if system_user is None:
        return {'status': 'ERROR', 'reason': 'No superuser found for system actor'}
    return auto_advance_review_cycles_service(actor=system_user)
