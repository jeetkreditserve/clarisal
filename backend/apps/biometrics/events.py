from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

REDIS_AVAILABLE = False
try:
    import redis

    _redis_client = redis.Redis.from_url(
        getattr(settings, "REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:  # noqa: BLE001
    _redis_client = None


class EventChannel:
    ATTENDANCE_PUNCH = "attendance:punch"
    DEVICE_HEALTH = "biometric:health"
    DEVICE_SYNC = "biometric:sync"


def _get_channel_name(channel: str, org_id: str) -> str:
    return f"{channel}:{org_id}"


def publish_event(
    channel: str,
    event_type: str,
    org_id: str,
    payload: dict[str, Any],
) -> bool:
    if not REDIS_AVAILABLE:
        logger.debug("Redis not available, skipping event publish: %s", event_type)
        return False

    try:
        message = json.dumps(
            {
                "type": event_type,
                "organisation_id": org_id,
                "timestamp": timezone.now().isoformat(),
                "payload": payload,
            }
        )
        _redis_client.publish(_get_channel_name(channel, org_id), message)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to publish event: %s", event_type)
        return False


def publish_punch_event(
    organisation_id: str,
    punch_id: str,
    employee_code: str,
    direction: str,
    punch_time: str,
    device_id: str | None = None,
    source: str = "DEVICE",
) -> bool:
    return publish_event(
        channel=EventChannel.ATTENDANCE_PUNCH,
        event_type="punch_created",
        org_id=organisation_id,
        payload={
            "punch_id": punch_id,
            "employee_code": employee_code,
            "direction": direction,
            "punch_time": punch_time,
            "device_id": device_id,
            "source": source,
        },
    )


def publish_device_health_event(
    organisation_id: str,
    device_id: str,
    device_name: str,
    health_status: str,
    last_sync_at: str | None = None,
    error_message: str | None = None,
) -> bool:
    return publish_event(
        channel=EventChannel.DEVICE_HEALTH,
        event_type="device_health_update",
        org_id=organisation_id,
        payload={
            "device_id": device_id,
            "device_name": device_name,
            "health_status": health_status,
            "last_sync_at": last_sync_at,
            "error_message": error_message,
        },
    )


def publish_device_sync_event(
    organisation_id: str,
    device_id: str,
    device_name: str,
    records_processed: int,
    records_skipped: int,
    success: bool,
    errors: list[str] | None = None,
) -> bool:
    return publish_event(
        channel=EventChannel.DEVICE_SYNC,
        event_type="device_sync_complete",
        org_id=organisation_id,
        payload={
            "device_id": device_id,
            "device_name": device_name,
            "records_processed": records_processed,
            "records_skipped": records_skipped,
            "success": success,
            "errors": errors or [],
        },
    )


def is_event_streaming_available() -> bool:
    return REDIS_AVAILABLE
