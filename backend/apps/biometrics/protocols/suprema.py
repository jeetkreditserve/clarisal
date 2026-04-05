from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

from django.utils import timezone

from apps.attendance.services import create_punch_from_source
from apps.biometrics.http import get as http_get
from apps.biometrics.http import post as http_post

_SESSION_CACHE: dict[tuple[str, str], str] = {}


def _get_session_id(server_url: str, login_id: str, password: str, timeout: int = 10) -> str:
    cache_key = (server_url, login_id)
    if cache_key in _SESSION_CACHE:
        return _SESSION_CACHE[cache_key]

    response = http_post(
        f'{server_url}/api/login',
        json_body={'User': {'login_id': login_id, 'password': password}},
        timeout=timeout,
        verify=False,
    )
    response.raise_for_status()
    session_id = (
        response.headers.get('bs-session-id')
        or response.cookies.get('bs-session-id')
        or response.cookies.get('BS-SESSION-ID')
    )
    if not session_id:
        raise ValueError('Suprema login succeeded but no session id was returned.')
    _SESSION_CACHE[cache_key] = session_id
    return cast(str, session_id)


def fetch_biostar_attendance(
    server_url: str,
    login_id: str,
    password: str,
    from_datetime: str,
    to_datetime: str | None = None,
    timeout: int = 20,
) -> list[dict]:
    session_id = _get_session_id(server_url, login_id, password)
    params = {'from_time': from_datetime}
    if to_datetime:
        params['to_time'] = to_datetime

    response = http_get(
        f'{server_url}/api/events',
        headers={'bs-session-id': session_id, 'Accept': 'application/json'},
        params=params,
        timeout=timeout,
        verify=False,
    )
    response.raise_for_status()

    rows = response.json().get('EventCollection', {}).get('rows', [])
    records = []
    for row in rows:
        try:
            punch_time = datetime.fromisoformat(row['datetime'])
        except (KeyError, ValueError):
            continue
        event_type = str(row.get('event_type_id', '1'))
        records.append(
            {
                'employee_code': str(row.get('user_id', '')).strip(),
                'punch_time': punch_time,
                'direction': 'OUT' if event_type == '2' else 'IN',
            }
        )
    return records


def sync_biostar_device(device, organisation_id: str) -> dict:
    since = device.last_sync_at or (timezone.now() - timedelta(days=1))
    password = device.get_oauth_client_secret()
    if not device.oauth_client_id or not password:
        raise ValueError('Suprema BioStar device is missing login credentials.')

    records = fetch_biostar_attendance(
        server_url=f'https://{device.ip_address}:{device.port}',
        login_id=device.oauth_client_id,
        password=password,
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
            metadata={'protocol': 'SUPREMA_BIOSTAR'},
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}
