
import pytest


@pytest.mark.django_db
def test_org_admin_can_create_list_and_deactivate_biometric_device(biometric_setup):
    client = biometric_setup['client']

    create_response = client.post(
        '/api/org/biometrics/devices/',
        {
            'name': 'HQ Main Gate',
            'device_serial': 'SN-ADMS-001',
            'protocol': 'ZK_ADMS',
            'is_active': True,
        },
        format='json',
    )

    assert create_response.status_code == 201
    device_id = create_response.data['id']

    list_response = client.get('/api/org/biometrics/devices/')
    delete_response = client.delete(f'/api/org/biometrics/devices/{device_id}/')
    detail_response = client.get('/api/org/biometrics/devices/')

    assert list_response.status_code == 200
    assert len(list_response.data) == 1
    assert delete_response.status_code == 204
    assert detail_response.data[0]['is_active'] is False


@pytest.mark.django_db
def test_adms_endpoint_processes_attlog_and_writes_sync_log(biometric_setup):
    from apps.biometrics.models import BiometricDevice, BiometricSyncLog

    organisation = biometric_setup['organisation']
    employee = biometric_setup['employee']
    anonymous_client = biometric_setup['anonymous_client']
    BiometricDevice.objects.create(
        organisation=organisation,
        name='HQ ADMS',
        device_serial='SN-ADMS-001',
        protocol='ZK_ADMS',
        is_active=True,
    )

    body = 'EMP100\t2026-04-05 09:05:00\t0\t1\t0'
    response = anonymous_client.post(
        '/api/biometric/adms/iclock/cdata?SN=SN-ADMS-001&table=ATTLOG',
        data=body,
        content_type='text/plain',
    )

    assert response.status_code == 200
    assert response.content.decode() == 'OK'
    assert employee.attendance_punches.count() == 1
    assert BiometricSyncLog.objects.count() == 1
    assert BiometricSyncLog.objects.get().records_processed == 1


@pytest.mark.django_db
def test_device_sync_logs_endpoint_returns_recent_logs(biometric_setup):
    from apps.biometrics.models import BiometricDevice, BiometricSyncLog

    client = biometric_setup['client']
    organisation = biometric_setup['organisation']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='HQ Matrix',
        device_serial='MATRIX-01',
        protocol='MATRIX_COSEC',
        is_active=True,
    )
    BiometricSyncLog.objects.create(
        device=device,
        records_fetched=3,
        records_processed=2,
        records_skipped=1,
        success=True,
    )

    response = client.get(f'/api/org/biometrics/devices/{device.id}/sync-logs/')

    assert response.status_code == 200
    assert response.data[0]['records_fetched'] == 3


@pytest.mark.django_db
def test_essl_ebioserver_device_requires_shared_secret(biometric_setup):
    client = biometric_setup['client']

    response = client.post(
        '/api/org/biometrics/devices/',
        {
            'name': 'eSSL Web API',
            'protocol': 'ESSL_EBIOSERVER',
            'is_active': True,
        },
        format='json',
    )

    assert response.status_code == 400
    assert 'api_key' in response.data


@pytest.mark.django_db
def test_essl_ebioserver_webhook_rejects_invalid_secret(biometric_setup):
    from apps.biometrics.models import BiometricDevice

    anonymous_client = biometric_setup['anonymous_client']
    organisation = biometric_setup['organisation']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='eSSL Web API',
        protocol='ESSL_EBIOSERVER',
        is_active=True,
    )
    device.set_api_key('correct-secret')
    device.save(update_fields=['api_key_hash', 'api_key_encrypted', 'modified_at'])

    response = anonymous_client.post(
        f'/api/biometric/essl/ebioserver/{device.id}/events/',
        data={
            'transactions': [
                {
                    'EnrollNo': 'EMP100',
                    'PunchTime': '2026-04-05T09:05:00+05:30',
                    'Direction': 'IN',
                }
            ]
        },
        format='json',
        HTTP_X_BIOMETRIC_SECRET='wrong-secret',
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_essl_ebioserver_webhook_processes_transactions_and_writes_sync_log(biometric_setup):
    from apps.biometrics.models import BiometricDevice, BiometricSyncLog

    anonymous_client = biometric_setup['anonymous_client']
    organisation = biometric_setup['organisation']
    employee = biometric_setup['employee']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='eSSL Web API',
        protocol='ESSL_EBIOSERVER',
        is_active=True,
    )
    device.set_api_key('shared-secret')
    device.save(update_fields=['api_key_hash', 'api_key_encrypted', 'modified_at'])

    response = anonymous_client.post(
        f'/api/biometric/essl/ebioserver/{device.id}/events/',
        data={
            'transactions': [
                {
                    'EnrollNo': 'EMP100',
                    'PunchTime': '2026-04-05T09:05:00+05:30',
                    'Direction': 'IN',
                }
            ]
        },
        format='json',
        HTTP_X_BIOMETRIC_SECRET='shared-secret',
    )

    assert response.status_code == 200
    assert response.json()['processed'] == 1
    assert employee.attendance_punches.count() == 1
    assert BiometricSyncLog.objects.count() == 1
    assert BiometricSyncLog.objects.get().records_processed == 1


