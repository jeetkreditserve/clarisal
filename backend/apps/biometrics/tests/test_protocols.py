from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.attendance.models import AttendanceDay, AttendancePunch


@pytest.mark.django_db
def test_create_punch_from_source_creates_device_punch_and_attendance_day(biometric_setup):
    from apps.attendance.services import create_punch_from_source

    employee = biometric_setup['employee']
    organisation = biometric_setup['organisation']
    punch_time = timezone.make_aware(datetime(2026, 4, 5, 9, 5), ZoneInfo('Asia/Kolkata'))

    result = create_punch_from_source(
        employee_code='EMP100',
        punch_time=punch_time,
        organisation_id=str(organisation.id),
        direction='IN',
        source='DEVICE',
        device_id='SN-ADMS-001',
    )

    assert result['status'] == 'created'
    punch = AttendancePunch.objects.get(employee=employee)
    assert punch.source == 'DEVICE'
    assert punch.metadata['device_id'] == 'SN-ADMS-001'
    assert AttendanceDay.objects.get(employee=employee, attendance_date=date(2026, 4, 5)).raw_punch_count == 1


@pytest.mark.django_db
def test_create_punch_from_source_skips_duplicate_within_one_minute(biometric_setup):
    from apps.attendance.services import create_punch_from_source

    organisation = biometric_setup['organisation']
    punch_time = timezone.make_aware(datetime(2026, 4, 5, 9, 5), ZoneInfo('Asia/Kolkata'))

    first = create_punch_from_source(
        employee_code='EMP100',
        punch_time=punch_time,
        organisation_id=str(organisation.id),
        direction='IN',
        source='DEVICE',
        device_id='SN-ADMS-001',
    )
    second = create_punch_from_source(
        employee_code='EMP100',
        punch_time=punch_time + timedelta(seconds=30),
        organisation_id=str(organisation.id),
        direction='IN',
        source='DEVICE',
        device_id='SN-ADMS-001',
    )

    assert first['status'] == 'created'
    assert second['status'] == 'skipped'
    assert AttendancePunch.objects.count() == 1


@pytest.mark.django_db
def test_parse_attlog_line_returns_correct_fields():
    from apps.biometrics.protocols.adms import parse_attlog_line

    result = parse_attlog_line('1001\t2024-04-01 09:05:00\t0\t1\t0')

    assert result == {
        'pin': '1001',
        'datetime_str': '2024-04-01 09:05:00',
        'status': '0',
        'verify': '1',
        'work_code': '0',
    }


@pytest.mark.django_db
def test_parse_attlog_line_ignores_malformed():
    from apps.biometrics.protocols.adms import parse_attlog_line

    assert parse_attlog_line('malformed line') is None


@pytest.mark.django_db
def test_handle_adms_push_processes_valid_records(biometric_setup):
    from apps.biometrics.protocols.adms import handle_adms_push

    organisation = biometric_setup['organisation']
    body = 'EMP100\t2026-04-05 09:05:00\t0\t1\t0\nEMP100\t2026-04-05 18:10:00\t1\t1\t0'

    result = handle_adms_push(
        body=body,
        organisation_id=str(organisation.id),
        device_serial='SN-ADMS-001',
    )

    assert result['processed'] == 2
    assert result['skipped'] == 0
    assert result['errors'] == []
    assert AttendancePunch.objects.count() == 2


class TestMatrixCosecProtocol:
    def test_fetch_attendance_parses_records(self):
        from apps.biometrics.protocols.matrix_cosec import fetch_cosec_attendance

        with patch('apps.biometrics.protocols.matrix_cosec.http_get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'response': {
                    'data': [
                        {
                            'userID': '1001',
                            'dateTime': '2024-04-01T09:05:00',
                            'eventType': 'DOOR_OPEN',
                            'direction': 'IN',
                        }
                    ]
                }
            }
            records = fetch_cosec_attendance(
                device_ip='192.168.1.100',
                port=80,
                api_key='test-key',
                from_datetime='2024-04-01T00:00:00',
            )

        assert len(records) == 1
        assert records[0]['employee_code'] == '1001'
        assert records[0]['direction'] == 'IN'


class TestSupremaProtocol:
    def test_fetch_suprema_attendance_uses_session_login(self):
        from apps.biometrics.protocols.suprema import fetch_biostar_attendance

        with patch('apps.biometrics.protocols.suprema.http_post') as mock_post, patch('apps.biometrics.protocols.suprema.http_get') as mock_get:
            mock_post.return_value.status_code = 200
            mock_post.return_value.headers = {'bs-session-id': 'session-123'}
            mock_post.return_value.json.return_value = {'ok': True}
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'EventCollection': {
                    'rows': [
                        {
                            'user_id': '1001',
                            'datetime': '2024-04-01T09:05:00+05:30',
                            'event_type_id': '2',
                        }
                    ]
                }
            }
            records = fetch_biostar_attendance(
                server_url='https://biostar.example.com',
                login_id='api-user',
                password='secret',
                from_datetime='2024-04-01T00:00:00',
            )

        assert len(records) == 1
        assert records[0]['employee_code'] == '1001'
        assert records[0]['direction'] == 'OUT'
        assert mock_post.called
        assert mock_get.call_args.kwargs['headers']['bs-session-id'] == 'session-123'


class TestHikVisionProtocol:
    def test_fetch_hikvision_events(self):
        from apps.biometrics.protocols.hikvision import fetch_hikvision_events

        with patch('apps.biometrics.protocols.hikvision.http_get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'AcsEvent': {
                    'InfoList': [
                        {
                            'employeeNoString': '1001',
                            'time': '2024-04-01T09:05:00+05:30',
                            'major': 5,
                            'minor': 75,
                            'serialNo': 1,
                        }
                    ]
                }
            }
            records = fetch_hikvision_events(
                device_ip='192.168.1.200',
                port=80,
                username='admin',
                password='hikvision123',
            )

        assert len(records) == 1
        assert records[0]['employee_code'] == '1001'
        assert records[0]['direction'] == 'IN'


class TestEsslEbioserverProtocol:
    def test_parse_essl_payload_normalizes_transactions(self):
        from apps.biometrics.protocols.essl_ebioserver import parse_essl_ebioserver_payload

        records = parse_essl_ebioserver_payload(
            {
                'transactions': [
                    {
                        'EnrollNo': '1001',
                        'PunchTime': '2026-04-05T09:05:00+05:30',
                        'Direction': 'in',
                    },
                    {
                        'EnrollNo': '1001',
                        'PunchTime': '2026-04-05T18:01:00+05:30',
                        'Direction': 'unknown',
                    },
                ]
            }
        )

        assert len(records) == 2
        assert records[0]['employee_code'] == '1001'
        assert records[0]['direction'] == 'IN'
        assert records[1]['direction'] == 'RAW'

    def test_parse_essl_payload_normalizes_realtime_payload(self):
        from apps.biometrics.protocols.essl_ebioserver import parse_essl_ebioserver_payload

        records = parse_essl_ebioserver_payload(
            {
                'RealTime': {
                    'OperationID': 'op-1',
                    'SerialNumber': 'DESX12345678',
                    'PunchLog': {
                        'Type': 'CheckIn',
                        'UserId': 'EMP100',
                        'LogTime': '2026-04-05 09:05:00',
                    },
                    'AuthToken': 'token-123',
                }
            }
        )

        assert len(records) == 1
        assert records[0]['employee_code'] == 'EMP100'
        assert records[0]['direction'] == 'IN'
        assert records[0]['metadata']['serial_number'] == 'DESX12345678'
