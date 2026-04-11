from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.biometrics.models import BiometricDevice


class VendorFamily(str, Enum):  # noqa: UP042
    ZK = "ZK"
    ESSL = "ESSL"
    MATRIX = "MATRIX"
    HIKVISION = "HIKVISION"
    SUPREMA = "SUPREMA"
    MANTRA = "MANTRA"
    CP_PLUS = "CP_PLUS"


class ConnectivityMode(str, Enum):  # noqa: UP042
    PUSH = "PUSH"
    PULL = "PULL"
    EXPORT_BRIDGE = "EXPORT_BRIDGE"


class AuthType(str, Enum):  # noqa: UP042
    DEVICE_SERIAL = "DEVICE_SERIAL"
    API_KEY = "API_KEY"
    SHARED_SECRET = "SHARED_SECRET"  # nosec B105
    DIGEST_AUTH = "DIGEST_AUTH"
    OAUTH_SESSION = "OAUTH_SESSION"
    AEBAS_BRIDGE = "AEBAS_BRIDGE"


@dataclass
class VendorCapability:
    transport: ConnectivityMode
    auth_type: AuthType
    push_endpoint: str | None = None
    pull_endpoint: str | None = None
    supports_direction: bool = True
    supports_work_code: bool = False
    supports_offline_recovery: bool = False
    native_vendor: bool = True


@dataclass
class VendorRegistry:
    vendor: str
    product_families: list[str]
    capabilities: dict[str, VendorCapability]
    notes: str = ""
    middleware_mode: bool = False
    compatible_with: list[str] = field(default_factory=list)


def _zk_adms_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.PUSH,
        auth_type=AuthType.DEVICE_SERIAL,
        push_endpoint="/api/v1/biometric/adms/iclock/cdata",
        supports_direction=True,
        supports_work_code=True,
    )


def _essl_ebioserver_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.PUSH,
        auth_type=AuthType.SHARED_SECRET,
        push_endpoint="/api/v1/biometric/essl/webhook",
        supports_direction=True,
    )


def _matrix_cosec_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.PULL,
        auth_type=AuthType.API_KEY,
        pull_endpoint="/api/v1/monitoring/attendance",
        supports_direction=True,
    )


def _suprema_biostar_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.PULL,
        auth_type=AuthType.OAUTH_SESSION,
        pull_endpoint="/api/lists/log",
        supports_direction=True,
    )


def _hikvision_isapi_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.PULL,
        auth_type=AuthType.DIGEST_AUTH,
        pull_endpoint="/ISAPI/Attendance/Record",
        supports_direction=True,
    )


def _mantra_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.EXPORT_BRIDGE,
        auth_type=AuthType.AEBAS_BRIDGE,
        supports_direction=True,
        supports_offline_recovery=True,
    )


def _cpplus_capability() -> VendorCapability:
    return VendorCapability(
        transport=ConnectivityMode.EXPORT_BRIDGE,
        auth_type=AuthType.API_KEY,
        supports_direction=True,
    )


VENDOR_REGISTRY: dict[str, VendorRegistry] = {
    "ZKTECO": VendorRegistry(
        vendor="ZKTeco",
        product_families=["ADMS", "ZKBio", "ZKTeco Time"],
        capabilities={
            "ZK_ADMS": _zk_adms_capability(),
        },
        notes="Supports ZK push protocol via ADMS. Also covers eSSL and Biomax deployments using ADMS.",
        compatible_with=["ESSL"],
    ),
    "ESSL": VendorRegistry(
        vendor="eSSL",
        product_families=["eBioserver", "eTime", "eSecure", "ZKTeco-based"],
        capabilities={
            "ZK_ADMS": _zk_adms_capability(),
            "ESSL_EBIOSERVER": _essl_ebioserver_capability(),
        },
        notes="eSSL uses ZK-compatible ADMS push or eBioserver webhooks.",
        middleware_mode=True,
        compatible_with=["ZK"],
    ),
    "MATRIX": VendorRegistry(
        vendor="Matrix COSEC",
        product_families=["COSEC", "COSEC VISA", "COSEC DOOR"],
        capabilities={
            "MATRIX_COSEC": _matrix_cosec_capability(),
        },
        notes="REST pull from COSEC REST API using API key.",
    ),
    "HIKVISION": VendorRegistry(
        vendor="HikVision",
        product_families=["DS-K1T", "DS-K1M", "iDS"],
        capabilities={
            "HIKVISION_ISAPI": _hikvision_isapi_capability(),
        },
        notes="ISAPI REST pull with digest authentication.",
    ),
    "SUPREMA": VendorRegistry(
        vendor="Suprema",
        product_families=["BioStar 2", "BioEntry", "BioLite", "FaceStation"],
        capabilities={
            "SUPREMA_BIOSTAR": _suprema_biostar_capability(),
        },
        notes="BioStar 2 REST API with session-based authentication.",
    ),
    "MANTRA": VendorRegistry(
        vendor="Mantra",
        product_families=["MFS100", "Morpho", "AEBAS-linked"],
        capabilities={
            "MANTRA_AEBAS": _mantra_capability(),
        },
        notes="AEBAS bridge integration for government-linked attendance. Supports offline export ingestion.",
        middleware_mode=True,
    ),
    "CP_PLUS": VendorRegistry(
        vendor="CP PLUS",
        product_families=["CP PLUS Attendance", "eSSL-based"],
        capabilities={
            "CP_PLUS_EXPORT": _cpplus_capability(),
        },
        notes="CP PLUS devices often use eSSL-compatible protocols. Export bridge available.",
        middleware_mode=True,
        compatible_with=["ESSL"],
    ),
}


def get_vendor_for_protocol(protocol: str) -> str | None:
    for vendor_key, registry in VENDOR_REGISTRY.items():
        if protocol in registry.capabilities:
            return vendor_key
    return None


def get_vendor_registry(vendor_key: str) -> VendorRegistry | None:
    return VENDOR_REGISTRY.get(vendor_key.upper())


def get_capability_for_device(device: BiometricDevice) -> VendorCapability | None:
    vendor_key = device.vendor.upper() if device.vendor else None
    if not vendor_key:
        vendor_key = get_vendor_for_protocol(device.protocol)
    if not vendor_key:
        return None
    registry = VENDOR_REGISTRY.get(vendor_key)
    if not registry:
        return None
    return registry.capabilities.get(device.protocol)


def get_device_connectivity_mode(device: BiometricDevice) -> ConnectivityMode | None:
    capability = get_capability_for_device(device)
    return capability.transport if capability else None


def list_all_vendors() -> list[dict]:
    return [
        {
            "key": key,
            "vendor": reg.vendor,
            "product_families": reg.product_families,
            "protocols": list(reg.capabilities.keys()),
            "notes": reg.notes,
            "middleware_mode": reg.middleware_mode,
            "compatible_with": reg.compatible_with,
        }
        for key, reg in VENDOR_REGISTRY.items()
    ]


def get_compatible_vendors(vendor_key: str) -> list[str]:
    registry = VENDOR_REGISTRY.get(vendor_key.upper())
    if not registry:
        return []
    return registry.compatible_with
