from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    ActAsSession,
    Organisation,
    OrganisationMembership,
    OrganisationMembershipStatus,
)

from .models import AccountType, User, UserRole

ACTIVE_EMPLOYEE_STATUSES = [
    EmployeeStatus.INVITED,
    EmployeeStatus.PENDING,
    EmployeeStatus.ACTIVE,
]


@dataclass
class WorkspaceState:
    admin_memberships: list[OrganisationMembership]
    employee_records: list[Employee]
    active_admin_membership: OrganisationMembership | None
    active_employee: Employee | None
    active_kind: str | None
    impersonation_session: ActAsSession | None
    impersonated_organisation: Organisation | None


def _clear_control_tower_impersonation_session(request):
    if request is None:
        return
    request.session.pop('ct_act_as_session_id', None)
    request.session.modified = True


def get_active_impersonation_session(request, user: User) -> ActAsSession | None:
    if request is None or user.account_type != AccountType.CONTROL_TOWER:
        return None
    session_id = request.session.get('ct_act_as_session_id')
    if not session_id:
        return None
    act_as_session = (
        ActAsSession.objects.select_related('organisation', 'target_org_admin')
        .filter(
            id=session_id,
            actor=user,
            ended_at__isnull=True,
            revoked_at__isnull=True,
        )
        .first()
    )
    if act_as_session is None:
        _clear_control_tower_impersonation_session(request)
    return act_as_session


def is_control_tower_impersonating(request, user: User) -> bool:
    return get_active_impersonation_session(request, user) is not None


CT_IMPERSONATION_ALLOWED_ACTIONS = frozenset({
    "unlock_account",
    "reset_onboarding_step",
    "extend_licence_expiry",
})


def is_ct_action_allowed_during_impersonation(action_code: str) -> bool:
    return action_code in CT_IMPERSONATION_ALLOWED_ACTIONS


