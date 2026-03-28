# Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a fully running Docker environment with PostgreSQL, Redis, Django backend with all models + JWT auth, Celery, and React/Vite frontend with auth pages, AuthContext, role-specific layouts and routing — everything needed as foundation for Phases 2-5.

**Architecture:** Dockerized monolith — Django DRF backend + React Vite SPA frontend. All 8 Django apps created with their models in one pass to handle circular FK references cleanly. JWT auth with custom payload (role + org_id). Role-aware routing with three distinct layout shells.

**Tech Stack:** Django 4.2, DRF, SimpleJWT, Celery 5, Redis 7, PostgreSQL 15, React 18, Vite 5, TypeScript, Tailwind 4, shadcn/ui, TanStack Query 5, React Router 7, axios, pytest-django, Playwright.

---

## File Map

### Root
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

### Backend
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `backend/manage.py`
- Create: `backend/calrisal/__init__.py`
- Create: `backend/calrisal/settings/__init__.py`
- Create: `backend/calrisal/settings/base.py`
- Create: `backend/calrisal/settings/development.py`
- Create: `backend/calrisal/settings/production.py`
- Create: `backend/calrisal/urls.py`
- Create: `backend/calrisal/wsgi.py`
- Create: `backend/calrisal/asgi.py`
- Create: `backend/calrisal/celery.py`
- Create: `backend/apps/__init__.py`
- Create: `backend/apps/accounts/` — Custom User model, JWT auth, permissions
- Create: `backend/apps/organisations/` — Organisation model + state enum
- Create: `backend/apps/invitations/` — Invitation model
- Create: `backend/apps/locations/` — OfficeLocation model
- Create: `backend/apps/departments/` — Department model
- Create: `backend/apps/employees/` — Employee, EmployeeProfile, EducationRecord models
- Create: `backend/apps/documents/` — Document model
- Create: `backend/apps/audit/` — AuditLog model
- Create: `backend/conftest.py`
- Create: `backend/pytest.ini`

### Frontend
- Create: `frontend/` — Vite+React+TS scaffold
- Create: `frontend/src/types/auth.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/rbac.ts`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/components/auth/ProtectedRoute.tsx`
- Create: `frontend/src/components/layouts/CTLayout.tsx`
- Create: `frontend/src/components/layouts/OrgLayout.tsx`
- Create: `frontend/src/components/layouts/EmployeeLayout.tsx`
- Create: `frontend/src/routes/index.tsx`
- Create: `frontend/src/pages/auth/LoginPage.tsx`
- Create: `frontend/src/pages/auth/InviteAcceptPage.tsx`
- Create: `frontend/src/pages/auth/RequestPasswordResetPage.tsx`
- Create: `frontend/src/pages/ct/DashboardPage.tsx` (placeholder)
- Create: `frontend/src/pages/org/DashboardPage.tsx` (placeholder)
- Create: `frontend/src/pages/employee/DashboardPage.tsx` (placeholder)

---

## Task 1: Repository Structure + Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

- [ ] **Step 1.1: Create project root structure**

```bash
cd /home/jeet/PycharmProjects/clarisal
mkdir -p backend frontend nginx docs/superpowers/specs docs/superpowers/plans
```

- [ ] **Step 1.2: Create .gitignore**

Create `/home/jeet/PycharmProjects/clarisal/.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*.pyo
.Python
*.egg-info/
dist/
build/
.eggs/
.venv/
venv/
*.pyc

# Django
*.log
local_settings.py
db.sqlite3
media/

# Env
.env
.env.local
.env.*.local

# Node
node_modules/
frontend/dist/
frontend/.vite/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Test
.coverage
htmlcov/
.pytest_cache/
/tmp/test-emails/

# Playwright
frontend/playwright-report/
frontend/test-results/
```

- [ ] **Step 1.3: Create .env.example**

Create `/home/jeet/PycharmProjects/clarisal/.env.example`:
```bash
# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
POSTGRES_DB=calrisal
POSTGRES_USER=calrisal
POSTGRES_PASSWORD=calrisal_dev_password
DATABASE_URL=postgresql://calrisal:calrisal_dev_password@db:5432/calrisal

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=calrisal-documents
AWS_S3_REGION_NAME=ap-south-1

# Email (Zoho SMTP)
EMAIL_HOST=smtp.zoho.in
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=noreply@calrisal.com
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=Calrisal <noreply@calrisal.com>

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api

# App
FRONTEND_URL=http://localhost:5173
CONTROL_TOWER_EMAIL=admin@calrisal.com
CONTROL_TOWER_PASSWORD=CalrisalAdmin@2024!
```

- [ ] **Step 1.4: Create backend Dockerfile**

Create `/home/jeet/PycharmProjects/clarisal/backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "calrisal.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

- [ ] **Step 1.5: Create frontend Dockerfile**

Create `/home/jeet/PycharmProjects/clarisal/frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 1.6: Create docker-compose.yml**

Create `/home/jeet/PycharmProjects/clarisal/docker-compose.yml`:
```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-calrisal}
      POSTGRES_USER: ${POSTGRES_USER:-calrisal}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-calrisal_dev_password}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-calrisal}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      DJANGO_SETTINGS_MODULE: calrisal.settings.development
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A calrisal worker -l info
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      DJANGO_SETTINGS_MODULE: calrisal.settings.development
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A calrisal beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app
    env_file:
      - .env
    environment:
      DJANGO_SETTINGS_MODULE: calrisal.settings.development
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    env_file:
      - .env
    environment:
      - VITE_API_BASE_URL=http://localhost:8000/api

volumes:
  postgres_data:
```

- [ ] **Step 1.7: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git init
git add docker-compose.yml .env.example .gitignore backend/Dockerfile frontend/Dockerfile
git commit -m "chore: add docker-compose and Dockerfiles for all services"
```

---

