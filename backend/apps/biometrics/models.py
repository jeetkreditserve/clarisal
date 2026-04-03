from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel
from apps.common.security import decrypt_value, encrypt_value, hash_token, mask_value


class BiometricProtocol(models.TextChoices):
    ZK_ADMS = 'ZK_ADMS', 'ZKTeco / eSSL / Biomax (ADMS Push)'
    ESSL_EBIOSERVER = 'ESSL_EBIOSERVER', 'eSSL eBioserver (Webhook Push)'
    MATRIX_COSEC = 'MATRIX_COSEC', 'Matrix COSEC (REST Pull)'
    SUPREMA_BIOSTAR = 'SUPREMA_BIOSTAR', 'Suprema BioStar 2 (REST Pull)'
    HIKVISION_ISAPI = 'HIKVISION_ISAPI', 'HikVision ISAPI (REST Pull)'


class BiometricDevice(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='biometric_devices',
    )
    name = models.CharField(max_length=100)
    device_serial = models.CharField(max_length=100, blank=True, help_text='Device serial number / SN')
    protocol = models.CharField(max_length=30, choices=BiometricProtocol.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.PositiveIntegerField(default=80)
    auth_username = models.CharField(max_length=200, blank=True)
    api_key_hash = models.CharField(max_length=128, blank=True, help_text='SHA-256 hash of the device secret')
    api_key_encrypted = models.TextField(blank=True)
    oauth_client_id = models.CharField(max_length=200, blank=True)
    oauth_client_secret_hash = models.CharField(max_length=128, blank=True)
    oauth_client_secret_encrypted = models.TextField(blank=True)
    location = models.ForeignKey(
        'locations.OfficeLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='biometric_devices',
    )
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name', 'device_serial']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'device_serial'],
                condition=~Q(device_serial=''),
                name='unique_biometric_device_serial_per_org',
            ),
        ]
        indexes = [
            models.Index(fields=['organisation', 'protocol', 'is_active']),
            models.Index(fields=['organisation', 'last_sync_at']),
        ]

    def set_api_key(self, raw_key: str):
        self.api_key_hash = hash_token(raw_key)
        self.api_key_encrypted = encrypt_value(raw_key)

    def get_api_key(self) -> str:
        return decrypt_value(self.api_key_encrypted)

    def get_api_key_preview(self) -> str:
        return mask_value(self.get_api_key())

    def set_oauth_client_secret(self, raw_secret: str):
        self.oauth_client_secret_hash = hash_token(raw_secret)
        self.oauth_client_secret_encrypted = encrypt_value(raw_secret)

    def get_oauth_client_secret(self) -> str:
        return decrypt_value(self.oauth_client_secret_encrypted)

    def __str__(self):
        return f'{self.name} ({self.protocol})'


class BiometricSyncLog(AuditedBaseModel):
    device = models.ForeignKey(BiometricDevice, on_delete=models.CASCADE, related_name='sync_logs')
    synced_at = models.DateTimeField(auto_now_add=True)
    records_fetched = models.PositiveIntegerField(default=0)
    records_processed = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ['-synced_at']
        indexes = [
            models.Index(fields=['device', 'synced_at']),
        ]