def list_admin_memberships(user: User):
    if user.account_type != AccountType.WORKFORCE:
        return []
    return list(
        OrganisationMembership.objects.select_related('organisation')
        .filter(
            user=user,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        .order_by('organisation__name')
    )


def list_employee_records(user: User):
    if user.account_type != AccountType.WORKFORCE:
        return []
    return list(
        Employee.objects.select_related('organisation')
        .filter(
            user=user,
            status__in=ACTIVE_EMPLOYEE_STATUSES,
        )
        .order_by('organisation__name', 'employee_code')
    )


def get_workspace_state(user: User, request=None) -> WorkspaceState:
    admin_memberships = list_admin_memberships(user)
    employee_records = list_employee_records(user)

    active_admin_membership = None
    active_employee = None
    active_kind = None
    impersonation_session = None
    impersonated_organisation = None

    if user.account_type == AccountType.CONTROL_TOWER and request is not None:
        impersonation_session = get_active_impersonation_session(request, user)
        if impersonation_session is not None:
            impersonated_organisation = impersonation_session.organisation
            active_kind = 'ADMIN'

    if request is not None:
        admin_org_id = request.session.get('active_admin_org_id')
        employee_org_id = request.session.get('active_employee_org_id')
        active_kind = active_kind or request.session.get('active_workspace_kind')

        if admin_org_id and user.account_type == AccountType.WORKFORCE:
            active_admin_membership = next(
                (membership for membership in admin_memberships if str(membership.organisation_id) == str(admin_org_id)),
                None,
            )
        if employee_org_id and user.account_type == AccountType.WORKFORCE:
            active_employee = next(
                (employee for employee in employee_records if str(employee.organisation_id) == str(employee_org_id)),
                None,
            )

    if active_admin_membership is None and admin_memberships:
        active_admin_membership = admin_memberships[0]
    if active_employee is None and employee_records:
        active_employee = employee_records[0]

    if not active_kind:
        if admin_memberships:
            active_kind = 'ADMIN'
        elif employee_records:
            active_kind = 'EMPLOYEE'

    return WorkspaceState(
        admin_memberships=admin_memberships,
        employee_records=employee_records,
        active_admin_membership=active_admin_membership,
        active_employee=active_employee,
        active_kind=active_kind,
        impersonation_session=impersonation_session,
        impersonated_organisation=impersonated_organisation,
    )


def sync_user_role(user: User):
    if user.account_type == AccountType.CONTROL_TOWER:
        new_role = UserRole.CONTROL_TOWER
    elif OrganisationMembership.objects.filter(
        user=user,
        is_org_admin=True,
        status__in=[OrganisationMembershipStatus.ACTIVE, OrganisationMembershipStatus.INVITED],
    ).exists():
        new_role = UserRole.ORG_ADMIN
    elif Employee.objects.filter(user=user, status__in=ACTIVE_EMPLOYEE_STATUSES).exists():
        new_role = UserRole.EMPLOYEE
    else:
        new_role = UserRole.EMPLOYEE

    if user.role != new_role:
        user.role = new_role
        user.save(update_fields=['role', 'modified_at'])
    return user


def initialize_workforce_workspace(request, user: User):
    state = get_workspace_state(user, request)
    if state.admin_memberships and state.active_admin_membership is not None:
        set_active_admin_organisation(request, user, state.active_admin_membership.organisation_id)
    elif state.employee_records and state.active_employee is not None:
        set_active_employee_workspace(request, user, state.active_employee.organisation_id)
    else:
        request.session.pop('active_workspace_kind', None)
        request.session.pop('active_admin_org_id', None)
        request.session.pop('active_employee_org_id', None)


def set_active_admin_organisation(request, user: User, organisation_id):
    membership = OrganisationMembership.objects.select_related('organisation').filter(
        user=user,
        organisation_id=organisation_id,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    ).first()
    if membership is None:
        raise ValueError('You do not have administrator access to that organisation.')

    membership.last_used_at = timezone.now()
    membership.save(update_fields=['last_used_at', 'modified_at'])

    request.session['active_workspace_kind'] = 'ADMIN'
    request.session['active_admin_org_id'] = str(membership.organisation_id)
    request.session.modified = True
    return membership


def set_active_employee_workspace(request, user: User, organisation_id):
    employee = Employee.objects.select_related('organisation').filter(
        user=user,
        organisation_id=organisation_id,
        status__in=ACTIVE_EMPLOYEE_STATUSES,
    ).first()
    if employee is None:
        raise ValueError('You do not have employee access to that organisation.')

    request.session['active_workspace_kind'] = 'EMPLOYEE'
    request.session['active_employee_org_id'] = str(employee.organisation_id)
    request.session.modified = True
    return employee


def get_active_admin_organisation(request, user: User) -> Organisation | None:
    state = get_workspace_state(user, request)
    if state.impersonated_organisation is not None:
        return state.impersonated_organisation
    return state.active_admin_membership.organisation if state.active_admin_membership else None


def get_active_employee(request, user: User) -> Employee | None:
    state = get_workspace_state(user, request)
    return state.active_employee


def get_current_organisation(request, user: User) -> Organisation | None:
    state = get_workspace_state(user, request)
    if state.impersonated_organisation is not None:
        return state.impersonated_organisation
    if state.active_kind == 'ADMIN' and state.active_admin_membership:
        return state.active_admin_membership.organisation
    if state.active_kind == 'EMPLOYEE' and state.active_employee:
        return state.active_employee.organisation
    if state.active_admin_membership:
        return state.active_admin_membership.organisation
    if state.active_employee:
        return state.active_employee.organisation
    return None


def get_default_route(user: User, request=None):
    if user.account_type == AccountType.CONTROL_TOWER:
        if request is not None and is_control_tower_impersonating(request, user):
            return '/org/dashboard'
        return '/ct/dashboard'

    state = get_workspace_state(user, request)
    if state.admin_memberships:
        from apps.organisations.services import is_org_admin_setup_required

        active_organisation = state.active_admin_membership.organisation if state.active_admin_membership else None
        if active_organisation and is_org_admin_setup_required(active_organisation):
            return '/org/setup'
        return '/org/dashboard'
    if state.employee_records:
        employee = state.active_employee or state.employee_records[0]
        if employee.status == EmployeeStatus.INVITED or employee.onboarding_status != 'COMPLETE':
            return '/me/onboarding'
        return '/me/dashboard'
    return '/auth/login'
