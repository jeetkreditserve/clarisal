from .base import *
import warnings

INSTALLED_APPS += ['django_extensions']

DEBUG = True

if not FIELD_ENCRYPTION_KEY:
    warnings.warn(
        'FIELD_ENCRYPTION_KEY is not set. Falling back to a SECRET_KEY-derived key. '
        'Use a real Fernet key outside development.',
        stacklevel=1,
    )

EMAIL_HOST = env('EMAIL_HOST', default='mailpit')
EMAIL_PORT = env.int('EMAIL_PORT', default=1025)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
ZEPTOMAIL_API_URL = env('DEV_ZEPTOMAIL_API_URL', default='')
ZEPTOMAIL_API_KEY = env('DEV_ZEPTOMAIL_API_KEY', default='')
FRONTEND_URL = env('DEV_FRONTEND_URL', default='http://localhost:8080')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_DOMAIN = env('DEV_SESSION_COOKIE_DOMAIN', default='') or None
CSRF_COOKIE_DOMAIN = env('DEV_CSRF_COOKIE_DOMAIN', default='') or None

# Keep local QA and Playwright runs from tripping production-tight auth throttles.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        **REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
        'anon': env('DEV_ANON_RATE', default='100000/hour'),
        'user': env('DEV_USER_RATE', default='100000/hour'),
        'auth_csrf': env('DEV_AUTH_CSRF_RATE', default='1000/minute'),
        'workforce_login': env('DEV_WORKFORCE_LOGIN_RATE', default='100/minute'),
        'control_tower_login': env('DEV_CONTROL_TOWER_LOGIN_RATE', default='100/minute'),
        'invite_validate': env('DEV_INVITE_VALIDATE_RATE', default='300/hour'),
        'invite_accept': env('DEV_INVITE_ACCEPT_RATE', default='100/hour'),
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
