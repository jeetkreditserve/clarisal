from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast

from django.db.models import Q, QuerySet

from apps.accounts.models import AccountType, User
from apps.accounts.workspaces import get_active_employee
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import Organisation, OrganisationMembership, OrganisationMembershipStatus

from .catalog import PERMISSIONS, SEED_ROLES
from .models import (
    AccessPermission,
    AccessRole,
    AccessRoleAssignment,
    AccessRolePermission,
    AccessRoleScope,
    AccessScope,
    DataScopeKind,
)


@dataclass(frozen=True)
class EffectiveRoleBundle:
    code: str
    scope: str
    permission_codes: frozenset[str]
    scope_summary: tuple[dict[str, str], ...]
    assignment_id: str | None = None
    source: str = "EXPLICIT"


def sync_access_control() -> dict[str, int]:
    permission_map: dict[str, AccessPermission] = {}
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
        permission_map[spec.code] = permission

    role_map: dict[str, AccessRole] = {}
    for role_spec in SEED_ROLES.values():
        role, _ = AccessRole.objects.update_or_create(
            code=role_spec.code,
            defaults={
                "scope": role_spec.scope,
                "name": role_spec.name,
                "description": role_spec.description,
                "is_system": True,
                "is_active": True,
            },
        )
        role_map[role_spec.code] = role
        AccessRolePermission.objects.filter(role=role).exclude(permission__code__in=role_spec.permissions).delete()
        existing_codes = set(role.role_permissions.values_list("permission__code", flat=True))
        for permission_code in role_spec.permissions:
            if permission_code in existing_codes:
                continue
            AccessRolePermission.objects.create(role=role, permission=permission_map[permission_code])

    ct_assignments = 0
    for user in User.objects.filter(account_type=AccountType.CONTROL_TOWER, is_active=True):
        _, created = AccessRoleAssignment.objects.get_or_create(
            user=user,
            role=role_map["CT_SUPER_ADMIN"],
            organisation=None,
            defaults={"is_active": True},
        )
        ct_assignments += int(created)

    org_assignments = 0
    active_memberships = OrganisationMembership.objects.filter(
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).select_related("organisation", "user")
    for membership in active_memberships:
        existing = AccessRoleAssignment.objects.filter(
            user=membership.user,
            organisation=membership.organisation,
            role__scope=AccessRoleScope.ORGANISATION,
        ).exists()
        if existing:
            continue
        AccessRoleAssignment.objects.create(
            user=membership.user,
            organisation=membership.organisation,
            role=role_map["ORG_OWNER"],
            is_active=True,
        )
        org_assignments += 1

    return {
        "permissions": len(permission_map),
        "roles": len(role_map),
        "ct_assignments": ct_assignments,
        "org_assignments": org_assignments,
    }


def get_effective_permission_codes(
    user: User,
    *,
    organisation: Organisation | None = None,
    request=None,
) -> list[str]:
    permissions: set[str] = set()
    for bundle in get_effective_role_bundles(user, organisation=organisation, request=request):
        permissions.update(bundle.permission_codes)
    return sorted(permissions)


def has_permission(
    user: User,
    permission_code: str,
    *,
    organisation: Organisation | None = None,
    request=None,
) -> bool:
    if user.account_type == AccountType.CONTROL_TOWER and organisation is not None:
        return True
    return permission_code in get_effective_permission_codes(user, organisation=organisation, request=request)


def summarize_effective_scopes(
    user: User,
    *,
    organisation: Organisation | None = None,
    request=None,
) -> list[dict[str, str]]:
    scopes: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for bundle in get_effective_role_bundles(user, organisation=organisation, request=request):
        for scope in bundle.scope_summary:
            key = (scope["kind"], scope["label"])
            if key in seen:
                continue
            seen.add(key)
            scopes.append(scope)
    return scopes


def scope_employee_queryset(
    queryset: QuerySet[Employee],
    user: User,
    *,
    organisation: Organisation,
    request=None,
) -> QuerySet[Employee]:
    if user.account_type == AccountType.CONTROL_TOWER:
        return queryset.filter(organisation=organisation)

    bundles = get_effective_role_bundles(user, organisation=organisation, request=request)
    if any(scope["kind"] == DataScopeKind.ALL_EMPLOYEES for bundle in bundles for scope in bundle.scope_summary):
        return queryset.filter(organisation=organisation)

    active_employee = _get_employee_record_for_org(user, organisation, request=request)
    filters = Q()
    for bundle in bundles:
        if not bundle.scope_summary:
            return queryset.filter(organisation=organisation)
        for scope in bundle.scope_summary:
            if scope["kind"] == DataScopeKind.OWN_RECORD and active_employee is not None:
                filters |= Q(id=active_employee.id)
            elif scope["kind"] == DataScopeKind.REPORTING_TREE and active_employee is not None:
                from apps.employees.services import get_reporting_team

                team_ids = [member.id for member in get_reporting_team(active_employee, include_indirect=True)]
                filters |= Q(id__in=team_ids)
            elif scope["kind"] == DataScopeKind.SELECTED_DEPARTMENTS:
                filters |= Q(department__name=scope["label"])
            elif scope["kind"] == DataScopeKind.SELECTED_OFFICE_LOCATIONS:
                filters |= Q(office_location__name=scope["label"])

    if not filters:
        return queryset.none()
    return queryset.filter(organisation=organisation).filter(filters).distinct()


def mask_serializer_data(
    data: dict[str, Any],
    field_permissions: dict[str, str],
    user: User,
    *,
    organisation: Organisation | None = None,
    request=None,
) -> dict[str, Any]:
    masked = deepcopy(data)
    for field_name, permission_code in field_permissions.items():
        if field_name not in masked:
            continue
        if has_permission(user, permission_code, organisation=organisation, request=request):
            continue
        masked[field_name] = _mask_value(masked[field_name])
    return masked


