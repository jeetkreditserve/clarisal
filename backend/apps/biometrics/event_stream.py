from __future__ import annotations

import json
import logging
from typing import Any, cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from apps.accounts.models import User
from apps.accounts.workspaces import get_active_admin_organisation

logger = logging.getLogger(__name__)

REDIS_AVAILABLE = False
_redis_client: Any = None


def _redis_url() -> str:
    return getattr(settings, "REDIS_URL", "redis://localhost:6379/0")


try:
    import redis

    _redis_client = redis.Redis.from_url(
        _redis_url(),
        decode_responses=True,
    )
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:  # noqa: BLE001
    _redis_client = None


def _format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@method_decorator(csrf_exempt, name="dispatch")
class AttendanceEventStreamView(View):
    def get(self, request: HttpRequest):
        if not getattr(request.user, "is_authenticated", False):
            return HttpResponse("Authentication required", status=401)
        user = cast(User, request.user)
        try:
            organisation = get_active_admin_organisation(request, user)
            if organisation is None:
                return HttpResponse("No active organisation", status=401)
        except ValueError:
            return HttpResponse("No active organisation", status=401)

        org_id = str(organisation.id)

        def event_stream():
            if not REDIS_AVAILABLE:
                yield _format_sse("error", {"message": "Event streaming unavailable"})
                return

            pubsub = None
            channels = [
                f"attendance:punch:{org_id}",
                f"biometric:health:{org_id}",
                f"biometric:sync:{org_id}",
            ]
            try:
                pubsub = _redis_client.pubsub()
                pubsub.subscribe(*channels)

                yield _format_sse(
                    "connected",
                    {
                        "organisation_id": org_id,
                        "channels": channels,
                    },
                )

                for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            payload = json.loads(message["data"])
                            event_type = payload.get("type", "unknown")
                            yield _format_sse(event_type, payload)
                        except json.JSONDecodeError:
                            yield _format_sse("raw", {"data": message["data"]})

            except GeneratorExit:
                pass
            except Exception:  # noqa: BLE001
                logger.exception("Attendance event stream failed")
                yield _format_sse("error", {"message": "Event streaming unavailable"})
            finally:
                if pubsub is not None:
                    try:
                        pubsub.unsubscribe(*channels)
                        pubsub.close()
                    except Exception:  # noqa: BLE001
                        logger.debug("Attendance event stream pubsub cleanup failed", exc_info=True)

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


@method_decorator(csrf_exempt, name="dispatch")
class DeviceEventStreamView(View):
    def get(self, request: HttpRequest, device_id: str):
        if not getattr(request.user, "is_authenticated", False):
            return HttpResponse("Authentication required", status=401)
        user = cast(User, request.user)
        try:
            organisation = get_active_admin_organisation(request, user)
            if organisation is None:
                return HttpResponse("No active organisation", status=401)
        except ValueError:
            return HttpResponse("No active organisation", status=401)

        org_id = str(organisation.id)

        def event_stream():
            if not REDIS_AVAILABLE:
                yield _format_sse("error", {"message": "Event streaming unavailable"})
                return

            pubsub = None
            channels = [
                f"biometric:health:{org_id}",
                f"biometric:sync:{org_id}",
            ]
            try:
                pubsub = _redis_client.pubsub()
                pubsub.subscribe(*channels)

                yield _format_sse(
                    "connected",
                    {
                        "organisation_id": org_id,
                        "device_id": device_id,
                        "channels": channels,
                    },
                )

                for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            payload = json.loads(message["data"])
                            if device_id and payload.get("payload", {}).get("device_id") != device_id:
                                continue
                            event_type = payload.get("type", "unknown")
                            yield _format_sse(event_type, payload)
                        except json.JSONDecodeError:
                            yield _format_sse("raw", {"data": message["data"]})

            except GeneratorExit:
                pass
            except Exception:  # noqa: BLE001
                logger.exception("Device event stream failed")
                yield _format_sse("error", {"message": "Event streaming unavailable"})
            finally:
                if pubsub is not None:
                    try:
                        pubsub.unsubscribe(*channels)
                        pubsub.close()
                    except Exception:  # noqa: BLE001
                        logger.debug("Device event stream pubsub cleanup failed", exc_info=True)

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
