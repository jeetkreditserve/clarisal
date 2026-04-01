from .development import *

# Use in-memory SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Speed up tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable email sending in tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        **REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
        'anon': '100000/hour',
        'user': '100000/hour',
        'auth_csrf': '100000/hour',
        'workforce_login': '100000/hour',
        'control_tower_login': '100000/hour',
        'password_reset_request': '100000/hour',
        'password_reset_confirm': '100000/hour',
        'invite_validate': '100000/hour',
        'invite_accept': '100000/hour',
        'approval_action': '100000/hour',
        'document_upload': '100000/hour',
    },
}
