from unittest.mock import patch

import pytest
from rest_framework.exceptions import ErrorDetail, NotFound, Throttled, ValidationError
from rest_framework.test import APIRequestFactory

from apps.accounts.exceptions import custom_exception_handler


class DummyView:
    pass


@pytest.mark.parametrize(
    ('exc', 'expected'),
    [
        (NotFound(detail='Missing record.'), {'error': 'Missing record.'}),
        (ValidationError({'non_field_errors': [ErrorDetail('Broken input', code='invalid')]}), {'error': ErrorDetail('Broken input', code='invalid')}),
    ],
)
def test_custom_exception_handler_normalizes_known_error_shapes(exc, expected):
    request = APIRequestFactory().get('/api/example/')

    response = custom_exception_handler(exc, {'request': request, 'view': DummyView()})

    assert response.data == expected


def test_custom_exception_handler_includes_retry_after_for_throttling():
    request = APIRequestFactory().get('/api/example/')

    response = custom_exception_handler(Throttled(wait=120), {'request': request, 'view': DummyView()})

    assert response.status_code == 429
    assert response.data['retry_after'] == 120


def test_custom_exception_handler_returns_500_for_unhandled_exceptions():
    request = APIRequestFactory().get('/api/example/')
    request.user = type('UserStub', (), {'id': 'user-1'})()

    with patch('apps.accounts.exceptions.logger.exception') as mock_log:
        response = custom_exception_handler(RuntimeError('unexpected'), {'request': request, 'view': DummyView()})

    assert response.status_code == 500
    assert response.data == {'error': 'An unexpected error occurred', 'detail': 'unexpected'}
    mock_log.assert_called_once()
