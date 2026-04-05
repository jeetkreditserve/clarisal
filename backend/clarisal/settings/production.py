# ruff: noqa: F403, F405
from django.core.exceptions import ImproperlyConfigured

from apps.common.security import validate_field_encryption_configuration

from .base import *

# In production, ALLOWED_HOSTS MUST be set via environment variable — no fallback
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

_INSECURE_SECRET_KEY_FRAGMENTS = (
    'insecure',
    'change-in-production',
    'your-secret-key-here',
    'django-insecure',
)
if any(fragment in SECRET_KEY for fragment in _INSECURE_SECRET_KEY_FRAGMENTS):
    raise ImproperlyConfigured(
        'SECRET_KEY contains an insecure placeholder value. '
        'Generate a strong key with: python -c "from django.core.utils.crypto import get_random_string; '
        'print(get_random_string(50))"'
    )

DEBUG = False
validate_field_encryption_configuration(field_encryption_key=FIELD_ENCRYPTION_KEY, debug=DEBUG)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Use S3 for media in production
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
