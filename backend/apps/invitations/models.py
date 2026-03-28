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