## Task 2: Django Project Scaffold + Settings + Requirements

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/manage.py`
- Create: `backend/calrisal/__init__.py`
- Create: `backend/calrisal/settings/base.py`
- Create: `backend/calrisal/settings/development.py`
- Create: `backend/calrisal/settings/production.py`
- Create: `backend/calrisal/urls.py`
- Create: `backend/calrisal/wsgi.py`
- Create: `backend/calrisal/asgi.py`
- Create: `backend/calrisal/celery.py`

- [ ] **Step 2.1: Create requirements.txt**

Create `/home/jeet/PycharmProjects/clarisal/backend/requirements.txt`:
```
# Core
Django==4.2.16
djangorestframework==3.15.2
django-cors-headers==4.4.0
django-environ==0.11.2
psycopg2-binary==2.9.9
gunicorn==22.0.0

# Auth
djangorestframework-simplejwt==5.3.1

# Celery + Redis
celery==5.4.0
redis==5.1.1
django-celery-results==2.5.1
django-celery-beat==2.7.0

# AWS S3
boto3==1.35.30
django-storages==1.14.4

# Security
django-ratelimit==4.1.0

# Utilities
Pillow==10.4.0
python-slugify==8.0.4

# Testing
pytest==8.3.3
pytest-django==4.9.0
factory-boy==3.3.1
faker==30.3.0
```

- [ ] **Step 2.2: Create Django project structure**

```bash
cd /home/jeet/PycharmProjects/clarisal/backend
mkdir -p calrisal/settings apps
touch calrisal/__init__.py
touch calrisal/settings/__init__.py
touch apps/__init__.py
```

- [ ] **Step 2.3: Create manage.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/manage.py`:
```python
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calrisal.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2.4: Create settings/base.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/settings/base.py`:
```python
import os
from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_celery_results',
    'django_celery_beat',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.organisations',
    'apps.invitations',
    'apps.locations',
    'apps.departments',
    'apps.employees',
    'apps.documents',
    'apps.audit',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'calrisal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'calrisal.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgresql://calrisal:calrisal_dev_password@localhost:5432/calrisal')
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'apps.accounts.serializers.CustomTokenObtainPairSerializer',
}

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'apps.accounts.exceptions.custom_exception_handler',
}

# CORS
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:5173'])
CORS_ALLOW_CREDENTIALS = True

# Celery
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.zoho.in')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Calrisal <noreply@calrisal.com>')

# AWS S3
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='calrisal-documents')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='ap-south-1')
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_DEFAULT_ACL = 'private'
AWS_S3_FILE_OVERWRITE = False

# App config
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:5173')
INVITE_TOKEN_EXPIRY_HOURS = 48
```

- [ ] **Step 2.5: Create settings/development.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/settings/development.py`:
```python
from .base import *

DEBUG = True

INSTALLED_APPS += ['django_extensions']

# Use console email in development (override with file-based for Playwright tests)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
```

- [ ] **Step 2.6: Create settings/production.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/settings/production.py`:
```python
from .base import *

DEBUG = False

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

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
```

- [ ] **Step 2.7: Create calrisal/urls.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'calrisal-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/auth/', include('apps.accounts.urls')),
    # Phase 2+: CT, Org, Employee URLs will be added here
]
```

- [ ] **Step 2.8: Create calrisal/wsgi.py and asgi.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/wsgi.py`:
```python
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calrisal.settings.production')
application = get_wsgi_application()
```

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calrisal.settings.production')
application = get_asgi_application()
```

- [ ] **Step 2.9: Create calrisal/celery.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calrisal.settings.development')

app = Celery('calrisal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

Create `/home/jeet/PycharmProjects/clarisal/backend/calrisal/__init__.py`:
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

- [ ] **Step 2.10: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add backend/requirements.txt backend/manage.py backend/calrisal/
git commit -m "feat: scaffold Django project with split settings and Celery config"
```

---

## Task 3: All Django App Scaffolds + Models

**Files:**
- Create: all 8 app directories under `backend/apps/`
- Create: all `models.py` files

> **Note:** All models are created together to avoid circular migration issues. The FK from `User → Organisation` and `Organisation → User (created_by)` are both nullable and use string-based references, so Django resolves the dependency automatically.

- [ ] **Step 3.1: Create all 8 app directories**

```bash
cd /home/jeet/PycharmProjects/clarisal/backend
for app in accounts organisations invitations locations departments employees documents audit; do
    mkdir -p apps/$app/management/commands apps/$app/tests
    touch apps/$app/__init__.py
    touch apps/$app/admin.py
    touch apps/$app/apps.py
    touch apps/$app/models.py
    touch apps/$app/serializers.py
    touch apps/$app/views.py
    touch apps/$app/urls.py
    touch apps/$app/services.py
    touch apps/$app/repositories.py
    touch apps/$app/permissions.py
    touch apps/$app/signals.py
    touch apps/$app/tests/__init__.py
    touch apps/$app/tests/test_models.py
    touch apps/$app/tests/test_services.py
    touch apps/$app/tests/test_views.py
    touch apps/$app/management/__init__.py
    touch apps/$app/management/commands/__init__.py
done
```

- [ ] **Step 3.2: Create accounts/apps.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/apps.py`:
```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    label = 'accounts'

    def ready(self):
        import apps.accounts.signals  # noqa
```
Create similar `apps.py` for every other app (replace name/label accordingly):

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/organisations/apps.py`:
```python
from django.apps import AppConfig
class OrganisationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organisations'
    label = 'organisations'
    def ready(self):
        import apps.organisations.signals  # noqa
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/invitations/apps.py`:
```python
from django.apps import AppConfig
class InvitationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invitations'
    label = 'invitations'
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/locations/apps.py`:
```python
from django.apps import AppConfig
class LocationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.locations'
    label = 'locations'
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/departments/apps.py`:
```python
from django.apps import AppConfig
class DepartmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.departments'
    label = 'departments'
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/employees/apps.py`:
```python
from django.apps import AppConfig
class EmployeesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.employees'
    label = 'employees'
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/documents/apps.py`:
```python
from django.apps import AppConfig
class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'
    label = 'documents'
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/audit/apps.py`:
```python
from django.apps import AppConfig
class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    label = 'audit'
```

