from django.db import models

from apps.common.models import AuditedBaseModel


class OfficeLocation(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='locations',
    )
    organisation_address = models.ForeignKey(
        'organisations.OrganisationAddress',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='office_locations',
    )
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    is_remote = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'office_locations'
        unique_together = [('organisation', 'name')]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.organisation.name})'
