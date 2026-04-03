import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clarisal.settings.development')

app = Celery('clarisal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