- [ ] **Step 3.3: Create accounts/models.py (Custom User)**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/models.py`:
```python
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    CONTROL_TOWER = 'CONTROL_TOWER', 'Control Tower'
    ORG_ADMIN = 'ORG_ADMIN', 'Organisation Admin'
    EMPLOYEE = 'EMPLOYEE', 'Employee'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.CONTROL_TOWER)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.EMPLOYEE)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users',
    )
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_onboarding_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} ({self.role})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email
```

- [ ] **Step 3.4: Create organisations/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/organisations/models.py`:
```python
import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class OrganisationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Payment'
    PAID = 'PAID', 'Paid'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class Organisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OrganisationStatus.choices,
        default=OrganisationStatus.PENDING,
    )
    licence_count = models.PositiveIntegerField(default=0)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_organisations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organisations'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Organisation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.status})'


class OrganisationStateTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='state_transitions',
    )
    from_status = models.CharField(max_length=20, choices=OrganisationStatus.choices)
    to_status = models.CharField(max_length=20, choices=OrganisationStatus.choices)
    transitioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='org_transitions',
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organisation_state_transitions'
        ordering = ['-created_at']
```

- [ ] **Step 3.5: Create invitations/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/invitations/models.py`:
```python
import uuid
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone


class InvitationRole(models.TextChoices):
    ORG_ADMIN = 'ORG_ADMIN', 'Organisation Admin'
    EMPLOYEE = 'EMPLOYEE', 'Employee'


class InvitationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    EXPIRED = 'EXPIRED', 'Expired'
    REVOKED = 'REVOKED', 'Revoked'


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=64, unique=True, blank=True)
    email = models.EmailField()
    organisation = models.ForeignKey(
        'organisations.Organisation',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    role = models.CharField(max_length=20, choices=InvitationRole.choices)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='sent_invitations',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
    )
    email_sent = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invitations'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)[:64]
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.status == InvitationStatus.PENDING and not self.is_expired

    def __str__(self):
        return f'Invite({self.email}, {self.role}, {self.status})'
```

- [ ] **Step 3.6: Create locations/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/locations/models.py`:
```python
import uuid
from django.db import models


class OfficeLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='locations',
    )
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'office_locations'
        unique_together = [('organisation', 'name')]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.organisation.name})'
```

- [ ] **Step 3.7: Create departments/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/departments/models.py`:
```python
import uuid
from django.db import models


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='departments',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        unique_together = [('organisation', 'name')]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.organisation.name})'
```

- [ ] **Step 3.8: Create employees/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/employees/models.py`:
```python
import uuid
from django.conf import settings
from django.db import models


class EmploymentType(models.TextChoices):
    FULL_TIME = 'FULL_TIME', 'Full Time'
    PART_TIME = 'PART_TIME', 'Part Time'
    CONTRACT = 'CONTRACT', 'Contract'
    INTERN = 'INTERN', 'Intern'


class EmployeeStatus(models.TextChoices):
    INVITED = 'INVITED', 'Invited'
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    TERMINATED = 'TERMINATED', 'Terminated'


class GenderChoice(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER = 'OTHER', 'Other'
    PREFER_NOT_TO_SAY = 'PREFER_NOT_TO_SAY', 'Prefer Not To Say'


class MaritalStatus(models.TextChoices):
    SINGLE = 'SINGLE', 'Single'
    MARRIED = 'MARRIED', 'Married'
    DIVORCED = 'DIVORCED', 'Divorced'
    WIDOWED = 'WIDOWED', 'Widowed'


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='employees',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_record',
    )
    employee_code = models.CharField(max_length=20)
    department = models.ForeignKey(
        'departments.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees',
    )
    office_location = models.ForeignKey(
        'locations.OfficeLocation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees',
    )
    designation = models.CharField(max_length=255, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    status = models.CharField(
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.INVITED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employees'
        unique_together = [('organisation', 'employee_code')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.employee_code} - {self.user.full_name}'


class EmployeeProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GenderChoice.choices, blank=True)
    marital_status = models.CharField(max_length=20, choices=MaritalStatus.choices, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    phone_personal = models.CharField(max_length=20, blank=True)
    phone_emergency = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_relation = models.CharField(max_length=100, blank=True)
    address_line1 = models.TextField(blank=True)
    address_line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee_profiles'

    def __str__(self):
        return f'Profile({self.employee.employee_code})'


class EducationRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='education_records',
    )
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'education_records'
        ordering = ['-end_year', '-start_year']

    def __str__(self):
        return f'{self.degree} at {self.institution}'
```

- [ ] **Step 3.9: Create documents/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/documents/models.py`:
```python
import uuid
from django.conf import settings
from django.db import models


class DocumentType(models.TextChoices):
    PAN = 'PAN', 'PAN Card'
    AADHAAR = 'AADHAAR', 'Aadhaar Card'
    EDUCATION_CERT = 'EDUCATION_CERT', 'Education Certificate'
    EMPLOYMENT_LETTER = 'EMPLOYMENT_LETTER', 'Employment Letter'
    OTHER = 'OTHER', 'Other'


class DocumentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    VERIFIED = 'VERIFIED', 'Verified'
    REJECTED = 'REJECTED', 'Rejected'


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file_key = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_documents',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document_type} - {self.employee.employee_code}'
```

- [ ] **Step 3.10: Create audit/models.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/audit/models.py`:
```python
import uuid
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    organisation = models.ForeignKey(
        'organisations.Organisation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} by {self.actor_id} at {self.created_at}'
```

- [ ] **Step 3.11: Run makemigrations**

```bash
cd /home/jeet/PycharmProjects/clarisal/backend
# Activate the venv first
source ../.venv/bin/activate
# Install requirements
pip install -r requirements.txt
# Run migrations
python manage.py makemigrations accounts organisations invitations locations departments employees documents audit
```

Expected output: 8 migration files created, Django resolves circular FKs automatically via dependency ordering.

