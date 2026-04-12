# P38 - Granular RBAC and Data Visibility Scopes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace coarse `CONTROL_TOWER` / `ORG_ADMIN` / `EMPLOYEE` access checks with granular permission roles, permission sets, and data scopes for Control Tower users and organisation administrators.

**Architecture:** Add a focused `access_control` app that owns permission catalog, role assignments, field visibility, row-level scopes, and audit-friendly policy decisions. Existing DRF permission classes stay in place as compatibility gates, but views move to explicit `permission_code` checks and queryset scoping. This plan preserves current behavior by backfilling owner roles, then narrows access only after endpoints opt in.

**Tech Stack:** Django 4.2 | DRF | PostgreSQL | React 19 | TypeScript | TanStack Query | pytest | Vitest | Docker Compose

---

## Current Capability Answer

Role-based and scoped access is not implemented at the level needed for Control Tower or org admin delegation.

- Backend account roles are only `CONTROL_TOWER`, `ORG_ADMIN`, and `EMPLOYEE` in `backend/apps/accounts/models.py:14-17`.
- `OrganisationMembership` only stores `is_org_admin` and status in `backend/apps/organisations/models.py:623-667`; it has no role profile, permission set, department scope, location scope, or field visibility.
- `IsControlTowerUser` checks account type and impersonation write constraints, not module/action permissions, in `backend/apps/accounts/permissions.py:39-61`.
- `IsOrgAdmin` checks whether the user has any admin membership, not what that admin may access, in `backend/apps/accounts/permissions.py:64-76`.
- `BelongsToActiveOrg` validates active billing/access state and feature flag only, not row-level data visibility, in `backend/apps/accounts/permissions.py:93-119`.
- Frontend RBAC only chooses routes and coarse role booleans in `frontend/src/lib/rbac.ts:1-32`.

This means every active org admin has broad org-admin access today. The product cannot safely delegate payroll-only, finance-only, department-only, location-only, implementation-only, auditor-only, or support-only access.

## Benchmark Requirements

- SAP SuccessFactors RBP separates permission role, access population, target population, and role assignment. This plan mirrors that by separating `AccessRole`, `AccessRoleAssignment`, and `DataScope`. Source: https://help.sap.com/docs/successfactors-platform/implementing-role-based-permissions/f1d86a9f5be14fc8a337f21703249415.html
- Zoho People specific roles support location and department applicability for data-admin access. This plan implements department and office-location scopes as first-class data scopes. Source: https://www.zoho.com/people/help/adminguide/RolesEnhancementUPDdoc.html
- Darwinbox describes permission control by department, location, band, designation, business unit, assignments, and modules. This plan covers department, office location, legal entity, cost centre, employment type, grade/band, reporting tree, and module/action permissions. Source: https://darwinbox.com/blog/advanced-hrms-features
- Keka uses explicit user roles and implicit roles such as reporting manager, department head, and business head. This plan supports direct role assignments and computed scope helpers for managers and department heads. Source: https://help.keka.com/hc/en-us/articles/39946719445393-Overview-Roles-Permissions
- BambooHR positions granular custom access levels and advanced approvals as a way to provide the right permissions while maintaining compliance. This plan includes audit logs, permission simulation, and scoped read/write checks. Source: https://www.bamboohr.com/resources/guides/customize-bamboohr-nonprofit

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/access_control/__init__.py` | Create | New app package |
| `backend/apps/access_control/apps.py` | Create | App config |
| `backend/apps/access_control/catalog.py` | Create | Canonical permission and seed-role catalog |
| `backend/apps/access_control/models.py` | Create | Permission, role, role assignment, data scope, field permission, audit decision models |
| `backend/apps/access_control/migrations/0001_initial.py` | Create | Initial RBAC schema |
| `backend/apps/access_control/services.py` | Create | Policy resolution, permission checks, queryset scoping, field masking, compatibility helpers |
| `backend/apps/access_control/serializers.py` | Create | API serializers for roles, permissions, scopes, simulator |
| `backend/apps/access_control/views.py` | Create | CT and org role-management endpoints |
| `backend/apps/access_control/urls.py` | Create | Route RBAC endpoints |
| `backend/apps/access_control/tests/test_policy.py` | Create | Permission and scope unit tests |
| `backend/apps/access_control/tests/test_views.py` | Create | CT/org API tests |
| `backend/clarisal/settings/base.py` | Modify | Add `apps.access_control` to `INSTALLED_APPS` |
| `backend/clarisal/urls.py` | Modify | Include access-control URLs |
| `backend/apps/accounts/permissions.py` | Modify | Add opt-in `HasPermission`, `ScopedOrgAccess`, `ScopedControlTowerAccess` permission classes |
| `backend/apps/accounts/serializers.py` | Modify | Return effective permission summary to the frontend |
| `backend/apps/accounts/workspaces.py` | Modify | Include scoped role assignments in workspace state |
| `backend/apps/organisations/models.py` | Modify | Keep `is_org_admin`; add migration/backfill links only if needed |
| `backend/apps/employees/views.py` | Modify | First scoped queryset integration target |
| `backend/apps/payroll/views.py` | Modify | Payroll scoped queryset and permission-code integration |
| `backend/apps/reports/views.py` | Modify | Report module permission gate for P39 |
| `backend/apps/approvals/views.py` | Modify | Workflow-admin and approval-action permission gates |
| `frontend/src/types/auth.ts` | Modify | Add effective permissions and scope types |
| `frontend/src/types/access-control.ts` | Create | Access role, permission, scope, simulator types |
| `frontend/src/lib/api/access-control.ts` | Create | RBAC API client |
| `frontend/src/lib/rbac.ts` | Modify | Add `hasPermission`, `canAccessScope`, and field visibility helpers |
| `frontend/src/pages/ct/CtAccessControlPage.tsx` | Create | Control Tower role and user assignment management |
| `frontend/src/pages/org/OrgAccessControlPage.tsx` | Create | Org admin role and user assignment management |
| `frontend/src/pages/org/AccessSimulatorPage.tsx` | Create | "View effective permissions" and "view as user" simulator |
| `frontend/src/routes.tsx` | Modify | Register CT/org access-control pages |
| `frontend/src/pages/org/__tests__/OrgAccessControlPage.test.tsx` | Create | UI permission matrix tests |
| `frontend/src/lib/__tests__/rbac.test.ts` | Modify | Frontend helper tests |

---

## Permission Model

Permission codes use this exact format:

```text
<domain>.<resource>.<action>
```

Examples:

- `ct.organisations.read`
- `ct.organisations.write`
- `ct.billing.write`
- `org.employees.read`
- `org.employees.write`
- `org.payroll.read`
- `org.payroll.process`
- `org.approvals.workflow.manage`
- `org.approvals.action.approve`
- `org.reports.read`
- `org.reports.builder.manage`
- `org.reports.export`

Scope kinds:

```text
ALL_ORGANISATIONS
SELECTED_ORGANISATIONS
CURRENT_ORGANISATION
ALL_EMPLOYEES
OWN_RECORD
REPORTING_TREE
SELECTED_DEPARTMENTS
SELECTED_OFFICE_LOCATIONS
SELECTED_LEGAL_ENTITIES
SELECTED_COST_CENTRES
SELECTED_EMPLOYMENT_TYPES
SELECTED_GRADES
SELECTED_BANDS
SELECTED_DESIGNATIONS
SELECTED_EMPLOYEES
```

Default seed roles:

- Control Tower: `CT_SUPER_ADMIN`, `CT_SUPPORT`, `CT_IMPLEMENTATION`, `CT_BILLING`, `CT_COMPLIANCE_AUDITOR`, `CT_READ_ONLY`
- Organisation: `ORG_OWNER`, `ORG_HR_ADMIN`, `ORG_PAYROLL_ADMIN`, `ORG_FINANCE_APPROVER`, `ORG_MANAGER`, `ORG_RECRUITER`, `ORG_ASSET_ADMIN`, `ORG_REPORTS_ANALYST`, `ORG_AUDITOR_READ_ONLY`

## Task 1: Create the Access Control App and Catalog

- [ ] Create `backend/apps/access_control/apps.py`:

```python
from django.apps import AppConfig


class AccessControlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.access_control"
```

- [ ] Add to `backend/clarisal/settings/base.py` after `apps.accounts`:

```python
    "apps.access_control",
```

- [ ] Create `backend/apps/access_control/catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    label: str
    domain: str
    resource: str
    action: str
    description: str


PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec("ct.organisations.read", "Read organisations", "ct", "organisations", "read", "View tenant records in Control Tower."),
    PermissionSpec("ct.organisations.write", "Manage organisations", "ct", "organisations", "write", "Create and update tenant records."),
    PermissionSpec("ct.billing.read", "Read billing", "ct", "billing", "read", "View licences, ledger, invoices, and payments."),
    PermissionSpec("ct.billing.write", "Manage billing", "ct", "billing", "write", "Modify licences, payment status, and billing settings."),
    PermissionSpec("ct.impersonation.start", "Start impersonation", "ct", "impersonation", "start", "Start a scoped Control Tower act-as session."),
    PermissionSpec("ct.audit.read", "Read CT audit", "ct", "audit", "read", "View Control Tower audit logs."),
    PermissionSpec("org.employees.read", "Read employees", "org", "employees", "read", "View employee profiles within assigned scope."),
    PermissionSpec("org.employees.write", "Manage employees", "org", "employees", "write", "Create and edit employee records within assigned scope."),
    PermissionSpec("org.employee_sensitive.read", "Read sensitive employee fields", "org", "employees", "read_sensitive", "View compensation, identifiers, bank, and personal fields."),
    PermissionSpec("org.payroll.read", "Read payroll", "org", "payroll", "read", "View payroll data within assigned scope."),
    PermissionSpec("org.payroll.process", "Process payroll", "org", "payroll", "process", "Calculate, finalize, and publish payroll."),
    PermissionSpec("org.expenses.read", "Read expenses", "org", "expenses", "read", "View expense claims within assigned scope."),
    PermissionSpec("org.expenses.approve", "Approve expenses", "org", "expenses", "approve", "Approve assigned expense claims."),
    PermissionSpec("org.approvals.workflow.manage", "Manage approval workflows", "org", "approvals", "workflow_manage", "Create and edit workflow definitions."),
    PermissionSpec("org.approvals.action.approve", "Act on approvals", "org", "approvals", "approve", "Approve or reject assigned approval actions."),
    PermissionSpec("org.reports.read", "Read reports", "org", "reports", "read", "View reports allowed by role and data scope."),
    PermissionSpec("org.reports.builder.manage", "Manage report templates", "org", "reports", "builder_manage", "Create, edit, and share report templates."),
    PermissionSpec("org.reports.export", "Export reports", "org", "reports", "export", "Export report data."),
    PermissionSpec("org.access_control.manage", "Manage org access", "org", "access_control", "manage", "Assign org roles and data scopes."),
    PermissionSpec("org.audit.read", "Read org audit", "org", "audit", "read", "View organisation audit logs within assigned scope."),
)


