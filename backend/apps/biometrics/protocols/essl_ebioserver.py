from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from apps.attendance.services import create_punch_from_source

POSSIBLE_EVENT_LIST_KEYS = ('transactions', 'logs', 'events', 'rows', 'data')
POSSIBLE_EMPLOYEE_KEYS = ('employee_code', 'employeeCode', 'EnrollNo', 'enrollNo', 'EmployeeCode', 'emp_code', 'UserId', 'userId')
POSSIBLE_TIME_KEYS = ('punch_time', 'punchTime', 'PunchTime', 'datetime', 'dateTime', 'log_time', 'logTime', 'TransactionTime', 'LogTime')
POSSIBLE_DIRECTION_KEYS = ('direction', 'Direction', 'status', 'Status', 'punch_state', 'punchState', 'state', 'Type', 'type')


def _first_value(payload: dict, keys: tuple[str, ...]):
    for key in keys:
        value = payload.get(key)
        if value not in (None, ''):
            return value
    return None


def _normalize_direction(value) -> str:
    normalized = str(value or '').strip().upper()
    if normalized in {'IN', 'CHECK_IN', 'CHECKIN', '0', 'ENTRY'}:
        return 'IN'
    if normalized in {'OUT', 'CHECK_OUT', 'CHECKOUT', '1', 'EXIT'}:
        return 'OUT'
    return 'RAW'


def _parse_datetime(value) -> datetime | None:
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for transform in (
        lambda item: datetime.fromisoformat(item),
        lambda item: datetime.strptime(item, '%Y-%m-%d %H:%M:%S'),
        lambda item: datetime.strptime(item, '%d/%m/%Y %H:%M:%S'),
    ):
        try:
            return transform(text)
        except ValueError:
            continue
    return None


def parse_essl_ebioserver_payload(payload) -> list[dict]:
    if isinstance(payload, list):
        event_items = payload
    elif isinstance(payload, dict):
        realtime_payload = payload.get('RealTime')
        if isinstance(realtime_payload, dict) and isinstance(realtime_payload.get('PunchLog'), dict):
            event_items = [
                {
                    **realtime_payload['PunchLog'],
                    'serial_number': realtime_payload.get('SerialNumber', ''),
                    'operation_id': realtime_payload.get('OperationID', ''),
                }
            ]
        else:
            event_items = None
            for key in POSSIBLE_EVENT_LIST_KEYS:
                value = payload.get(key)
                if isinstance(value, list):
                    event_items = value
                    break
        if event_items is None:
            event_items = [payload]
    else:
        return []

    normalized = []
    for item in event_items:
        if not isinstance(item, dict):
            continue
        employee_code = _first_value(item, POSSIBLE_EMPLOYEE_KEYS)
        punch_time = _parse_datetime(_first_value(item, POSSIBLE_TIME_KEYS))
        if not employee_code or punch_time is None:
            continue
        normalized.append(
            {
                'employee_code': str(employee_code).strip(),
                'punch_time': punch_time,
                'direction': _normalize_direction(_first_value(item, POSSIBLE_DIRECTION_KEYS)),
                'metadata': {
                    'raw_event': item,
                    'protocol': 'ESSL_EBIOSERVER',
                    'serial_number': item.get('serial_number', ''),
                    'operation_id': item.get('operation_id', ''),
                },
            }
        )
    return normalized


def handle_essl_ebioserver_push(payload, organisation_id: str, device_id: str) -> dict:
    records = parse_essl_ebioserver_payload(payload)
    processed = 0
    skipped = 0
    errors: list[str] = []

    for record in records:
        punch_time = record['punch_time']
        if timezone.is_naive(punch_time):
            punch_time = timezone.make_aware(punch_time, timezone.get_default_timezone())
        result = create_punch_from_source(
            employee_code=record['employee_code'],
            punch_time=punch_time,
            organisation_id=organisation_id,
            direction=record['direction'],
            source='DEVICE',
            device_id=device_id,
            metadata=record['metadata'],
        )
        if result['status'] == 'created':
            processed += 1
        elif result['status'] == 'error':
            errors.append(result['reason'])
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