- [ ] **Step 3.12: Commit models and migrations**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add backend/apps/ backend/calrisal/
git commit -m "feat: create all Django apps and database models"
```

---

## Task 4: JWT Auth Endpoints + Permissions + Exception Handler

**Files:**
- Create: `backend/apps/accounts/serializers.py`
- Create: `backend/apps/accounts/views.py`
- Create: `backend/apps/accounts/urls.py`
- Create: `backend/apps/accounts/permissions.py`
- Create: `backend/apps/accounts/exceptions.py`
- Create: `backend/apps/accounts/tests/test_views.py`

- [ ] **Step 4.1: Write failing auth tests**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/tests/test_views.py`:
```python
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ct_user(db):
    return User.objects.create_user(
        email='ct@calrisal.com',
        password='TestPass@123',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_tokens_and_user(self, api_client, ct_user):
        response = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['role'] == UserRole.CONTROL_TOWER
        assert data['user']['email'] == 'ct@calrisal.com'

    def test_login_wrong_password_returns_401(self, api_client, ct_user):
        response = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'wrongpassword',
        }, format='json')
        assert response.status_code == 401

    def test_login_inactive_user_returns_401(self, api_client, db):
        User.objects.create_user(
            email='inactive@calrisal.com',
            password='TestPass@123',
            is_active=False,
        )
        response = api_client.post('/api/auth/login/', {
            'email': 'inactive@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        assert response.status_code == 401

    def test_me_returns_current_user(self, api_client, ct_user):
        login = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 200
        assert response.json()['email'] == 'ct@calrisal.com'

    def test_logout_blacklists_refresh_token(self, api_client, ct_user):
        login = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        response = api_client.post('/api/auth/logout/', {
            'refresh': login.json()['refresh']
        }, format='json')
        assert response.status_code == 200
        # Attempt to refresh with blacklisted token
        refresh_response = api_client.post('/api/auth/refresh/', {
            'refresh': login.json()['refresh']
        }, format='json')
        assert refresh_response.status_code == 401
```

- [ ] **Step 4.2: Run tests — verify they fail**

```bash
cd /home/jeet/PycharmProjects/clarisal/backend
pytest apps/accounts/tests/test_views.py -v
```

Expected: Multiple failures — serializers/views not yet implemented.

- [ ] **Step 4.3: Create accounts/serializers.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/serializers.py`:
```python
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['org_id'] = str(user.organisation_id) if user.organisation_id else None
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'org_id': str(self.user.organisation_id) if self.user.organisation_id else None,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'organisation_id', 'is_active']
        read_only_fields = ['id', 'email', 'role', 'organisation_id', 'is_active']
```

- [ ] **Step 4.4: Create accounts/views.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/views.py`:
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import CustomTokenObtainPairSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except TokenError:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
```

- [ ] **Step 4.5: Create accounts/urls.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/urls.py`:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, MeView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
]
```

- [ ] **Step 4.6: Create accounts/permissions.py**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/permissions.py`:
```python
from rest_framework.permissions import BasePermission
from .models import UserRole


class IsControlTowerUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.CONTROL_TOWER
        )


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.ORG_ADMIN
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.EMPLOYEE
        )


class IsOrgAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [UserRole.CONTROL_TOWER, UserRole.ORG_ADMIN]
        )


class BelongsToActiveOrg(BasePermission):
    """
    Ensures Org Admin and Employee users can only act if their org is PAID or ACTIVE.
    Control Tower users always pass.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == UserRole.CONTROL_TOWER:
            return True
        org = request.user.organisation
        return org is not None and org.status in ['PAID', 'ACTIVE']
```

- [ ] **Step 4.7: Create accounts/exceptions.py (custom error handler)**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/exceptions.py`:
```python
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
```

- [ ] **Step 4.8: Create conftest.py and pytest.ini**

Create `/home/jeet/PycharmProjects/clarisal/backend/conftest.py`:
```python
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calrisal.settings.development')
```

Create `/home/jeet/PycharmProjects/clarisal/backend/pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = calrisal.settings.development
python_files = tests/test_*.py
python_classes = Test
python_functions = test_
addopts = -v --tb=short
```

- [ ] **Step 4.9: Run tests — verify they pass**

```bash
cd /home/jeet/PycharmProjects/clarisal/backend
# Apply migrations first
python manage.py migrate
pytest apps/accounts/tests/test_views.py -v
```

Expected:
```
PASSED apps/accounts/tests/test_views.py::TestLogin::test_login_returns_tokens_and_user
PASSED apps/accounts/tests/test_views.py::TestLogin::test_login_wrong_password_returns_401
PASSED apps/accounts/tests/test_views.py::TestLogin::test_login_inactive_user_returns_401
PASSED apps/accounts/tests/test_views.py::TestLogin::test_me_returns_current_user
PASSED apps/accounts/tests/test_views.py::TestLogin::test_logout_blacklists_refresh_token
5 passed
```

- [ ] **Step 4.10: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add backend/apps/accounts/ backend/conftest.py backend/pytest.ini
git commit -m "feat: implement JWT auth endpoints with custom payload (role + org_id)"
```

---

## Task 5: Seed Management Command + empty signals

**Files:**
- Create: `backend/apps/accounts/management/commands/seed_control_tower.py`
- Create: `backend/apps/accounts/signals.py`
- Create: all remaining `signals.py` stubs

- [ ] **Step 5.1: Create seed command**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/management/commands/seed_control_tower.py`:
```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
import os


class Command(BaseCommand):
    help = 'Creates the initial Control Tower superuser and permission groups'

    def handle(self, *args, **options):
        from apps.accounts.models import User, UserRole

        # Create permission groups
        for group_name in ['control_tower', 'org_admin', 'employee']:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  Created group: {group_name}')

        # Create Control Tower user
        email = os.environ.get('CONTROL_TOWER_EMAIL', 'admin@calrisal.com')
        password = os.environ.get('CONTROL_TOWER_PASSWORD', 'CalrisalAdmin@2024!')

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Control Tower user {email} already exists, skipping.'))
            return

        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Control',
            last_name='Tower',
            role=UserRole.CONTROL_TOWER,
        )
        ct_group = Group.objects.get(name='control_tower')
        user.groups.add(ct_group)

        self.stdout.write(self.style.SUCCESS(f'Control Tower user created: {email}'))
        self.stdout.write(self.style.WARNING('IMPORTANT: Change the default password in production!'))