SEED_ROLES: dict[str, dict[str, object]] = {
    "CT_SUPER_ADMIN": {
        "scope": "CONTROL_TOWER",
        "name": "Control Tower Super Admin",
        "permissions": [permission.code for permission in PERMISSIONS if permission.domain == "ct"],
    },
    "CT_READ_ONLY": {
        "scope": "CONTROL_TOWER",
        "name": "Control Tower Read Only",
        "permissions": ["ct.organisations.read", "ct.billing.read", "ct.audit.read"],
    },
    "CT_SUPPORT": {
        "scope": "CONTROL_TOWER",
        "name": "Control Tower Support",
        "permissions": ["ct.organisations.read", "ct.impersonation.start", "ct.audit.read"],
    },
    "CT_IMPLEMENTATION": {
        "scope": "CONTROL_TOWER",
        "name": "Implementation Admin",
        "permissions": ["ct.organisations.read", "ct.organisations.write", "ct.impersonation.start"],
    },
    "CT_BILLING": {
        "scope": "CONTROL_TOWER",
        "name": "Billing Admin",
        "permissions": ["ct.organisations.read", "ct.billing.read", "ct.billing.write"],
    },
    "CT_COMPLIANCE_AUDITOR": {
        "scope": "CONTROL_TOWER",
        "name": "Compliance Auditor",
        "permissions": ["ct.organisations.read", "ct.billing.read", "ct.audit.read"],
    },
    "ORG_OWNER": {
        "scope": "ORGANISATION",
        "name": "Organisation Owner",
        "permissions": [permission.code for permission in PERMISSIONS if permission.domain == "org"],
    },
    "ORG_HR_ADMIN": {
        "scope": "ORGANISATION",
        "name": "HR Admin",
        "permissions": ["org.employees.read", "org.employees.write", "org.employee_sensitive.read", "org.approvals.workflow.manage", "org.reports.read"],
    },
    "ORG_PAYROLL_ADMIN": {
        "scope": "ORGANISATION",
        "name": "Payroll Admin",
        "permissions": ["org.employees.read", "org.employee_sensitive.read", "org.payroll.read", "org.payroll.process", "org.reports.read", "org.reports.export"],
    },
    "ORG_FINANCE_APPROVER": {
        "scope": "ORGANISATION",
        "name": "Finance Approver",
        "permissions": ["org.expenses.read", "org.expenses.approve", "org.approvals.action.approve", "org.reports.read"],
    },
    "ORG_REPORTS_ANALYST": {
        "scope": "ORGANISATION",
        "name": "Reports Analyst",
        "permissions": ["org.reports.read", "org.reports.builder.manage", "org.reports.export"],
    },
    "ORG_MANAGER": {
        "scope": "ORGANISATION",
        "name": "Manager",
        "permissions": ["org.employees.read", "org.approvals.action.approve", "org.expenses.approve", "org.reports.read"],
    },
    "ORG_RECRUITER": {
        "scope": "ORGANISATION",
        "name": "Recruiter",
        "permissions": ["org.employees.read", "org.reports.read"],
    },
    "ORG_ASSET_ADMIN": {
        "scope": "ORGANISATION",
        "name": "Asset Admin",
        "permissions": ["org.employees.read", "org.reports.read"],
    },
    "ORG_AUDITOR_READ_ONLY": {
        "scope": "ORGANISATION",
        "name": "Read Only Auditor",
        "permissions": ["org.employees.read", "org.payroll.read", "org.expenses.read", "org.reports.read", "org.audit.read"],
    },
}
```

- [ ] Add `apps.access_control` to local import lint allow-list if the repository has one.
- [ ] Run `docker compose run --rm backend python manage.py check`.
- [ ] Expected: Django app imports successfully.

## Task 2: Add RBAC Models

- [ ] Create `backend/apps/access_control/models.py`:

```python
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import AuditedBaseModel


class AccessScope(models.TextChoices):
    CONTROL_TOWER = "CONTROL_TOWER", "Control Tower"
    ORGANISATION = "ORGANISATION", "Organisation"


class DataScopeKind(models.TextChoices):
    ALL_ORGANISATIONS = "ALL_ORGANISATIONS", "All Organisations"
    SELECTED_ORGANISATIONS = "SELECTED_ORGANISATIONS", "Selected Organisations"
    CURRENT_ORGANISATION = "CURRENT_ORGANISATION", "Current Organisation"
    ALL_EMPLOYEES = "ALL_EMPLOYEES", "All Employees"
    OWN_RECORD = "OWN_RECORD", "Own Record"
    REPORTING_TREE = "REPORTING_TREE", "Reporting Tree"
    SELECTED_DEPARTMENTS = "SELECTED_DEPARTMENTS", "Selected Departments"
    SELECTED_OFFICE_LOCATIONS = "SELECTED_OFFICE_LOCATIONS", "Selected Office Locations"
    SELECTED_LEGAL_ENTITIES = "SELECTED_LEGAL_ENTITIES", "Selected Legal Entities"
    SELECTED_COST_CENTRES = "SELECTED_COST_CENTRES", "Selected Cost Centres"
    SELECTED_EMPLOYMENT_TYPES = "SELECTED_EMPLOYMENT_TYPES", "Selected Employment Types"
    SELECTED_GRADES = "SELECTED_GRADES", "Selected Grades"
    SELECTED_BANDS = "SELECTED_BANDS", "Selected Bands"
    SELECTED_DESIGNATIONS = "SELECTED_DESIGNATIONS", "Selected Designations"
    SELECTED_EMPLOYEES = "SELECTED_EMPLOYEES", "Selected Employees"


