from django.db import models

from apps.common.models import AuditedBaseModel


class NoticeStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    PUBLISHED = 'PUBLISHED', 'Published'
    EXPIRED = 'EXPIRED', 'Expired'
    ARCHIVED = 'ARCHIVED', 'Archived'


class NoticeAudienceType(models.TextChoices):
    ALL_EMPLOYEES = 'ALL_EMPLOYEES', 'All Employees'
    DEPARTMENTS = 'DEPARTMENTS', 'Departments'
    OFFICE_LOCATIONS = 'OFFICE_LOCATIONS', 'Office Locations'
    SPECIFIC_EMPLOYEES = 'SPECIFIC_EMPLOYEES', 'Specific Employees'


class NoticeCategory(models.TextChoices):
    GENERAL = 'GENERAL', 'General'
    HR_POLICY = 'HR_POLICY', 'HR Policy'
    OPERATIONS = 'OPERATIONS', 'Operations'
    CELEBRATION = 'CELEBRATION', 'Celebration'
    COMPLIANCE = 'COMPLIANCE', 'Compliance'
    URGENT = 'URGENT', 'Urgent'


class Notice(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='notices',
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(max_length=24, choices=NoticeCategory.choices, default=NoticeCategory.GENERAL)
    audience_type = models.CharField(max_length=30, choices=NoticeAudienceType.choices, default=NoticeAudienceType.ALL_EMPLOYEES)
    status = models.CharField(max_length=20, choices=NoticeStatus.choices, default=NoticeStatus.DRAFT)
    is_sticky = models.BooleanField(default=False)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    departments = models.ManyToManyField('departments.Department', blank=True, related_name='notices')
    office_locations = models.ManyToManyField('locations.OfficeLocation', blank=True, related_name='notices')
    employees = models.ManyToManyField('employees.Employee', blank=True, related_name='notices')

    class Meta:
        db_table = 'notices'
        ordering = ['-is_sticky', '-published_at', '-created_at']
        indexes = [
            models.Index(fields=['organisation', 'status', 'published_at']),
            models.Index(fields=['organisation', 'is_sticky', 'published_at']),
        ]

    def __str__(self):
        return f'{self.organisation.name} - {self.title}'