```

- [ ] **Step 5.2: Create empty signals stubs for all apps**

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/accounts/signals.py`:
```python
# Auth signals — audit logging for login/logout will be added in Phase 2
```

Create `/home/jeet/PycharmProjects/clarisal/backend/apps/organisations/signals.py`:
```python
# Organisation signals — audit logging for state transitions will be added in Phase 2
```

Create stubs for remaining apps (invitations, locations, departments, employees, documents):
```python
# Signals for this app will be implemented in later phases
```

- [ ] **Step 5.3: Test seed command**

```bash
cd /home/jeet/PycharmProjects/clarisal/backend
python manage.py seed_control_tower
```

Expected:
```
Created group: control_tower
Created group: org_admin
Created group: employee
Control Tower user created: admin@calrisal.com
IMPORTANT: Change the default password in production!
```

- [ ] **Step 5.4: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add backend/apps/
git commit -m "feat: add seed_control_tower management command and permission groups"
```

---

## Task 6: Frontend Scaffold (React + Vite + TypeScript + Tailwind + shadcn/ui)

**Files:**
- Create: `frontend/` Vite project
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/components.json`

- [ ] **Step 6.1: Create Vite project**

```bash
cd /home/jeet/PycharmProjects/clarisal
npm create vite@latest frontend -- --template react-ts
cd frontend
```

- [ ] **Step 6.2: Install all dependencies**

```bash
cd /home/jeet/PycharmProjects/clarisal/frontend
npm install
npm install \
  react-router-dom@7 \
  @tanstack/react-query \
  axios \
  class-variance-authority \
  clsx \
  tailwind-merge \
  lucide-react \
  @radix-ui/react-dialog \
  @radix-ui/react-dropdown-menu \
  @radix-ui/react-label \
  @radix-ui/react-select \
  @radix-ui/react-separator \
  @radix-ui/react-slot \
  @radix-ui/react-toast \
  @radix-ui/react-tooltip \
  @radix-ui/react-avatar \
  @radix-ui/react-badge \
  @radix-ui/react-progress \
  @radix-ui/react-tabs \
  sonner

npm install -D \
  tailwindcss \
  @tailwindcss/vite \
  autoprefixer \
  postcss \
  @types/node \
  playwright \
  @playwright/test
```

- [ ] **Step 6.3: Configure vite.config.ts**

Create `/home/jeet/PycharmProjects/clarisal/frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
```

- [ ] **Step 6.4: Configure Tailwind CSS 4**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/index.css`:
```css
@import "tailwindcss";

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
    --sidebar-background: 222.2 84% 4.9%;
    --sidebar-foreground: 210 40% 98%;
    --sidebar-primary: 221.2 83.2% 53.3%;
    --sidebar-primary-foreground: 210 40% 98%;
    --sidebar-accent: 217.2 32.6% 17.5%;
    --sidebar-accent-foreground: 210 40% 98%;
    --sidebar-border: 217.2 32.6% 17.5%;
    --sidebar-ring: 221.2 83.2% 53.3%;
  }
}

@layer base {
  * {
    border-color: hsl(var(--border));
  }
  body {
    background-color: hsl(var(--background));
    color: hsl(var(--foreground));
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
}
```

- [ ] **Step 6.5: Add tsconfig path aliases**

Modify `/home/jeet/PycharmProjects/clarisal/frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 6.6: Create lib/utils.ts (shadcn/ui utility)**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/lib/utils.ts`:
```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 6.7: Verify frontend builds**

```bash
cd /home/jeet/PycharmProjects/clarisal/frontend
npm run build
```

Expected: Build completes with no errors.

- [ ] **Step 6.8: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add frontend/
git commit -m "feat: scaffold React+Vite+TypeScript frontend with Tailwind 4 and shadcn/ui deps"
```

---

## Task 7: Auth Types + API Client + RBAC Helpers

**Files:**
- Create: `frontend/src/types/auth.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/rbac.ts`

- [ ] **Step 7.1: Create types/auth.ts**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/types/auth.ts`:
```typescript
export type UserRole = 'CONTROL_TOWER' | 'ORG_ADMIN' | 'EMPLOYEE'

export interface AuthUser {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: UserRole
  org_id: string | null
  is_active: boolean
}

export interface LoginResponse {
  access: string
  refresh: string
  user: Omit<AuthUser, 'full_name' | 'is_active'>
}

export interface ApiError {
  error?: string
  detail?: string
  [key: string]: unknown
}
```

- [ ] **Step 7.2: Create lib/api.ts**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/lib/api.ts`:
```typescript
import axios, { type AxiosError } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

// Handle 401 — try token refresh once, then redirect to login
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean }

    if (error.response?.status === 401 && !original?._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshSubscribers.push((token: string) => {
            if (original) {
              original.headers = original.headers ?? {}
              original.headers.Authorization = `Bearer ${token}`
              resolve(api(original))
            }
          })
        })
      }

      if (original) {
        original._retry = true
      }
      isRefreshing = true

      try {
        const refresh = localStorage.getItem('refresh_token')
        if (!refresh) throw new Error('No refresh token')

        const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
        localStorage.setItem('access_token', data.access)
        onRefreshed(data.access)
        isRefreshing = false

        if (original) {
          original.headers = original.headers ?? {}
          original.headers.Authorization = `Bearer ${data.access}`
          return api(original)
        }
      } catch {
        isRefreshing = false
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/auth/login'
      }
    }

    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 7.3: Create lib/rbac.ts**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/lib/rbac.ts`:
```typescript
import type { UserRole } from '@/types/auth'

export function isControlTower(role: UserRole | undefined): boolean {
  return role === 'CONTROL_TOWER'
}

