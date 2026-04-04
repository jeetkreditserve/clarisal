from celery import shared_task
from django.core.cache import cache

from .services import process_pending_action_escalations, send_pending_action_reminders

APPROVAL_TASK_LOCK_TTL = 540


def _run_with_lock(lock_key, callback):
    if not cache.add(lock_key, '1', APPROVAL_TASK_LOCK_TTL):
        return 0
    try:
        return callback()
    finally:
        cache.delete(lock_key)


@shared_task(name='approvals.send_pending_action_reminders')
def send_pending_action_reminders_task():
    return _run_with_lock('approvals:send_pending_action_reminders', send_pending_action_reminders)


@shared_task(name='approvals.process_pending_action_escalations')
def process_pending_action_escalations_task():
    return _run_with_lock('approvals:process_pending_action_escalations', process_pending_action_escalations)
