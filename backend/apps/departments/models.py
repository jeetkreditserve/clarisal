from django.db import models

from apps.common.models import AuditedBaseModel


class Department(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='departments',
    )
    parent_department = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_departments',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'departments'
        unique_together = [('organisation', 'name')]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.organisation.name})'
