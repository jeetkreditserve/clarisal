from .development import *

# Use local database for tests (not the Docker 'db' hostname)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'calrisal_test',
        'USER': 'calrisal',
        'PASSWORD': 'calrisal_dev_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'calrisal_test',
        },
    }
}

# Speed up tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable email sending in tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