export function isOrgAdmin(role: UserRole | undefined): boolean {
  return role === 'ORG_ADMIN'
}

export function isEmployee(role: UserRole | undefined): boolean {
  return role === 'EMPLOYEE'
}

export function isOrgAdminOrAbove(role: UserRole | undefined): boolean {
  return role === 'CONTROL_TOWER' || role === 'ORG_ADMIN'
}

export function getDefaultRoute(role: UserRole | undefined): string {
  switch (role) {
    case 'CONTROL_TOWER':
      return '/ct/dashboard'
    case 'ORG_ADMIN':
      return '/org/dashboard'
    case 'EMPLOYEE':
      return '/me/dashboard'
    default:
      return '/auth/login'
  }
}
```

- [ ] **Step 7.4: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add frontend/src/types/ frontend/src/lib/
git commit -m "feat: add auth types, axios API client with token refresh, and RBAC helpers"
```

---

## Task 8: AuthContext + useAuth Hook + ProtectedRoute

**Files:**
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/components/auth/ProtectedRoute.tsx`

- [ ] **Step 8.1: Create AuthContext.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/context/AuthContext.tsx`:
```typescript
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { AuthUser, LoginResponse, UserRole } from '@/types/auth'
import api from '@/lib/api'
import { getDefaultRoute } from '@/lib/rbac'

interface AuthContextType {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<string>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.get('/auth/me/')
        .then((res) => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string): Promise<string> => {
    const response = await api.post<LoginResponse>('/auth/login/', { email, password })
    const { access, refresh, user: userData } = response.data
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    // Fetch full user object (includes full_name, is_active)
    const meResponse = await api.get<AuthUser>('/auth/me/', {
      headers: { Authorization: `Bearer ${access}` },
    })
    setUser(meResponse.data)
    return getDefaultRoute(userData.role as UserRole)
  }

  const logout = async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        await api.post('/auth/logout/', { refresh })
      } catch {
        // Ignore errors on logout
      }
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider')
  return ctx
}
```

- [ ] **Step 8.2: Create hooks/useAuth.ts**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/hooks/useAuth.ts`:
```typescript
import { useAuthContext } from '@/context/AuthContext'

export function useAuth() {
  return useAuthContext()
}
```

- [ ] **Step 8.3: Create ProtectedRoute.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/components/auth/ProtectedRoute.tsx`:
```typescript
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { UserRole } from '@/types/auth'
import { useAuth } from '@/hooks/useAuth'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Wrong role — send to their correct dashboard
    const roleRoutes: Record<UserRole, string> = {
      CONTROL_TOWER: '/ct/dashboard',
      ORG_ADMIN: '/org/dashboard',
      EMPLOYEE: '/me/dashboard',
    }
    return <Navigate to={roleRoutes[user.role]} replace />
  }

  return <Outlet />
}
```

- [ ] **Step 8.4: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add frontend/src/context/ frontend/src/hooks/ frontend/src/components/auth/
git commit -m "feat: implement AuthContext, useAuth hook, and ProtectedRoute component"
```

---

## Task 9: Role-Specific Layouts + Routing + Auth Pages

**Files:**
- Create: `frontend/src/components/layouts/CTLayout.tsx`
- Create: `frontend/src/components/layouts/OrgLayout.tsx`
- Create: `frontend/src/components/layouts/EmployeeLayout.tsx`
- Create: `frontend/src/routes/index.tsx`
- Create: `frontend/src/pages/auth/LoginPage.tsx`
- Create: `frontend/src/pages/auth/InviteAcceptPage.tsx`
- Create: `frontend/src/pages/auth/RequestPasswordResetPage.tsx`
- Create: `frontend/src/pages/ct/DashboardPage.tsx`
- Create: `frontend/src/pages/org/DashboardPage.tsx`
- Create: `frontend/src/pages/employee/DashboardPage.tsx`

- [ ] **Step 9.1: Create shared sidebar nav component**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/components/layouts/SidebarNav.tsx`:
```typescript
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
}

interface SidebarNavProps {
  items: NavItem[]
  title: string
  subtitle?: string
}

export function SidebarNav({ items, title, subtitle }: SidebarNavProps) {
  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[hsl(var(--sidebar-background))] border-r border-[hsl(var(--sidebar-border))]">
      <div className="flex h-16 items-center px-6 border-b border-[hsl(var(--sidebar-border))]">
        <div>
          <p className="text-sm font-semibold text-[hsl(var(--sidebar-foreground))]">{title}</p>
          {subtitle && (
            <p className="text-xs text-[hsl(var(--sidebar-foreground))] opacity-60">{subtitle}</p>
          )}
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {items.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-[hsl(var(--sidebar-primary))] text-[hsl(var(--sidebar-primary-foreground))]'
                  : 'text-[hsl(var(--sidebar-foreground))] opacity-70 hover:opacity-100 hover:bg-[hsl(var(--sidebar-accent))]'
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
```

- [ ] **Step 9.2: Create CTLayout.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/components/layouts/CTLayout.tsx`:
```typescript
import { Outlet } from 'react-router-dom'
import { Building2, LayoutDashboard, LogOut } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { useAuth } from '@/hooks/useAuth'
import { useNavigate } from 'react-router-dom'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/ct/dashboard', icon: LayoutDashboard },
  { label: 'Organisations', href: '/ct/organisations', icon: Building2 },
]

export function CTLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))]">
      <SidebarNav items={navItems} title="Calrisal" subtitle="Control Tower" />
      <div className="flex flex-1 flex-col overflow-hidden pl-64">
        <header className="flex h-16 items-center justify-between border-b bg-background px-6">
          <div />
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.3: Create OrgLayout.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/components/layouts/OrgLayout.tsx`:
```typescript
import { Outlet } from 'react-router-dom'
import { LayoutDashboard, MapPin, Building, Users, LogOut } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { useAuth } from '@/hooks/useAuth'
import { useNavigate } from 'react-router-dom'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/org/dashboard', icon: LayoutDashboard },
  { label: 'Locations', href: '/org/locations', icon: MapPin },
  { label: 'Departments', href: '/org/departments', icon: Building },
  { label: 'Employees', href: '/org/employees', icon: Users },
]

