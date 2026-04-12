from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.notifications.models import NotificationKind
from apps.notifications.services import create_notification

from .services import list_documents_expiring_soon


@shared_task(name='documents.send_document_expiry_alerts')
def send_document_expiry_alerts() -> int:
    today = timezone.localdate()
    sent = 0
    for document in list_documents_expiring_soon(today=today):
        create_notification(
            recipient=document.employee.user,
            organisation=document.employee.organisation,
            kind=NotificationKind.GENERAL,
            title=f'Document expiring soon: {document.file_name}',
            body=f'Your {document.document_type} document expires on {document.expiry_date}. Please upload a renewed copy.',
            related_object=document,
        )
        sent += 1
    return sent