class AccessPermission(AuditedBaseModel):
    code = models.CharField(max_length=160, unique=True)
    label = models.CharField(max_length=255)
    domain = models.CharField(max_length=40)
    resource = models.CharField(max_length=80)
    action = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "access_permissions"
        ordering = ["domain", "resource", "action"]

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
    scope = models.CharField(max_length=32, choices=AccessScope.choices)
    code = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "access_roles"
        ordering = ["scope", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "code"],
                name="unique_org_access_role_code",
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=Q(organisation__isnull=True),
                name="unique_global_access_role_code",
            ),
        ]


class AccessRolePermission(AuditedBaseModel):
    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(AccessPermission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        db_table = "access_role_permissions"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="unique_access_role_permission"),
        ]


class AccessRoleAssignment(AuditedBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_role_assignments")
    organisation = models.ForeignKey(
        "organisations.Organisation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_role_assignments",
    )
    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="assignments")
    is_active = models.BooleanField(default=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "access_role_assignments"
        ordering = ["user__email", "role__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organisation", "role"],
                condition=Q(is_active=True),
                name="unique_active_user_org_role_assignment",
            ),
        ]


class DataScope(AuditedBaseModel):
    assignment = models.ForeignKey(AccessRoleAssignment, on_delete=models.CASCADE, related_name="data_scopes")
    kind = models.CharField(max_length=40, choices=DataScopeKind.choices)
    organisation = models.ForeignKey(
        "organisations.Organisation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_data_scopes",
    )
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_data_scopes",
    )
    office_location = models.ForeignKey(
        "locations.OfficeLocation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_data_scopes",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_data_scopes",
    )
    legal_entity = models.CharField(max_length=120, blank=True)
    cost_centre = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(max_length=40, blank=True)
    grade = models.CharField(max_length=120, blank=True)
    band = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "access_data_scopes"
        ordering = ["kind", "created_at"]


class FieldPermission(AuditedBaseModel):
    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="field_permissions")
    field_code = models.CharField(max_length=160)
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = "access_field_permissions"
        constraints = [
            models.UniqueConstraint(fields=["role", "field_code"], name="unique_role_field_permission"),
        ]