export function OrgLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))]">
      <SidebarNav items={navItems} title="Calrisal" subtitle="HR Portal" />
      <div className="flex flex-1 flex-col overflow-hidden pl-64">
        <header className="flex h-16 items-center justify-between border-b bg-background px-6">
          <div />
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.4: Create EmployeeLayout.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/components/layouts/EmployeeLayout.tsx`:
```typescript
import { Outlet } from 'react-router-dom'
import { LayoutDashboard, User, GraduationCap, FileText, Settings, LogOut } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { useAuth } from '@/hooks/useAuth'
import { useNavigate } from 'react-router-dom'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/me/dashboard', icon: LayoutDashboard },
  { label: 'My Profile', href: '/me/profile', icon: User },
  { label: 'Education', href: '/me/education', icon: GraduationCap },
  { label: 'Documents', href: '/me/documents', icon: FileText },
  { label: 'Settings', href: '/me/settings', icon: Settings },
]

export function EmployeeLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))]">
      <SidebarNav items={navItems} title="Calrisal" subtitle="Employee Portal" />
      <div className="flex flex-1 flex-col overflow-hidden pl-64">
        <header className="flex h-16 items-center justify-between border-b bg-background px-6">
          <div />
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.full_name || user?.email}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.5: Create placeholder dashboard pages**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/pages/ct/DashboardPage.tsx`:
```typescript
export function CTDashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-foreground">Control Tower Dashboard</h1>
      <p className="mt-1 text-sm text-muted-foreground">Overview of all organisations on the platform.</p>
      <div className="mt-8 rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
        Dashboard stats coming in Phase 2
      </div>
    </div>
  )
}
```

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/pages/org/DashboardPage.tsx`:
```typescript
export function OrgDashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-foreground">Organisation Dashboard</h1>
      <p className="mt-1 text-sm text-muted-foreground">Manage your organisation's people and structure.</p>
      <div className="mt-8 rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
        Dashboard stats coming in Phase 3
      </div>
    </div>
  )
}
```

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/pages/employee/DashboardPage.tsx`:
```typescript
export function EmployeeDashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-foreground">My Dashboard</h1>
      <p className="mt-1 text-sm text-muted-foreground">Your profile and documents at a glance.</p>
      <div className="mt-8 rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
        Profile completion card coming in Phase 4
      </div>
    </div>
  )
}
```

- [ ] **Step 9.6: Create LoginPage.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/pages/auth/LoginPage.tsx`:
```typescript
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      const redirectTo = await login(email, password)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname
      navigate(from || redirectTo, { replace: true })
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: string } } }
      setError(axiosError.response?.data?.error || 'Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">Calrisal</h1>
          <p className="mt-2 text-sm text-white/60">Employee & Payroll Management</p>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Sign in to your account</h2>
          <p className="mt-1 text-sm text-muted-foreground">Enter your credentials to continue</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1.5">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                'transition-opacity hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-ring',
                isLoading && 'opacity-60 cursor-not-allowed'
              )}
            >
              {isLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <a href="/auth/reset-password" className="text-sm text-muted-foreground hover:text-foreground">
              Forgot your password?
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.7: Create InviteAcceptPage.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/pages/auth/InviteAcceptPage.tsx`:
```typescript
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '@/lib/api'
import { cn } from '@/lib/utils'

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [tokenValid, setTokenValid] = useState<boolean | null>(null)
  const [inviteInfo, setInviteInfo] = useState<{ email: string; role: string } | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    api.get(`/auth/invite/validate/${token}/`)
      .then((res) => {
        setTokenValid(true)
        setInviteInfo(res.data)
      })
      .catch(() => setTokenValid(false))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setError('')
    setIsLoading(true)
    try {
      await api.post('/auth/invite/accept/', { token, password, confirm_password: confirmPassword })
      navigate('/auth/login', { state: { message: 'Password set successfully. Please sign in.' } })
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { error?: string } } }
      setError(axiosError.response?.data?.error || 'Failed to set password. The link may have expired.')
    } finally {
      setIsLoading(false)
    }
  }

  if (tokenValid === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-white border-t-transparent" />
      </div>
    )
  }

  if (tokenValid === false) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Invitation Expired</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            This invitation link is invalid or has expired. Please contact your administrator to resend the invite.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">Calrisal</h1>
          <p className="mt-2 text-sm text-white/60">Set up your account</p>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-foreground">Create your password</h2>
          {inviteInfo && (
            <p className="mt-1 text-sm text-muted-foreground">
              Setting up account for <strong>{inviteInfo.email}</strong>
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">New password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Minimum 8 characters"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Confirm password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Repeat your password"
              />
            </div>

            {error && (
              <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                'transition-opacity hover:opacity-90',
                isLoading && 'opacity-60 cursor-not-allowed'
              )}
            >
              {isLoading ? 'Setting password…' : 'Set password & sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.8: Create RequestPasswordResetPage.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/pages/auth/RequestPasswordResetPage.tsx`:
