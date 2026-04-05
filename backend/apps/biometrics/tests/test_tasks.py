from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_sync_pull_devices_dispatches_active_pull_devices(biometric_setup):
    from apps.biometrics.models import BiometricDevice, BiometricSyncLog
    from apps.biometrics.tasks import sync_pull_devices

    organisation = biometric_setup['organisation']
    device = BiometricDevice.objects.create(
        organisation=organisation,
        name='HQ Matrix',
        device_serial='MATRIX-01',
        protocol='MATRIX_COSEC',
        ip_address='192.168.1.100',
        port=80,
        is_active=True,
    )
    with patch('apps.biometrics.tasks.sync_cosec_device') as mock_sync_cosec_device:
        mock_sync_cosec_device.return_value = {'processed': 2, 'skipped': 1, 'errors': []}
        sync_pull_devices()

    device.refresh_from_db()
    assert mock_sync_cosec_device.called
    assert device.last_sync_at is not None
    assert BiometricSyncLog.objects.get(device=device).records_processed == 2
