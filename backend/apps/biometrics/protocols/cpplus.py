from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from apps.attendance.services import create_punch_from_source

POSSIBLE_EMPLOYEE_KEYS = (
    "employee_code",
    "employeeCode",
    "emp_code",
    "EnrollNo",
    "enrollNo",
    "UserId",
    "userId",
    "card_no",
    "cardNumber",
)
POSSIBLE_TIME_KEYS = (
    "punch_time",
    "punchTime",
    "PunchTime",
    "datetime",
    "date_time",
    "time",
    "timestamp",
    "log_time",
    "LogTime",
)
POSSIBLE_DIRECTION_KEYS = (
    "direction",
    "Direction",
    "status",
    "Status",
    "type",
    "Type",
    "event",
    "Event",
)


def _first_value(payload: dict, keys: tuple[str, ...]):
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for transform in (
        lambda item: datetime.fromisoformat(item),
        lambda item: datetime.fromisoformat(item.replace("Z", "+00:00")),
        lambda item: datetime.strptime(item, "%Y-%m-%d %H:%M:%S"),
        lambda item: datetime.strptime(item, "%d/%m/%Y %H:%M:%S"),
        lambda item: datetime.strptime(item, "%Y-%m-%dT%H:%M:%S"),
        lambda item: datetime.strptime(item, "%d-%m-%Y %H:%M:%S"),
    ):
        try:
            return transform(text)
        except ValueError:
            continue
    return None


def _normalize_direction(value) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"IN", "CHECK_IN", "CHECKIN", "0", "ENTRY"}:
        return "IN"
    if normalized in {"OUT", "CHECK_OUT", "CHECKOUT", "1", "EXIT"}:
        return "OUT"
    return "RAW"


def parse_cpplus_payload(payload) -> list[dict]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        data = payload.get("data", payload.get("attendance", payload.get("records", payload.get("events", []))))
        if isinstance(data, list):
            records = data
        else:
            records = [payload]
    else:
        return []

    normalized = []
    for item in records:
        if not isinstance(item, dict):
            continue
        employee_code = _first_value(item, POSSIBLE_EMPLOYEE_KEYS)
        punch_time = _parse_datetime(_first_value(item, POSSIBLE_TIME_KEYS))
        if not employee_code or punch_time is None:
            continue
        normalized.append(
            {
                "employee_code": str(employee_code).strip(),
                "punch_time": punch_time,
                "direction": _normalize_direction(_first_value(item, POSSIBLE_DIRECTION_KEYS)),
                "metadata": {
                    "raw_event": item,
                    "protocol": "CP_PLUS_EXPORT",
                    "source": "CP_PLUS",
                },
            }
        )
    return normalized


def handle_cpplus_export(
    payload,
    organisation_id: str,
    device_id: str,
) -> dict:
    records = parse_cpplus_payload(payload)
    processed = 0
    skipped = 0
    errors: list[str] = []

    for record in records:
        punch_time = record["punch_time"]
        if timezone.is_naive(punch_time):
            punch_time = timezone.make_aware(punch_time, timezone.get_default_timezone())

        result = create_punch_from_source(
            employee_code=record["employee_code"],
            punch_time=punch_time,
            organisation_id=organisation_id,
            direction=record["direction"],
            source="DEVICE",
            device_id=device_id,
            metadata=record["metadata"],
        )
        if result["status"] == "created":
            processed += 1
        elif result["status"] == "error":
            errors.append(result["reason"])
        else:
            skipped += 1

    return {"processed": processed, "skipped": skipped, "errors": errors}


def parse_csv_export(csv_content: str, delimiter: str = ",") -> list[dict]:
    lines = [line.strip() for line in csv_content.strip().splitlines() if line.strip()]
    if not lines:
        return []

    header_line = lines[0]
    if delimiter in header_line:
        headers = [h.strip().lower().replace(" ", "_") for h in header_line.split(delimiter)]
    else:
        headers = ["employee_code", "punch_time", "direction"]

    records = []
    for line in lines[1:]:
        if delimiter in line:
            values = [v.strip() for v in line.split(delimiter)]
        else:
            continue

        row = dict(zip(headers, values, strict=False))
        employee_code = _first_value(row, POSSIBLE_EMPLOYEE_KEYS)
        punch_time = _parse_datetime(_first_value(row, POSSIBLE_TIME_KEYS))
        if not employee_code or punch_time is None:
            continue
        records.append(
            {
                "employee_code": str(employee_code).strip(),
                "punch_time": punch_time,
                "direction": _normalize_direction(row.get("direction", "")),
                "metadata": {
                    "raw_csv_row": row,
                    "protocol": "CP_PLUS_EXPORT",
                    "source": "CSV_EXPORT",
                },
            }
        )
    return records
