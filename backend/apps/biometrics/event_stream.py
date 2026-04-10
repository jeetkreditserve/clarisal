from __future__ import annotations

import json
import logging

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from apps.accounts.workspaces import get_active_admin_organisation

logger = logging.getLogger(__name__)

REDIS_AVAILABLE = False
try:
    import redis

    _redis_client = redis.Redis.from_url(
        "redis://localhost:6379/0",
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
        try:
            organisation = get_active_admin_organisation(request, request.user)
            if organisation is None:
                return HttpResponse("No active organisation", status=401)
        except ValueError:
            return HttpResponse("No active organisation", status=401)

        org_id = str(organisation.id)

        def event_stream():
            if not REDIS_AVAILABLE:
                yield _format_sse("error", {"message": "Event streaming unavailable"})
                return

            try:
                pubsub = _redis_client.pubsub()
                channels = [
                    f"attendance:punch:{org_id}",
                    f"biometric:health:{org_id}",
                    f"biometric:sync:{org_id}",
                ]
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
            finally:
                pubsub.unsubscribe(*channels)
                pubsub.close()

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
        try:
            organisation = get_active_admin_organisation(request, request.user)
            if organisation is None:
                return HttpResponse("No active organisation", status=401)
        except ValueError:
            return HttpResponse("No active organisation", status=401)

        org_id = str(organisation.id)

        def event_stream():
            if not REDIS_AVAILABLE:
                yield _format_sse("error", {"message": "Event streaming unavailable"})
                return

            try:
                pubsub = _redis_client.pubsub()
                channels = [
                    f"biometric:health:{org_id}",
                    f"biometric:sync:{org_id}",
                ]
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
            finally:
                pubsub.unsubscribe(*channels)
                pubsub.close()

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
