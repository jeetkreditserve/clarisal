import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.common.security import decrypt_value, encrypt_value, validate_field_encryption_configuration

VALID_FIELD_ENCRYPTION_KEY = 'h8nlt4sUe92YRk0-GDbvJ8vYtM8n0af9moboa-UfJIQ='  # pragma: allowlist secret
SECOND_VALID_FIELD_ENCRYPTION_KEY = 'o5j7RYM1mPSx3mGkW4onh8aKQk7rVJ6YQmD55Y2A7e8='  # pragma: allowlist secret


def test_validate_field_encryption_configuration_allows_debug_mode_without_field_key():
    validate_field_encryption_configuration(field_encryption_key='', debug=True)


@pytest.mark.parametrize('value', ['', 'replace-with-a-32-byte-secret'])
def test_validate_field_encryption_configuration_rejects_missing_or_placeholder_key_outside_debug(value):
    with pytest.raises(ImproperlyConfigured) as exc_info:
        validate_field_encryption_configuration(field_encryption_key=value, debug=False)

    assert 'FIELD_ENCRYPTION_KEY must be set' in str(exc_info.value)


def test_validate_field_encryption_configuration_allows_real_key_outside_debug():
    validate_field_encryption_configuration(field_encryption_key=VALID_FIELD_ENCRYPTION_KEY, debug=False)


@override_settings(FIELD_ENCRYPTION_KEY='unit-test-field-key', SECRET_KEY='fallback-secret')
def test_encrypt_value_round_trips_when_field_key_is_configured():
    encrypted = encrypt_value('ABCDE1234F')

    assert encrypted
    assert encrypted != 'ABCDE1234F'
    assert decrypt_value(encrypted) == 'ABCDE1234F'


def test_decrypt_value_logs_invalid_token_for_corrupt_ciphertext(monkeypatch):
    captured = {}

    def fake_warning(message, *, extra):
        captured['message'] = message
        captured['extra'] = extra

    monkeypatch.setattr('apps.common.security.logger.warning', fake_warning)

    assert decrypt_value('not-a-valid-fernet-token') == ''

    assert captured == {
        'message': 'field_decryption_failed',
        'extra': {
            'reason': 'invalid_token',
            'ciphertext_length': len('not-a-valid-fernet-token'),
        },
    }

def test_decrypt_value_logs_invalid_token_for_wrong_key(monkeypatch):
    with override_settings(FIELD_ENCRYPTION_KEY=VALID_FIELD_ENCRYPTION_KEY, SECRET_KEY='fallback-secret'):
        encrypted = encrypt_value('ABCDE1234F')

    captured = {}

    def fake_warning(message, *, extra):
        captured['message'] = message
        captured['extra'] = extra

    monkeypatch.setattr('apps.common.security.logger.warning', fake_warning)
    with override_settings(FIELD_ENCRYPTION_KEY=SECOND_VALID_FIELD_ENCRYPTION_KEY, SECRET_KEY='fallback-secret'):
        assert decrypt_value(encrypted) == ''

    assert captured == {
        'message': 'field_decryption_failed',
        'extra': {
            'reason': 'invalid_token',
            'ciphertext_length': len(encrypted),
        },
    }


def test_decrypt_value_returns_empty_string_for_non_value_inputs():
    assert decrypt_value(None) == ''
    assert decrypt_value('') == ''
    assert decrypt_value(123) == ''  # type: ignore[arg-type]


def test_api_health_endpoint_sets_security_headers(client, monkeypatch):
    monkeypatch.setenv('GIT_SHA', 'health-sha')

    response = client.get('/api/health/')

    assert response.status_code == 200
    assert response['X-Content-Type-Options'] == 'nosniff'
    assert response['X-Frame-Options'] == 'DENY'
