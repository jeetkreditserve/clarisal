from celery import shared_task
from django.core.cache import cache

from .services import expire_stale_notices, publish_scheduled_notices

NOTICE_TASK_LOCK_TTL = 240


def _run_with_lock(lock_key, callback):
    if not cache.add(lock_key, '1', NOTICE_TASK_LOCK_TTL):
        return 0
    try:
        return callback()
    finally:
        cache.delete(lock_key)


@shared_task(name='communications.publish_scheduled_notices')
def publish_scheduled_notices_task():
    return _run_with_lock('communications:publish_scheduled_notices', publish_scheduled_notices)


@shared_task(name='communications.expire_stale_notices')
def expire_stale_notices_task():
    return _run_with_lock('communications:expire_stale_notices', expire_stale_notices)