@pytest.mark.django_db
def test_essl_ebioserver_webhook_skips_duplicates_in_summary(biometric_setup):
    from apps.biometrics.models import BiometricDevice

    anonymous_client = biometric_setup['anonymous_client']
    organisation = biometric_setup['organisation']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='eSSL Web API',
        protocol='ESSL_EBIOSERVER',
        is_active=True,
    )
    device.set_api_key('shared-secret')
    device.save(update_fields=['api_key_hash', 'api_key_encrypted', 'modified_at'])

    response = anonymous_client.post(
        f'/api/biometric/essl/ebioserver/{device.id}/events/',
        data={
            'transactions': [
                {
                    'EnrollNo': 'EMP100',
                    'PunchTime': '2026-04-05T09:05:00+05:30',
                    'Direction': 'IN',
                },
                {
                    'EnrollNo': 'EMP100',
                    'PunchTime': '2026-04-05T09:05:30+05:30',
                    'Direction': 'IN',
                },
            ]
        },
        format='json',
        HTTP_X_BIOMETRIC_SECRET='shared-secret',
    )

    assert response.status_code == 200
    assert response.json() == {
        'processed': 1,
        'skipped': 1,
        'errors': [],
    }


@pytest.mark.django_db
def test_essl_ebioserver_webhook_skips_unknown_employees_without_failing_request(biometric_setup):
    from apps.biometrics.models import BiometricDevice, BiometricSyncLog

    anonymous_client = biometric_setup['anonymous_client']
    organisation = biometric_setup['organisation']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='eSSL Web API',
        protocol='ESSL_EBIOSERVER',
        is_active=True,
    )
    device.set_api_key('shared-secret')
    device.save(update_fields=['api_key_hash', 'api_key_encrypted', 'modified_at'])

    response = anonymous_client.post(
        f'/api/biometric/essl/ebioserver/{device.id}/events/',
        data={
            'transactions': [
                {
                    'EnrollNo': 'UNKNOWN-EMP',
                    'PunchTime': '2026-04-05T09:05:00+05:30',
                    'Direction': 'IN',
                }
            ]
        },
        format='json',
        HTTP_X_BIOMETRIC_SECRET='shared-secret',
    )

    assert response.status_code == 200
    assert response.json()['processed'] == 0
    assert response.json()['skipped'] == 1
    assert response.json()['errors'] == []
    assert BiometricSyncLog.objects.get().records_skipped == 1


@pytest.mark.django_db
def test_essl_ebioserver_webhook_accepts_auth_token_inside_realtime_payload(biometric_setup):
    from apps.biometrics.models import BiometricDevice

    anonymous_client = biometric_setup['anonymous_client']
    organisation = biometric_setup['organisation']
    employee = biometric_setup['employee']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='eSSL Web API',
        protocol='ESSL_EBIOSERVER',
        is_active=True,
    )
    device.set_api_key('shared-secret')
    device.save(update_fields=['api_key_hash', 'api_key_encrypted', 'modified_at'])

    response = anonymous_client.post(
        f'/api/biometric/essl/ebioserver/{device.id}/events/',
        data={
            'RealTime': {
                'OperationID': 'op-1',
                'SerialNumber': 'DESX12345678',
                'PunchLog': {
                    'Type': 'CheckIn',
                    'UserId': 'EMP100',
                    'LogTime': '2026-04-05 09:05:00',
                },
                'AuthToken': 'shared-secret',
            }
        },
        format='json',
    )

    assert response.status_code == 200
    assert response.json()['processed'] == 1
    assert employee.attendance_punches.count() == 1
