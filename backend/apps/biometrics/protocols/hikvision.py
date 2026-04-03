from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.attendance.services import create_punch_from_source
from apps.biometrics.http import HTTPDigestAuth, RequestException, get as http_get


def fetch_hikvision_events(
    device_ip: str,
    port: int,
    username: str,
    password: str,
    start_time: str | None = None,
    max_results: int = 200,
    timeout: int = 15,
) -> list[dict]:
    params = {
        'format': 'json',
        'searchResultPosition': 0,
        'maxResults': max_results,
    }
    if start_time:
        params['startTime'] = start_time

    try:
        response = http_get(
            f'http://{device_ip}:{port}/ISAPI/AccessControl/AcsEvent',
            auth=HTTPDigestAuth(username, password),
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except RequestException as exc:
        raise ConnectionError(f'HikVision device unreachable at {device_ip}:{port}: {exc}') from exc

    records = []
    for event in response.json().get('AcsEvent', {}).get('InfoList', []):
        try:
            punch_time = datetime.fromisoformat(event['time'])
        except (KeyError, ValueError):
            continue
        employee_code = str(event.get('employeeNoString') or event.get('employeeNo') or '').strip()
        if not employee_code:
            continue
        minor_code = int(event.get('minor', 75))
        records.append(
            {
                'employee_code': employee_code,
                'punch_time': punch_time,
                'direction': 'OUT' if minor_code in {76, 77} else 'IN',
            }
        )
    return records


def sync_hikvision_device(device, organisation_id: str) -> dict:
    since = device.last_sync_at or (timezone.now() - timedelta(days=1))
    password = device.get_api_key()
    if not device.auth_username or not password:
        raise ValueError('HikVision device is missing digest credentials.')

    records = fetch_hikvision_events(
        device_ip=device.ip_address,
        port=device.port,
        username=device.auth_username,
        password=password,
        start_time=since.isoformat(),
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
            metadata={'protocol': 'HIKVISION_ISAPI'},
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