```typescript
import { useState } from 'react'
import api from '@/lib/api'
import { cn } from '@/lib/utils'

export function RequestPasswordResetPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await api.post('/auth/password-reset/request/', { email })
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setIsLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--sidebar-background))]">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">Calrisal</h1>
        </div>
        <div className="rounded-xl bg-white p-8 shadow-2xl">
          {submitted ? (
            <div className="text-center">
              <h2 className="text-xl font-semibold text-foreground">Check your email</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                If an account with <strong>{email}</strong> exists, we've sent a password reset link. Check your inbox.
              </p>
              <a href="/auth/login" className="mt-4 block text-sm text-primary hover:underline">
                Back to sign in
              </a>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-foreground">Reset your password</h2>
              <p className="mt-1 text-sm text-muted-foreground">Enter your email and we'll send a reset link.</p>
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Email address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    placeholder="you@company.com"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className={cn(
                    'w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                    'transition-opacity hover:opacity-90',
                    isLoading && 'opacity-60 cursor-not-allowed'
                  )}
                >
                  {isLoading ? 'Sending…' : 'Send reset link'}
                </button>
              </form>
              <div className="mt-4 text-center">
                <a href="/auth/login" className="text-sm text-muted-foreground hover:text-foreground">
                  Back to sign in
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.9: Create routes/index.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/routes/index.tsx`:
```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { CTLayout } from '@/components/layouts/CTLayout'
import { OrgLayout } from '@/components/layouts/OrgLayout'
import { EmployeeLayout } from '@/components/layouts/EmployeeLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { InviteAcceptPage } from '@/pages/auth/InviteAcceptPage'
import { RequestPasswordResetPage } from '@/pages/auth/RequestPasswordResetPage'
import { CTDashboardPage } from '@/pages/ct/DashboardPage'
import { OrgDashboardPage } from '@/pages/org/DashboardPage'
import { EmployeeDashboardPage } from '@/pages/employee/DashboardPage'

export const router = createBrowserRouter([
  // Public auth routes
  {
    path: '/auth/login',
    element: <LoginPage />,
  },
  {
    path: '/auth/invite/:token',
    element: <InviteAcceptPage />,
  },
  {
    path: '/auth/reset-password',
    element: <RequestPasswordResetPage />,
  },

  // Control Tower routes
  {
    element: <ProtectedRoute allowedRoles={['CONTROL_TOWER']} />,
    children: [
      {
        element: <CTLayout />,
        children: [
          { path: '/ct/dashboard', element: <CTDashboardPage /> },
          // Phase 2: CT organisation routes will be added here
        ],
      },
    ],
  },

  // Organisation Admin routes
  {
    element: <ProtectedRoute allowedRoles={['ORG_ADMIN']} />,
    children: [
      {
        element: <OrgLayout />,
        children: [
          { path: '/org/dashboard', element: <OrgDashboardPage /> },
          // Phase 3: Locations, departments, employees routes will be added here
        ],
      },
    ],
  },

  // Employee routes
  {
    element: <ProtectedRoute allowedRoles={['EMPLOYEE']} />,
    children: [
      {
        element: <EmployeeLayout />,
        children: [
          { path: '/me/dashboard', element: <EmployeeDashboardPage /> },
          // Phase 4: Profile, education, documents routes will be added here
        ],
      },
    ],
  },

  // Root redirect
  { path: '/', element: <Navigate to="/auth/login" replace /> },
  { path: '*', element: <Navigate to="/auth/login" replace /> },
])
```

- [ ] **Step 9.10: Update App.tsx and main.tsx**

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/App.tsx`:
```typescript
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/context/AuthContext'
import { router } from '@/routes'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
```

Create `/home/jeet/PycharmProjects/clarisal/frontend/src/main.tsx`:
```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 9.11: Verify frontend builds and runs**

```bash
cd /home/jeet/PycharmProjects/clarisal/frontend
npm run build
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 9.12: Commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add frontend/src/
git commit -m "feat: add role-specific layouts, auth pages, routing, and app bootstrap"
```

---

## Task 10: End-to-End Verification

**Goal:** Verify the entire Phase 1 stack works together — docker-compose up, migrate, seed, login via API, login via UI.

- [ ] **Step 10.1: Copy .env from example**

```bash
cd /home/jeet/PycharmProjects/clarisal
cp .env.example .env
# Edit .env to fill in SECRET_KEY:
# SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
```

- [ ] **Step 10.2: Start all services**

```bash
cd /home/jeet/PycharmProjects/clarisal
docker-compose up --build -d
# Wait for health checks
docker-compose ps
```

Expected: All 6 services (db, redis, backend, celery, celery-beat, frontend) show as healthy/running.

- [ ] **Step 10.3: Run migrations and seed**

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_control_tower
```

Expected:
```
Created group: control_tower
Created group: org_admin
Created group: employee
Control Tower user created: admin@calrisal.com
```

- [ ] **Step 10.4: Verify health endpoint**

```bash
curl http://localhost:8000/health/
```

Expected: `{"status": "ok", "service": "calrisal-api"}`

- [ ] **Step 10.5: Verify login via API**

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@calrisal.com","password":"CalrisalAdmin@2024!"}'
```

Expected: Response with `access`, `refresh`, and `user.role == "CONTROL_TOWER"`.

- [ ] **Step 10.6: Verify /me/ endpoint with token**

```bash
# Use the access token from step 10.5
ACCESS_TOKEN="<paste access token here>"
curl http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Expected: `{"id":"...","email":"admin@calrisal.com","role":"CONTROL_TOWER",...}`

- [ ] **Step 10.7: Verify login via UI**

Open browser at `http://localhost:5173/auth/login`.
Login with `admin@calrisal.com` / `CalrisalAdmin@2024!`.
Expected: Redirected to `/ct/dashboard` with the Control Tower dashboard visible.

- [ ] **Step 10.8: Run backend test suite**

```bash
docker-compose exec backend pytest apps/accounts/tests/ -v
```

Expected: 5 tests pass.

- [ ] **Step 10.9: Final Phase 1 commit**

```bash
cd /home/jeet/PycharmProjects/clarisal
git add .
git commit -m "feat: Phase 1 complete — Docker foundation, Django models, JWT auth, React frontend with auth + routing"
```

---

## Phase 1 Complete ✓

**What you now have:**
- Docker Compose with all 6 services (PostgreSQL, Redis, Django, Celery, Celery Beat, Vite frontend)
- All 8 Django apps with complete database models and migrations
- JWT auth (login, refresh, logout, /me/) with custom role+org_id payload
- Permission classes for all three roles
- Custom exception handler
- Seed command for Control Tower user
- React frontend with auth pages, AuthContext, role-aware routing, three layout shells
- pytest-django test suite for auth endpoints

**Next:** Phase 2 plan — Invitations + Organisation Lifecycle (Control Tower Module)

---

*Plan generated: 2026-03-28 — calrisal Phase 1 Foundation*
