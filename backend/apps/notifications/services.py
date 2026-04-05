from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import Notification


def create_notification(
    *,
    recipient,
    kind: str,
    title: str,
    body: str = '',
    organisation=None,
    related_object=None,
    actor=None,
) -> Notification:
    content_type = None
    object_id = None

    if related_object is not None:
        content_type = ContentType.objects.get_for_model(related_object.__class__)
        object_id = str(related_object.pk)

    return Notification.objects.create(
        recipient=recipient,
        organisation=organisation,
        kind=kind,
        title=title,
        body=body,
        content_type=content_type,
        object_id=object_id,
        created_by=actor,
        modified_by=actor,
    )


def mark_notification_read(notification: Notification, requesting_user) -> Notification:
    if notification.recipient_id != requesting_user.id:
        raise PermissionError("Cannot mark another user's notification as read.")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at', 'modified_at'])
    return notification


def mark_all_read(user) -> int:
    now = timezone.now()
    return Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True,
        read_at=now,
        modified_at=now,
    )
