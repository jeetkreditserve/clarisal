from django.conf import settings
from django.db import models

from apps.common.models import AuditedBaseModel


class AssetCondition(models.TextChoices):
    NEW = 'NEW', 'New'
    GOOD = 'GOOD', 'Good'
    FAIR = 'FAIR', 'Fair'
    POOR = 'POOR', 'Poor'
    DAMAGED = 'DAMAGED', 'Damaged'


class AssetLifecycleStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    ASSIGNED = 'ASSIGNED', 'Assigned'
    IN_MAINTENANCE = 'IN_MAINTENANCE', 'In Maintenance'
    RETIRED = 'RETIRED', 'Retired'
    LOST = 'LOST', 'Lost'
    RETURNED = 'RETURNED', 'Returned'


class AssetAssignmentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    RETURNED = 'RETURNED', 'Returned'
    LOST = 'LOST', 'Lost'


class AssetCategory(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='asset_categories',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'asset_categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organisation', 'name'],
                name='unique_asset_category_per_org',
            ),
        ]

    def __str__(self):
        return self.name


class AssetItem(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='asset_items',
    )
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='items',
    )
    name = models.CharField(max_length=200)
    asset_tag = models.CharField(
        max_length=100,
        blank=True,
        help_text='Unique asset tag/serial number',
    )
    serial_number = models.CharField(max_length=200, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    warranty_expiry = models.DateField(null=True, blank=True)
    condition = models.CharField(
        max_length=20,
        choices=AssetCondition.choices,
        default=AssetCondition.NEW,
    )
    lifecycle_status = models.CharField(
        max_length=20,
        choices=AssetLifecycleStatus.choices,
        default=AssetLifecycleStatus.AVAILABLE,
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'asset_items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'lifecycle_status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f'{self.name} ({self.asset_tag or self.serial_number or self.id})'


class AssetAssignment(AuditedBaseModel):
    asset = models.ForeignKey(
        AssetItem,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='asset_assignments',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    condition_on_issue = models.CharField(
        max_length=20,
        choices=AssetCondition.choices,
        default=AssetCondition.NEW,
    )
    condition_on_return = models.CharField(
        max_length=20,
        choices=AssetCondition.choices,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=AssetAssignmentStatus.choices,
        default=AssetAssignmentStatus.ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'asset_assignments'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['asset', 'status']),
        ]

    def __str__(self):
        return f'{self.asset.name} -> {self.employee}'


class AssetMaintenance(AuditedBaseModel):
    asset = models.ForeignKey(
        AssetItem,
        on_delete=models.CASCADE,
        related_name='maintenance_records',
    )
    maintenance_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    vendor = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'asset_maintenance'
        ordering = ['-scheduled_date']

    def __str__(self):
        return f'{self.asset.name}: {self.maintenance_type}'


class AssetIncident(AuditedBaseModel):
    asset = models.ForeignKey(
        AssetItem,
        on_delete=models.CASCADE,
        related_name='incidents',
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        related_name='asset_incidents',
    )
    incident_type = models.CharField(
        max_length=50,
        choices=[
            ('DAMAGE', 'Damage'),
            ('LOSS', 'Loss'),
            ('THEFT', 'Theft'),
            ('OTHER', 'Other'),
        ],
    )
    description = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'asset_incidents'
        ordering = ['-reported_at']

    def __str__(self):
        return f'{self.asset.name}: {self.incident_type}'
