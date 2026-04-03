from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from apps.attendance.services import create_punch_from_source


def parse_attlog_line(line: str) -> dict | None:
    parts = [part.strip() for part in line.strip().split('\t')]
    if len(parts) < 5:
        return None
    return {
        'pin': parts[0],
        'datetime_str': parts[1],
        'status': parts[2],
        'verify': parts[3],
        'work_code': parts[4],
    }


def parse_punch_direction(status: str) -> str:
    return 'OUT' if str(status).strip() in {'1', '5'} else 'IN'


def handle_adms_push(body: str, organisation_id: str, device_serial: str) -> dict:
    lines = [line for line in body.strip().splitlines() if line.strip()]
    processed = 0
    skipped = 0
    errors: list[str] = []

    for line in lines:
        parsed = parse_attlog_line(line)
        if not parsed:
            skipped += 1
            continue
        try:
            punch_dt = timezone.make_aware(
                datetime.strptime(parsed['datetime_str'], '%Y-%m-%d %H:%M:%S'),
                timezone.get_default_timezone(),
            )
        except ValueError:
            errors.append(f'Bad datetime: {parsed["datetime_str"]}')
            continue

        result = create_punch_from_source(
            employee_code=parsed['pin'],
            punch_time=punch_dt,
            organisation_id=organisation_id,
            direction=parse_punch_direction(parsed['status']),
            source='DEVICE',
            device_id=device_serial,
            metadata={
                'protocol': 'ZK_ADMS',
                'verify': parsed['verify'],
                'work_code': parsed['work_code'],
                'status_code': parsed['status'],
            },
        )
        if result['status'] == 'created':
            processed += 1
        else:
            skipped += 1

    return {'processed': processed, 'skipped': skipped, 'errors': errors}

