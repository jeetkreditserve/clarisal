from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
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

    return response
