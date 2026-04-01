from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.common.email_service import _normalized_zeptomail_api_key, _normalized_zeptomail_api_url


@pytest.mark.parametrize(
    ('configured_url', 'expected_url'),
    [
        ('api.zeptomail.in', 'https://api.zeptomail.in/v1.1/email'),
        ('https://api.zeptomail.in', 'https://api.zeptomail.in/v1.1/email'),
        ('https://api.zeptomail.in/v1.1/email', 'https://api.zeptomail.in/v1.1/email'),
    ],
)
@override_settings(ZEPTOMAIL_API_KEY='dummy-key')
def test_normalizes_zeptomail_api_url(configured_url, expected_url):
    with patch('django.conf.settings.ZEPTOMAIL_API_URL', configured_url):
        assert _normalized_zeptomail_api_url() == expected_url


@pytest.mark.parametrize(
    ('configured_key', 'expected_header'),
    [
        ('raw-key', 'Zoho-enczapikey raw-key'),
        ('Zoho-enczapikey full-header-key', 'Zoho-enczapikey full-header-key'),
    ],
)
def test_normalizes_zeptomail_api_key(configured_key, expected_header):
    with patch('django.conf.settings.ZEPTOMAIL_API_KEY', configured_key):
        assert _normalized_zeptomail_api_key() == expected_header
