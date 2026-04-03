from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.common.models import AuditedBaseModel


class NotificationKind(models.TextChoices):
    LEAVE_APPROVED = 'LEAVE_APPROVED', 'Leave Approved'
    LEAVE_REJECTED = 'LEAVE_REJECTED', 'Leave Rejected'
    LEAVE_CANCELLED = 'LEAVE_CANCELLED', 'Leave Cancelled'
    ATTENDANCE_REGULARIZATION_APPROVED = 'ATT_REG_APPROVED', 'Attendance Regularization Approved'
    ATTENDANCE_REGULARIZATION_REJECTED = 'ATT_REG_REJECTED', 'Attendance Regularization Rejected'
    COMPENSATION_APPROVED = 'COMP_APPROVED', 'Compensation Approved'
    COMPENSATION_REJECTED = 'COMP_REJECTED', 'Compensation Rejected'
    PAYROLL_FINALIZED = 'PAYROLL_FINALIZED', 'Payroll Finalized'
    GENERAL = 'GENERAL', 'General'


class Notification(AuditedBaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    kind = models.CharField(max_length=40, choices=NotificationKind.choices, default=NotificationKind.GENERAL)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=36, null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='notif_recipient_read_idx'),
        ]

    def __str__(self):
        return f'{self.kind} -> {self.recipient_id} | {self.title[:40]}'
