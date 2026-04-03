from __future__ import annotations

from .models import BiometricProtocol
from .protocols.hikvision import sync_hikvision_device
from .protocols.matrix_cosec import sync_cosec_device
from .protocols.suprema import sync_biostar_device

PULL_SYNC_HANDLERS = {
    BiometricProtocol.MATRIX_COSEC: sync_cosec_device,
    BiometricProtocol.SUPREMA_BIOSTAR: sync_biostar_device,
    BiometricProtocol.HIKVISION_ISAPI: sync_hikvision_device,
}


def sync_device(device) -> dict:
    handler = PULL_SYNC_HANDLERS.get(device.protocol)
    if handler is None:
        raise ValueError(f'No pull sync handler registered for protocol {device.protocol}.')
    return handler(device, str(device.organisation_id))
