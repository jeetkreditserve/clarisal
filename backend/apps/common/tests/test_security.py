import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.common.security import decrypt_value, encrypt_value, validate_field_encryption_configuration


def test_validate_field_encryption_configuration_allows_debug_mode_without_field_key():
    validate_field_encryption_configuration(field_encryption_key='', debug=True)


@pytest.mark.parametrize('value', ['', 'replace-with-a-32-byte-secret'])
def test_validate_field_encryption_configuration_rejects_missing_or_placeholder_key_outside_debug(value):
    with pytest.raises(ImproperlyConfigured) as exc_info:
        validate_field_encryption_configuration(field_encryption_key=value, debug=False)

    assert 'FIELD_ENCRYPTION_KEY must be set' in str(exc_info.value)


def test_validate_field_encryption_configuration_allows_real_key_outside_debug():
    validate_field_encryption_configuration(field_encryption_key='prod-secret-key-1234567890', debug=False)


@override_settings(FIELD_ENCRYPTION_KEY='unit-test-field-key', SECRET_KEY='fallback-secret')
def test_encrypt_value_round_trips_when_field_key_is_configured():
    encrypted = encrypt_value('ABCDE1234F')

    assert encrypted
    assert encrypted != 'ABCDE1234F'
    assert decrypt_value(encrypted) == 'ABCDE1234F'
