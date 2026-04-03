from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from .models import PayrollRun
from .services import calculate_pay_run

User = get_user_model()


@shared_task(bind=True, name='payroll.calculate_pay_run', autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def calculate_pay_run_task(self, pay_run_id: str, actor_user_id: str) -> dict:
    try:
        pay_run = PayrollRun.objects.get(id=pay_run_id)
    except PayrollRun.DoesNotExist:
        return {'status': 'ERROR', 'error': f'PayrollRun {pay_run_id} not found'}

    try:
        actor = User.objects.get(id=actor_user_id)
    except User.DoesNotExist:
        return {'status': 'ERROR', 'error': f'User {actor_user_id} not found'}

    calculate_pay_run(pay_run, actor=actor)
    return {'status': 'SUCCESS', 'pay_run_id': pay_run_id}
