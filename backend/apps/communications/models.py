import uuid

from django.conf import settings
from django.db import models


class NoticeStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED', 'Archived'


class NoticeAudienceType(models.TextChoices):
    ALL_EMPLOYEES = 'ALL_EMPLOYEES', 'All Employees'
    DEPARTMENTS = 'DEPARTMENTS', 'Departments'
    OFFICE_LOCATIONS = 'OFFICE_LOCATIONS', 'Office Locations'
    SPECIFIC_EMPLOYEES = 'SPECIFIC_EMPLOYEES', 'Specific Employees'


class Notice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='notices',
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    audience_type = models.CharField(max_length=30, choices=NoticeAudienceType.choices, default=NoticeAudienceType.ALL_EMPLOYEES)
    status = models.CharField(max_length=20, choices=NoticeStatus.choices, default=NoticeStatus.DRAFT)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_notices',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_notices',
    )
    departments = models.ManyToManyField('departments.Department', blank=True, related_name='notices')
    office_locations = models.ManyToManyField('locations.OfficeLocation', blank=True, related_name='notices')
    employees = models.ManyToManyField('employees.Employee', blank=True, related_name='notices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notices'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status', 'published_at']),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.title}'
