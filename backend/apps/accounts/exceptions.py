import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('apps.api')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get('request')
    view = context.get('view')
    path = getattr(request, 'path', '')
    method = getattr(request, 'method', '')
    view_name = view.__class__.__name__ if view is not None else ''

    if response is None:
        logger.exception(
            'Unhandled API exception',
            extra={
                'path': path,
                'method': method,
                'view': view_name,
                'user_id': getattr(getattr(request, 'user', None), 'id', None),
            },
        )
        return Response(
            {'error': 'An unexpected error occurred', 'detail': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Normalize error format
    if isinstance(response.data, dict):
        if 'detail' in response.data:
            response.data = {'error': str(response.data['detail'])}
        elif 'non_field_errors' in response.data:
            response.data = {'error': response.data['non_field_errors'][0]}
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS and getattr(exc, 'wait', None):
            response.data['retry_after'] = exc.wait

    if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(
            'API error response',
            extra={
                'path': path,
                'method': method,
                'view': view_name,
                'status_code': response.status_code,
                'user_id': getattr(getattr(request, 'user', None), 'id', None),
            },
        )
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        logger.warning(
            'API request throttled',
            extra={
                'path': path,
                'method': method,
                'view': view_name,
                'user_id': getattr(getattr(request, 'user', None), 'id', None),
            },
        )

    return response
