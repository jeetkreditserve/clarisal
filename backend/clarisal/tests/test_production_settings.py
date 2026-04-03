import importlib
import os
import sys
import warnings
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured

VALID_FIELD_ENCRYPTION_KEY = 'h8nlt4sUe92YRk0-GDbvJ8vYtM8n0af9moboa-UfJIQ='


def _reload_production_settings(env_overrides):
    """Reload base and production settings with temporary env overrides."""
    with patch.dict(os.environ, env_overrides, clear=False):
        import clarisal.settings.base as base

        importlib.reload(base)
        sys.modules.pop('clarisal.settings.production', None)
        import clarisal.settings.production as production
        return importlib.reload(production)


def _reload_development_settings(env_overrides):
    """Reload development settings with temporary env overrides."""
    with patch.dict(os.environ, env_overrides, clear=False):
        import clarisal.settings.base as base

        importlib.reload(base)
        sys.modules.pop('clarisal.settings.development', None)
        import clarisal.settings.development as development
        return importlib.reload(development)


@pytest.mark.parametrize(
    'secret_key',
    [
        'django-insecure-dev-key-change-in-production',
        'your-secret-key-here-change-in-production',
    ],
)
def test_insecure_secret_key_raises_improperly_configured(secret_key):
    with pytest.raises(ImproperlyConfigured, match='SECRET_KEY'):
        _reload_production_settings(
            {
                'SECRET_KEY': secret_key,
                'FIELD_ENCRYPTION_KEY': VALID_FIELD_ENCRYPTION_KEY,
                'ALLOWED_HOSTS': 'example.com',
            }
        )


@pytest.mark.parametrize(
    'field_encryption_key',
    [
        '',
        'not-a-valid-fernet-key',
    ],
)
def test_invalid_field_encryption_key_raises_improperly_configured(field_encryption_key):
    with pytest.raises(ImproperlyConfigured, match='FIELD_ENCRYPTION_KEY'):
        _reload_production_settings(
            {
                'SECRET_KEY': 'a-sufficiently-long-random-secret-key-for-testing-123456',
                'FIELD_ENCRYPTION_KEY': field_encryption_key,
                'ALLOWED_HOSTS': 'example.com',
            }
        )


def test_missing_field_encryption_key_warns_in_development():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        _reload_development_settings(
            {
                'SECRET_KEY': 'a-sufficiently-long-random-secret-key-for-testing-123456',
                'FIELD_ENCRYPTION_KEY': '',
            }
        )

    assert any('FIELD_ENCRYPTION_KEY is not set' in str(item.message) for item in captured)
