from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel


class AccessRoleScope(models.TextChoices):
    CONTROL_TOWER = "CONTROL_TOWER", "Control Tower"
    ORGANISATION = "ORGANISATION", "Organisation"


class DataScopeKind(models.TextChoices):
    ALL_ORGANISATIONS = "ALL_ORGANISATIONS", "All organisations"
    SELECTED_ORGANISATIONS = "SELECTED_ORGANISATIONS", "Selected organisations"
    CURRENT_ORGANISATION = "CURRENT_ORGANISATION", "Current organisation"
    ALL_EMPLOYEES = "ALL_EMPLOYEES", "All employees"
    OWN_RECORD = "OWN_RECORD", "Own record"
    REPORTING_TREE = "REPORTING_TREE", "Reporting tree"
    SELECTED_DEPARTMENTS = "SELECTED_DEPARTMENTS", "Selected departments"
    SELECTED_OFFICE_LOCATIONS = "SELECTED_OFFICE_LOCATIONS", "Selected office locations"
    SELECTED_LEGAL_ENTITIES = "SELECTED_LEGAL_ENTITIES", "Selected legal entities"
    SELECTED_COST_CENTRES = "SELECTED_COST_CENTRES", "Selected cost centres"
    SELECTED_EMPLOYMENT_TYPES = "SELECTED_EMPLOYMENT_TYPES", "Selected employment types"
    SELECTED_GRADES = "SELECTED_GRADES", "Selected grades"
    SELECTED_BANDS = "SELECTED_BANDS", "Selected bands"
    SELECTED_DESIGNATIONS = "SELECTED_DESIGNATIONS", "Selected designations"
    SELECTED_EMPLOYEES = "SELECTED_EMPLOYEES", "Selected employees"


class AccessPermission(AuditedBaseModel):
    code = models.CharField(max_length=160, unique=True)
    label = models.CharField(max_length=255)
    domain = models.CharField(max_length=32)
    resource = models.CharField(max_length=64)
    action = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "access_permissions"
        ordering = ["code"]

    def __str__(self):
        return self.code


class AccessRole(AuditedBaseModel):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_roles",
    )
    code = models.CharField(max_length=120)
    scope = models.CharField(max_length=32, choices=AccessRoleScope.choices)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    permissions: Any = models.ManyToManyField(
        AccessPermission,
        through="AccessRolePermission",
        related_name="roles",
    )

    class Meta:
        db_table = "access_roles"
        ordering = ["scope", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "code"],
                condition=Q(organisation__isnull=False),
                name="unique_org_access_role_code",
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=Q(organisation__isnull=True),
                name="unique_global_access_role_code",
            ),
        ]

    def __str__(self):
        return self.code


class AccessRolePermission(AuditedBaseModel):
    role = models.ForeignKey(
        AccessRole,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        AccessPermission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    class Meta:
        db_table = "access_role_permissions"
        ordering = ["role__code", "permission__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_permission_per_access_role",
            ),
        ]


class AccessRoleAssignment(AuditedBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_role_assignments",
    )
    role = models.ForeignKey(
        AccessRole,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    organisation = models.ForeignKey(
        "organisations.Organisation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_role_assignments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "access_role_assignments"
        ordering = ["role__scope", "role__name", "user__email"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "organisation"],
                condition=Q(organisation__isnull=False),
                name="unique_org_access_role_assignment",
            ),
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(organisation__isnull=True),
                name="unique_ct_access_role_assignment",
            ),
        ]

    def __str__(self):
        suffix = f" @ {self.organisation.name}" if self.organisation_id else ""
        return f"{self.user.email} -> {self.role.code}{suffix}"


class AccessScope(AuditedBaseModel):
    assignment = models.ForeignKey(
        AccessRoleAssignment,
        on_delete=models.CASCADE,
        related_name="scopes",
    )
    scope_kind = models.CharField(max_length=48, choices=DataScopeKind.choices)
    organisation = models.ForeignKey(
        "organisations.Organisation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    office_location = models.ForeignKey(
        "locations.OfficeLocation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    value_text = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "access_scopes"
        ordering = ["scope_kind", "created_at"]

    def __str__(self):
        return f"{self.assignment} -> {self.scope_kind}"