def get_effective_role_bundles(
    user: User,
    *,
    organisation: Organisation | None = None,
    request=None,
) -> list[EffectiveRoleBundle]:
    explicit_assignments = list(_get_explicit_assignments(user, organisation=organisation))
    if explicit_assignments:
        return [_bundle_from_assignment(assignment) for assignment in explicit_assignments]

    synthetic_bundle = _get_synthetic_bundle(user, organisation=organisation, request=request)
    return [synthetic_bundle] if synthetic_bundle is not None else []


def _get_explicit_assignments(user: User, *, organisation: Organisation | None) -> QuerySet[AccessRoleAssignment]:
    queryset = (
        AccessRoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True,
        )
        .select_related("role", "organisation")
        .prefetch_related("role__role_permissions__permission", "scopes__department", "scopes__office_location", "scopes__employee")
    )
    if organisation is None:
        return queryset.filter(role__scope=AccessRoleScope.CONTROL_TOWER, organisation__isnull=True)
    return queryset.filter(role__scope=AccessRoleScope.ORGANISATION, organisation=organisation)


def _bundle_from_assignment(assignment: AccessRoleAssignment) -> EffectiveRoleBundle:
    permission_codes = frozenset(assignment.role.role_permissions.values_list("permission__code", flat=True))
    scope_summary = _summaries_from_scope_records(list(assignment.scopes.all()), assignment.role.scope)
    return EffectiveRoleBundle(
        code=assignment.role.code,
        scope=assignment.role.scope,
        permission_codes=permission_codes,
        scope_summary=scope_summary,
        assignment_id=str(assignment.id),
        source="EXPLICIT",
    )


def _get_synthetic_bundle(
    user: User,
    *,
    organisation: Organisation | None,
    request=None,
) -> EffectiveRoleBundle | None:
    if user.account_type == AccountType.CONTROL_TOWER and organisation is None:
        return _bundle_from_seed("CT_SUPER_ADMIN", source="SYNTHETIC")

    if organisation is None:
        return None

    if OrganisationMembership.objects.filter(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).exists():
        return _bundle_from_seed("ORG_OWNER", source="SYNTHETIC")

    active_employee = _get_employee_record_for_org(user, organisation, request=request)
    if active_employee is not None:
        return EffectiveRoleBundle(
            code="EMPLOYEE_SELF",
            scope=AccessRoleScope.ORGANISATION,
            permission_codes=frozenset(),
            scope_summary=({"kind": DataScopeKind.OWN_RECORD, "label": "Own record"},),
            source="SYNTHETIC",
        )
    return None


def _bundle_from_seed(role_code: str, *, source: str) -> EffectiveRoleBundle:
    spec = SEED_ROLES[role_code]
    scopes: tuple[dict[str, str], ...]
    if spec.scope == AccessRoleScope.CONTROL_TOWER:
        scopes = ({"kind": DataScopeKind.ALL_ORGANISATIONS, "label": "All organisations"},)
    else:
        scopes = (
            {"kind": DataScopeKind.CURRENT_ORGANISATION, "label": "Current organisation"},
            {"kind": DataScopeKind.ALL_EMPLOYEES, "label": "All employees"},
        )
    return EffectiveRoleBundle(
        code=spec.code,
        scope=spec.scope,
        permission_codes=frozenset(spec.permissions),
        scope_summary=scopes,
        source=source,
    )


def _summaries_from_scope_records(scope_records: list[AccessScope], role_scope: str) -> tuple[dict[str, str], ...]:
    if not scope_records:
        if role_scope == AccessRoleScope.CONTROL_TOWER:
            return ({"kind": DataScopeKind.ALL_ORGANISATIONS, "label": "All organisations"},)
        return ({"kind": DataScopeKind.ALL_EMPLOYEES, "label": "All employees"},)

    summaries: list[dict[str, str]] = []
    for scope in scope_records:
        if scope.scope_kind == DataScopeKind.SELECTED_DEPARTMENTS and scope.department is not None:
            label = scope.department.name
        elif scope.scope_kind == DataScopeKind.SELECTED_OFFICE_LOCATIONS and scope.office_location is not None:
            label = scope.office_location.name
        elif scope.scope_kind == DataScopeKind.SELECTED_EMPLOYEES and scope.employee is not None:
            label = scope.employee.user.full_name
        elif scope.scope_kind == DataScopeKind.SELECTED_ORGANISATIONS and scope.organisation is not None:
            label = scope.organisation.name
        elif scope.scope_kind == DataScopeKind.OWN_RECORD:
            label = "Own record"
        elif scope.scope_kind == DataScopeKind.REPORTING_TREE:
            label = "Reporting tree"
        else:
            label = scope.value_text or scope.get_scope_kind_display()
        summaries.append({"kind": scope.scope_kind, "label": label})
    return tuple(summaries)


def _get_employee_record_for_org(user: User, organisation: Organisation, *, request=None) -> Employee | None:
    employee = cast(Employee | None, get_active_employee(request, user) if request is not None else None)
    if employee is not None and employee.organisation_id == organisation.id:
        return employee
    return cast(
        Employee | None,
        Employee.objects.filter(
            user=user,
            organisation=organisation,
            status__in=[EmployeeStatus.INVITED, EmployeeStatus.PENDING, EmployeeStatus.ACTIVE],
        )
        .select_related("user")
        .first()
    )


def _mask_value(value: Any):
    if isinstance(value, list):
        return []
    if isinstance(value, dict):
        return None
    return None
