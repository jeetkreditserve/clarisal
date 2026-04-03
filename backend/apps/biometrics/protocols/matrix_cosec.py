from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.attendance.services import create_punch_from_source
from apps.biometrics.http import RequestError
from apps.biometrics.http import get as http_get


def fetch_cosec_attendance(
    device_ip: str,
    port: int,
    api_key: str,
    from_datetime: str,
    to_datetime: str | None = None,
    timeout: int = 15,
) -> list[dict]:
    url = f'http://{device_ip}:{port}/api/v1/monitoring/attendance'
    params = {'fromDate': from_datetime}
    if to_datetime:
        params['toDate'] = to_datetime

    try:
        response = http_get(
            url,
            headers={'X-API-Key': api_key, 'Accept': 'application/json'},
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except RequestError as exc:
        raise ConnectionError(f'COSEC device unreachable at {device_ip}:{port}: {exc}') from exc

    records = []
    for item in response.json().get('response', {}).get('data', []):
        try:
            punch_time = datetime.fromisoformat(item['dateTime'])
        except (KeyError, ValueError):
            continue
        records.append(
            {
                'employee_code': str(item.get('userID', '')).strip(),
                'punch_time': punch_time,
                'direction': 'OUT' if str(item.get('direction', 'IN')).upper() == 'OUT' else 'IN',
            }
        )
    return records


def sync_cosec_device(device, organisation_id: str) -> dict:
    since = device.last_sync_at or (timezone.now() - timedelta(days=1))
    api_key = device.get_api_key()
    if not api_key:
        raise ValueError('Matrix COSEC device is missing an API key.')

    records = fetch_cosec_attendance(
        device_ip=device.ip_address,
        port=device.port,
        api_key=api_key,
        from_datetime=since.isoformat(),
    )

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
            device_id=str(device.id),
            metadata={'protocol': 'MATRIX_COSEC'},
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
