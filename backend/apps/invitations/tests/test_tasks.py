from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.common.email_service import _normalized_zeptomail_api_url


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
