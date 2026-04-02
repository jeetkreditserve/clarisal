import base64
import hashlib
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def generate_secure_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def validate_field_encryption_configuration(*, field_encryption_key: str, debug: bool) -> None:
    if debug:
        return
    if not field_encryption_key or field_encryption_key == 'replace-with-a-32-byte-secret':
        raise ImproperlyConfigured(
            'FIELD_ENCRYPTION_KEY must be set to a real secret when DEBUG is false.'
        )


def _derive_fernet_key() -> bytes:
    seed = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or settings.SECRET_KEY
    digest = hashlib.sha256(seed.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt_value(value: Optional[str]) -> str:
    if not value:
        return ''
    return get_fernet().encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_value(value: Optional[str]) -> str:
    if not value:
        return ''
    try:
        return get_fernet().decrypt(value.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        return ''


def mask_value(value: str, keep_last: int = 4, mask_char: str = '•') -> str:
    if not value:
        return ''
    if len(value) <= keep_last:
        return value
    return f"{mask_char * max(0, len(value) - keep_last)}{value[-keep_last:]}"
