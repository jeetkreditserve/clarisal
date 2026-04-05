from celery import shared_task
from django.utils import timezone

from .models import BiometricDevice, BiometricProtocol, BiometricSyncLog
from .protocols.hikvision import sync_hikvision_device
from .protocols.matrix_cosec import sync_cosec_device
from .protocols.suprema import sync_biostar_device


@shared_task(name='biometrics.sync_pull_devices')
def sync_pull_devices():
    pull_sync_handlers = {
        BiometricProtocol.MATRIX_COSEC: sync_cosec_device,
        BiometricProtocol.SUPREMA_BIOSTAR: sync_biostar_device,
        BiometricProtocol.HIKVISION_ISAPI: sync_hikvision_device,
    }
    devices = BiometricDevice.objects.filter(
        is_active=True,
        protocol__in=list(pull_sync_handlers.keys()),
    ).select_related('organisation')

    for device in devices:
        handler = pull_sync_handlers.get(device.protocol)
        if handler is None:
            continue
        try:
            summary = handler(device, str(device.organisation_id))
            BiometricSyncLog.objects.create(
                device=device,
                records_fetched=summary['processed'] + summary['skipped'],
                records_processed=summary['processed'],
                records_skipped=summary['skipped'],
                errors=summary.get('errors', []),
                success=not summary.get('errors', []),
            )
            device.last_sync_at = timezone.now()
            device.save(update_fields=['last_sync_at', 'modified_at'])
        except Exception as exc:  # noqa: BLE001
            BiometricSyncLog.objects.create(
                device=device,
                records_fetched=0,
                records_processed=0,
                records_skipped=0,
                errors=[str(exc)],
                success=False,
            )
