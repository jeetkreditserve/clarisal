from __future__ import annotations

import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache

from .models import PayrollRun
from .services import calculate_pay_run

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(bind=True, name='payroll.calculate_pay_run', autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def calculate_pay_run_task(self, pay_run_id: str, actor_user_id: str) -> dict:
    lock_key = f'payroll:calc:lock:{pay_run_id}'
    # cache.add returns True only if the key did NOT already exist (atomic)
    if not cache.add(lock_key, self.request.id, timeout=1800):
        logger.info(
            'Payroll calculation already in progress — skipping duplicate delivery',
            extra={'pay_run_id': pay_run_id},
        )
        return {'status': 'SKIPPED', 'reason': 'duplicate_delivery', 'pay_run_id': pay_run_id}

    try:
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
    finally:
        cache.delete(lock_key)