class AccessDecisionLog(AuditedBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_decision_logs")
    organisation = models.ForeignKey(
        "organisations.Organisation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_decision_logs",
    )
    permission_code = models.CharField(max_length=160)
    allowed = models.BooleanField()
    reason = models.TextField(blank=True)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "access_decision_logs"
        ordering = ["-created_at"]
```

- [ ] Create migration `backend/apps/access_control/migrations/0001_initial.py`.
- [ ] Run `docker compose run --rm backend python manage.py makemigrations access_control --check --dry-run`.
- [ ] Expected: no pending access-control model changes after migration is present.

## Task 3: Seed Permissions and Preserve Existing Behavior

**Why:** Deploying RBAC must not lock out existing Control Tower users or org admins.

- [ ] In `backend/apps/access_control/services.py`, add seeding:

```python
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .catalog import PERMISSIONS, SEED_ROLES
from .models import AccessPermission, AccessRole, AccessRoleAssignment, AccessRolePermission, AccessScope, DataScope, DataScopeKind


@transaction.atomic
def sync_permission_catalog():
    permissions_by_code = {}
    for spec in PERMISSIONS:
        permission, _ = AccessPermission.objects.update_or_create(
            code=spec.code,
            defaults={
                "label": spec.label,
                "domain": spec.domain,
                "resource": spec.resource,
                "action": spec.action,
                "description": spec.description,
                "is_active": True,
            },
        )
        permissions_by_code[spec.code] = permission

    for role_code, role_spec in SEED_ROLES.items():
        role, _ = AccessRole.objects.update_or_create(
            organisation=None,
            code=role_code,
            defaults={
                "scope": role_spec["scope"],
                "name": role_spec["name"],
                "is_system": True,
                "is_active": True,
            },
        )
        for permission_code in role_spec["permissions"]:
            AccessRolePermission.objects.get_or_create(role=role, permission=permissions_by_code[permission_code])


@transaction.atomic
def backfill_existing_admin_roles():
    from django.contrib.auth import get_user_model

    from apps.accounts.models import AccountType
    from apps.organisations.models import OrganisationMembership, OrganisationMembershipStatus

    ct_role = AccessRole.objects.get(code="CT_SUPER_ADMIN", organisation__isnull=True)
    org_owner_role = AccessRole.objects.get(code="ORG_OWNER", organisation__isnull=True)

    User = get_user_model()
    for user in User.objects.filter(account_type=AccountType.CONTROL_TOWER):
        assignment, _ = AccessRoleAssignment.objects.get_or_create(user=user, organisation=None, role=ct_role, defaults={"is_active": True})
        DataScope.objects.get_or_create(assignment=assignment, kind=DataScopeKind.ALL_ORGANISATIONS)

    memberships = OrganisationMembership.objects.filter(
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).select_related("user", "organisation")
    for membership in memberships:
        assignment, _ = AccessRoleAssignment.objects.get_or_create(
            user=membership.user,
            organisation=membership.organisation,
            role=org_owner_role,
            defaults={"is_active": True},
        )
        DataScope.objects.get_or_create(
            assignment=assignment,
            kind=DataScopeKind.ALL_EMPLOYEES,
            organisation=membership.organisation,
        )
```

- [ ] Add management command `backend/apps/access_control/management/commands/sync_access_control.py`:

```python
from django.core.management.base import BaseCommand

from apps.access_control.services import backfill_existing_admin_roles, sync_permission_catalog


class Command(BaseCommand):
    help = "Synchronize access-control permissions, seed roles, and compatibility assignments."

    def handle(self, *args, **options):
        sync_permission_catalog()
        backfill_existing_admin_roles()
        self.stdout.write(self.style.SUCCESS("Access-control catalog synchronized."))
```

- [ ] Run `docker compose run --rm backend python manage.py sync_access_control`.
- [ ] Expected: command prints `Access-control catalog synchronized.`

## Task 4: Implement Policy Resolution Service

- [ ] In `backend/apps/access_control/services.py`, add:

```python
def get_active_role_assignments(user, organisation=None):
    today = timezone.localdate()
    queryset = (
        AccessRoleAssignment.objects.select_related("role", "organisation")
        .prefetch_related("role__role_permissions__permission", "data_scopes")
        .filter(user=user, is_active=True, role__is_active=True)
        .filter(Q(starts_on__isnull=True) | Q(starts_on__lte=today))
        .filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
    )
    if organisation is None:
        return queryset.filter(organisation__isnull=True)
    return queryset.filter(Q(organisation=organisation) | Q(organisation__isnull=True))


def get_effective_permission_codes(user, organisation=None) -> set[str]:
    codes: set[str] = set()
    for assignment in get_active_role_assignments(user, organisation):
        for role_permission in assignment.role.role_permissions.all():
            if role_permission.permission.is_active:
                codes.add(role_permission.permission.code)
    return codes


def has_permission(user, permission_code, organisation=None) -> bool:
    return permission_code in get_effective_permission_codes(user, organisation)


def require_permission(user, permission_code, organisation=None):
    if not has_permission(user, permission_code, organisation):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied(f"Missing permission: {permission_code}")
```

- [ ] Add tests:

```python
def test_has_permission_reads_seeded_org_owner(org_admin_user, organisation):
    sync_permission_catalog()
    backfill_existing_admin_roles()

    assert has_permission(org_admin_user, "org.employees.read", organisation)
    assert has_permission(org_admin_user, "org.access_control.manage", organisation)
```

- [ ] Run `docker compose run --rm backend pytest apps/access_control/tests/test_policy.py::test_has_permission_reads_seeded_org_owner -q`.
- [ ] Expected: test passes.

## Task 5: Implement Employee Queryset Scoping

- [ ] In `backend/apps/access_control/services.py`, add:

```python
def _reporting_tree_employee_ids(employee):
    from apps.employees.models import Employee

    collected: set[str] = set()
    frontier = [employee.id]
    while frontier:
        manager_id = frontier.pop()
        direct_ids = list(
            Employee.objects.filter(reporting_to_id=manager_id).values_list("id", flat=True)
        )
        for direct_id in direct_ids:
            if direct_id not in collected:
                collected.add(direct_id)
                frontier.append(direct_id)
    return collected


def scope_employee_queryset(queryset, user, organisation, permission_code="org.employees.read"):
    if not has_permission(user, permission_code, organisation):
        return queryset.none()

    assignments = get_active_role_assignments(user, organisation).prefetch_related("data_scopes")
    scoped_query = Q()
    matched_scope = False

    for assignment in assignments:
        for scope in assignment.data_scopes.all():
            if scope.kind == DataScopeKind.ALL_EMPLOYEES:
                return queryset.filter(organisation=organisation)
            if scope.kind == DataScopeKind.OWN_RECORD:
                matched_scope = True
                scoped_query |= Q(user=user, organisation=organisation)
            elif scope.kind == DataScopeKind.REPORTING_TREE:
                from apps.employees.models import Employee

                manager = Employee.objects.filter(user=user, organisation=organisation).first()
                if manager:
                    matched_scope = True
                    scoped_query |= Q(id__in=_reporting_tree_employee_ids(manager), organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_DEPARTMENTS and scope.department_id:
                matched_scope = True
                scoped_query |= Q(department_id=scope.department_id, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_OFFICE_LOCATIONS and scope.office_location_id:
                matched_scope = True
                scoped_query |= Q(office_location_id=scope.office_location_id, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_EMPLOYEES and scope.employee_id:
                matched_scope = True
                scoped_query |= Q(id=scope.employee_id, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_LEGAL_ENTITIES and scope.legal_entity:
                matched_scope = True
                scoped_query |= Q(legal_entity=scope.legal_entity, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_COST_CENTRES and scope.cost_centre:
                matched_scope = True
                scoped_query |= Q(cost_centre=scope.cost_centre, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_EMPLOYMENT_TYPES and scope.employment_type:
                matched_scope = True
                scoped_query |= Q(employment_type=scope.employment_type, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_GRADES and scope.grade:
                matched_scope = True
                scoped_query |= Q(grade=scope.grade, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_BANDS and scope.band:
                matched_scope = True
                scoped_query |= Q(band=scope.band, organisation=organisation)
            elif scope.kind == DataScopeKind.SELECTED_DESIGNATIONS and scope.designation:
                matched_scope = True
                scoped_query |= Q(designation=scope.designation, organisation=organisation)

    if not matched_scope:
        return queryset.none()
    return queryset.filter(scoped_query).distinct()
```

- [ ] Add tests:

```python
def test_department_scope_only_returns_department_employees(hr_admin_user, organisation, sales_department, engineering_department):
    sync_permission_catalog()
    role = AccessRole.objects.get(code="ORG_HR_ADMIN", organisation__isnull=True)
    assignment = AccessRoleAssignment.objects.create(
        user=hr_admin_user,
        organisation=organisation,
        role=role,
        is_active=True,
    )
    DataScope.objects.create(
        assignment=assignment,
        kind=DataScopeKind.SELECTED_DEPARTMENTS,
        organisation=organisation,
        department=sales_department,
    )
    sales_employee = employee_factory(organisation=organisation, department=sales_department)
    engineering_employee = employee_factory(organisation=organisation, department=engineering_department)

    scoped = scope_employee_queryset(Employee.objects.all(), hr_admin_user, organisation)

    assert sales_employee in scoped
    assert engineering_employee not in scoped
```

- [ ] Run `docker compose run --rm backend pytest apps/access_control/tests/test_policy.py -q`.
- [ ] Expected: tests pass.

## Task 6: Add Field-Level Visibility and Serializer Masking

**Why:** Payroll, bank, government ID, compensation, and personal fields require stronger protection than ordinary profile fields.

- [ ] In `backend/apps/access_control/services.py`, add:

```python
SENSITIVE_FIELD_GROUPS = {
    "employee.compensation": {"current_ctc", "salary", "payroll_component", "compensation_template"},
    "employee.bank": {"bank_name", "account_number", "ifsc_code"},
    "employee.government_id": {"pan", "aadhaar", "government_id_number"},
    "employee.personal": {"date_of_birth", "blood_group", "personal_email", "phone_number"},
}


def can_view_field(user, field_code, organisation=None) -> bool:
    if has_permission(user, "org.employee_sensitive.read", organisation):
        return True
    for fields in SENSITIVE_FIELD_GROUPS.values():
        if field_code in fields:
            return False
    return True


def mask_value(value):
    if value in (None, ""):
        return value
    text = str(value)
    if len(text) <= 4:
        return "****"
    return f"****{text[-4:]}"


def mask_serializer_data(data, user, organisation, field_map):
    masked = dict(data)
    for response_field, field_code in field_map.items():
        if response_field in masked and not can_view_field(user, field_code, organisation):
            masked[response_field] = mask_value(masked[response_field])
    return masked
```

- [ ] In employee serializers that expose sensitive fields, call `mask_serializer_data` using a map like:

```python
EMPLOYEE_SENSITIVE_FIELD_MAP = {
    "pan_number": "pan",
    "aadhaar_number": "aadhaar",
    "bank_account_number": "account_number",
    "current_ctc": "current_ctc",
}
```

- [ ] Add tests that users without `org.employee_sensitive.read` see masked values and users with it see full values.

## Task 7: Add DRF Permission Classes

- [ ] In `backend/apps/accounts/permissions.py`, add:

```python
class HasPermission(BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        from apps.access_control.services import has_permission
        from .workspaces import get_active_admin_organisation

        permission_code = getattr(view, "permission_code", None)
        if permission_code is None:
            resolver = getattr(view, "get_permission_code", None)
            permission_code = resolver() if callable(resolver) else None
        if permission_code is None:
            return True
        organisation = get_active_admin_organisation(request, request.user)
        return has_permission(request.user, permission_code, organisation)


class ScopedOrgAccess(BasePermission):
    message = "Your role does not include this organisation scope."

    def has_permission(self, request, view):
        from apps.access_control.services import has_permission
        from .workspaces import get_active_admin_organisation

        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return False
        return has_permission(request.user, getattr(view, "permission_code", "org.employees.read"), organisation)
```

- [ ] Do not remove existing `IsOrgAdmin`, `BelongsToActiveOrg`, or `OrgAdminMutationAllowed`; add new classes alongside them so endpoints can opt in safely.
- [ ] Add test that a user with active org membership but no `org.payroll.read` receives 403 from a payroll endpoint once that endpoint opts in.

## Task 8: Scope High-Risk Endpoints First

**Why:** Payroll, reports, employee profile access, approval workflow management, and Control Tower are the highest-risk surfaces.

- [ ] In `backend/apps/payroll/views.py`, set permission code by action:

```python
def get_permission_code(self):
    if self.request.method in ("GET", "HEAD", "OPTIONS"):
        return "org.payroll.read"
    return "org.payroll.process"
```

- [ ] Scope employee/payroll querysets with `scope_employee_queryset`.
- [ ] In `backend/apps/reports/views.py`, require `org.reports.read` for JSON preview and `org.reports.export` for CSV/XLSX.
- [ ] In `backend/apps/approvals/views.py`, require:
  - `org.approvals.workflow.manage` for workflow create/update/simulation/readiness
  - `org.approvals.action.approve` for approval actions
- [ ] In Control Tower views, require:
  - `ct.organisations.read` for org lists/details
  - `ct.organisations.write` for state transitions and org mutation
  - `ct.billing.read` or `ct.billing.write` for billing endpoints
  - `ct.impersonation.start` for act-as session creation
- [ ] Add endpoint tests for denied access and allowed scoped access.

## Task 9: Add Role Management APIs

- [ ] Create serializers in `backend/apps/access_control/serializers.py`:

```python
class AccessPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPermission
        fields = ["id", "code", "label", "domain", "resource", "action", "description"]


class DataScopeWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=DataScopeKind.choices)
    organisation_id = serializers.UUIDField(required=False)
    department_id = serializers.UUIDField(required=False)
    office_location_id = serializers.UUIDField(required=False)
    employee_id = serializers.UUIDField(required=False)
    legal_entity = serializers.CharField(required=False, allow_blank=True)
    cost_centre = serializers.CharField(required=False, allow_blank=True)
    employment_type = serializers.CharField(required=False, allow_blank=True)
    grade = serializers.CharField(required=False, allow_blank=True)
    band = serializers.CharField(required=False, allow_blank=True)
    designation = serializers.CharField(required=False, allow_blank=True)


class AccessRoleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    permission_codes = serializers.ListField(child=serializers.CharField(max_length=160))


class AccessRoleAssignmentWriteSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role_id = serializers.UUIDField()
    organisation_id = serializers.UUIDField(required=False)
    starts_on = serializers.DateField(required=False)
    ends_on = serializers.DateField(required=False)
    scopes = DataScopeWriteSerializer(many=True)
```

- [ ] Add views:
  - `AccessPermissionCatalogView`
  - `OrgAccessRoleListCreateView`
  - `OrgAccessRoleDetailView`
  - `OrgAccessRoleAssignmentListCreateView`
  - `OrgAccessRoleAssignmentDetailView`
  - `CtAccessRoleListCreateView`
  - `CtAccessRoleAssignmentListCreateView`
  - `EffectiveAccessSimulationView`
- [ ] Register:

```python
urlpatterns = [
    path("access-control/permissions/", AccessPermissionCatalogView.as_view()),
    path("org/access-control/roles/", OrgAccessRoleListCreateView.as_view()),
    path("org/access-control/roles/<uuid:pk>/", OrgAccessRoleDetailView.as_view()),
    path("org/access-control/assignments/", OrgAccessRoleAssignmentListCreateView.as_view()),
    path("org/access-control/assignments/<uuid:pk>/", OrgAccessRoleAssignmentDetailView.as_view()),
    path("ct/access-control/roles/", CtAccessRoleListCreateView.as_view()),
    path("ct/access-control/assignments/", CtAccessRoleAssignmentListCreateView.as_view()),
    path("access-control/simulate/", EffectiveAccessSimulationView.as_view()),
]
```

- [ ] Add tests for creating a payroll admin restricted to one office location.

## Task 10: Add Effective Permission Summary to Auth State

- [ ] In `backend/apps/accounts/serializers.py`, add fields to the current-user serializer:

```python
effective_permissions = serializers.SerializerMethodField()
effective_scopes = serializers.SerializerMethodField()

def get_effective_permissions(self, user):
    from apps.access_control.services import get_effective_permission_codes
    from apps.accounts.workspaces import get_active_admin_organisation

    request = self.context.get("request")
    organisation = get_active_admin_organisation(request, user) if request else None
    return sorted(get_effective_permission_codes(user, organisation))

def get_effective_scopes(self, user):
    from apps.access_control.services import summarize_effective_scopes
    from apps.accounts.workspaces import get_active_admin_organisation

    request = self.context.get("request")
    organisation = get_active_admin_organisation(request, user) if request else None
    return summarize_effective_scopes(user, organisation)
```

- [ ] Implement `summarize_effective_scopes` to return scope kinds and display names only, not internal SQL details.
- [ ] Add API test that an org owner receives `org.access_control.manage` and `ALL_EMPLOYEES`.

## Task 11: Build Frontend RBAC Helpers

- [ ] Create `frontend/src/types/access-control.ts`:

```ts
export type PermissionCode = string

export interface EffectiveScope {
  kind: string
  label: string
  values: Array<{ id: string; label: string }>
}

export interface AccessRole {
  id: string
  code: string
  name: string
  description: string
  is_system: boolean
  permission_codes: PermissionCode[]
}

export interface AccessRoleAssignment {
  id: string
  user_id: string
  user_label: string
  role: AccessRole
  scopes: EffectiveScope[]
  is_active: boolean
}
```

- [ ] Modify `frontend/src/types/auth.ts`:

```ts
effective_permissions: string[]
effective_scopes: EffectiveScope[]
```

- [ ] Modify `frontend/src/lib/rbac.ts`:

```ts
export function hasPermission(user: Pick<AuthUser, 'effective_permissions'> | undefined, permission: string): boolean {
  return Boolean(user?.effective_permissions?.includes(permission))
}

export function hasAnyPermission(user: Pick<AuthUser, 'effective_permissions'> | undefined, permissions: string[]): boolean {
  return permissions.some((permission) => hasPermission(user, permission))
}

export function canManageAccessControl(user: Pick<AuthUser, 'effective_permissions'> | undefined): boolean {
  return hasAnyPermission(user, ['org.access_control.manage', 'ct.organisations.write'])
}
```

- [ ] Add Vitest coverage for `hasPermission`, `hasAnyPermission`, and `canManageAccessControl`.

## Task 12: Build Org and CT Access Control Pages

- [ ] Create `frontend/src/lib/api/access-control.ts`:

```ts
export async function fetchOrgAccessRoles(): Promise<AccessRole[]> {
  const { data } = await api.get('/org/access-control/roles/')
  return data
}

export async function createOrgAccessRole(payload: AccessRoleWritePayload): Promise<AccessRole> {
  const { data } = await api.post('/org/access-control/roles/', payload)
  return data
}

export async function assignOrgAccessRole(payload: AccessRoleAssignmentWritePayload): Promise<AccessRoleAssignment> {
  const { data } = await api.post('/org/access-control/assignments/', payload)
  return data
}
```

- [ ] Create `frontend/src/pages/org/OrgAccessControlPage.tsx` with:
  - Permission matrix grouped by domain/resource.
  - Role list with system/custom badge.
  - Assignment drawer with user picker, role picker, scope picker.
  - Scope picker supporting all scope kinds listed in this plan.
  - Warning when granting `org.payroll.process`, `org.employee_sensitive.read`, or `org.access_control.manage`.
- [ ] Create `frontend/src/pages/ct/CtAccessControlPage.tsx` with CT role and assignment management.
- [ ] Create `frontend/src/pages/org/AccessSimulatorPage.tsx` with:
  - User picker.
  - Organisation picker where applicable.
  - Effective permissions table.
  - Effective scopes table.
  - "Can this user access employee?" simulator.
- [ ] Add route guards using `hasPermission`.
- [ ] Add UI tests:

```ts
it('hides access-control page when user lacks manage permission', () => {
  const user = buildAuthUser({ effective_permissions: ['org.employees.read'] })

  expect(canManageAccessControl(user)).toBe(false)
})
```

## Task 13: Replace P37 Compatibility Shims

**Why:** P37 creates temporary role lookup helpers for approval approver resolution. After P38, those helpers must use real assignments and scopes.

- [ ] Replace `employees_with_permission_role` in `backend/apps/approvals/role_resolver.py` so approvals call the P38 access-control service:

```python
def employees_with_permission_role(organisation, role_code):
    from apps.access_control.services import employees_with_permission_role as resolve

    return resolve(organisation, role_code)
```

- [ ] Replace `employees_with_scope` in `backend/apps/approvals/role_resolver.py`:

```python
def employees_with_scope(organisation, role_code, **scope):
    from apps.access_control.services import employees_with_scope as resolve

    return resolve(organisation, role_code, **scope)
```

- [ ] Add the real access-control implementations in `backend/apps/access_control/services.py`:

```python
def employees_with_permission_role(organisation, role_code):
    from apps.employees.models import Employee

    assignments = AccessRoleAssignment.objects.filter(
        organisation=organisation,
        role__code=role_code,
        is_active=True,
        role__is_active=True,
    ).values_list("user_id", flat=True)
    return Employee.objects.filter(
        organisation=organisation,
        user_id__in=assignments,
        status="ACTIVE",
    ).select_related("user")


def employees_with_scope(organisation, role_code, **scope):
    queryset = employees_with_permission_role(organisation, role_code)
    if scope.get("office_location_id"):
        queryset = queryset.filter(office_location_id=scope["office_location_id"])
    if scope.get("department_id"):
        queryset = queryset.filter(department_id=scope["department_id"])
    return queryset
```

- [ ] Add approval resolver test proving a `FINANCE_APPROVER` role assignment resolves to that employee and not every org admin.

## Task 14: Docker Verification

- [ ] Rebuild backend and frontend images:

```bash
docker compose build backend frontend
```

- [ ] Recreate services:

```bash
docker compose up -d --force-recreate backend frontend
```

- [ ] Run migrations:

```bash
docker compose run --rm backend python manage.py migrate
```

- [ ] Seed access control:

```bash
docker compose run --rm backend python manage.py sync_access_control
```

- [ ] Run backend tests:

```bash
docker compose run --rm backend pytest apps/access_control/tests apps/accounts/tests apps/employees/tests apps/payroll/tests apps/reports/tests apps/approvals/tests -q
```

- [ ] Run frontend tests:

```bash
docker compose run --rm frontend npm run test -- rbac OrgAccessControlPage CtAccessControlPage AccessSimulatorPage
```

- [ ] Run full frontend check:

```bash
docker compose run --rm frontend npm run check
```

- [ ] Expected: all commands exit 0.

## Rollout Rules

- [ ] Phase 1 deploy must backfill `CT_SUPER_ADMIN` for current Control Tower users and `ORG_OWNER` for current active org admins.
- [ ] Phase 1 must not remove `is_org_admin`; it remains a compatibility flag until all org-admin screens use permission codes.
- [ ] Phase 2 opts in high-risk endpoints: payroll, reports, approvals, employees, Control Tower billing.
- [ ] Phase 3 opts in lower-risk modules after endpoint-specific tests exist.
- [ ] Any endpoint that exposes employee data must either call `scope_employee_queryset` or prove it only returns the active user's own record.

## Self-Review Checklist for Workers

- [ ] Existing admins are not locked out after migration and seed.
- [ ] Department, office location, selected employee, and reporting-tree scopes have positive and negative tests.
- [ ] Payroll endpoints deny users who have HR read access but no payroll permission.
- [ ] Report endpoints deny export unless `org.reports.export` is present.
- [ ] Approval workflow management denies users who can approve actions but cannot manage workflow definitions.
- [ ] Sensitive employee fields are masked without `org.employee_sensitive.read`.
- [ ] Frontend navigation uses permissions, not only account type.
