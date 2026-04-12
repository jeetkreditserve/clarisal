from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.access_control.services import has_permission as has_access_permission
from apps.organisations.models import OrganisationAccessState, OrganisationBillingStatus
from apps.organisations.services import get_org_operations_guard, is_org_feature_enabled

from .models import AccountType
from .workspaces import (
    get_active_admin_organisation,
    get_active_employee,
    get_current_organisation,
    get_workspace_state,
    is_control_tower_impersonating,
    is_ct_action_allowed_during_impersonation,
)

MODULE_FEATURE_FLAG_MAP = {
    'apps.approvals.': 'APPROVALS',
    'apps.attendance.': 'ATTENDANCE',
    'apps.biometrics.': 'BIOMETRICS',
    'apps.communications.': 'NOTICES',
    'apps.payroll.': 'PAYROLL',
    'apps.performance.': 'PERFORMANCE',
    'apps.recruitment.': 'RECRUITMENT',
    'apps.reports.': 'REPORTS',
    'apps.timeoff.': 'TIMEOFF',
}


def _resolve_feature_flag_code(view):
    explicit_code = getattr(view, 'feature_flag_code', None)
    if explicit_code:
        return explicit_code
    module_path = getattr(view.__class__, '__module__', '')
    for module_prefix, feature_code in MODULE_FEATURE_FLAG_MAP.items():
        if module_path.startswith(module_prefix):
            return feature_code
    return None


class IsControlTowerUser(BasePermission):
    def has_permission(self, request, view):
        if not (
            request.user.is_authenticated
            and request.user.account_type == AccountType.CONTROL_TOWER
        ):
            return False
        if request.method in SAFE_METHODS:
            return True
        if not is_control_tower_impersonating(request, request.user):
            return True
        if getattr(view, 'ct_impersonation_passthrough', False):
            return True

        action_code = getattr(view, 'ct_impersonation_action_code', None)
        resolver = getattr(view, 'get_ct_impersonation_action_code', None)
        if action_code is None and callable(resolver):
            action_code = resolver()
        if action_code and is_ct_action_allowed_during_impersonation(action_code):
            return True

        self.message = 'Control Tower impersonation only allows a limited set of write actions.'
        return False


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        if (
            request.user.is_authenticated
            and request.user.account_type == AccountType.CONTROL_TOWER
            and is_control_tower_impersonating(request, request.user)
        ):
            return request.method in SAFE_METHODS
        return (
            request.user.is_authenticated
            and request.user.account_type == AccountType.WORKFORCE
            and bool(get_workspace_state(request.user, request).admin_memberships)
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.account_type == AccountType.WORKFORCE
            and bool(get_workspace_state(request.user, request).employee_records)
        )


class IsOrgAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return IsControlTowerUser().has_permission(request, view) or IsOrgAdmin().has_permission(request, view)


class BelongsToActiveOrg(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.account_type == AccountType.CONTROL_TOWER:
            return True

        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            active_employee = get_active_employee(request, request.user)
            organisation = active_employee.organisation if active_employee else None

        in_active_org = (
            organisation is not None
            and organisation.billing_status == OrganisationBillingStatus.PAID
            and organisation.access_state == OrganisationAccessState.ACTIVE
        )
        if not in_active_org:
            return False
        feature_flag_code = _resolve_feature_flag_code(view)
        if feature_flag_code:
            is_enabled = is_org_feature_enabled(organisation, feature_flag_code)
            if not is_enabled:
                self.message = f'The {feature_flag_code.lower()} module is disabled for this organisation.'
                return False
        return True


class OrgAdminMutationAllowed(BasePermission):
    message = 'Organisation admin actions are blocked because the organisation licence has expired.'

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        if request.user.account_type == AccountType.CONTROL_TOWER and is_control_tower_impersonating(request, request.user):
            self.message = 'Control Tower impersonation is read-only. Stop impersonating before changing organisation data.'
            return False
        if request.user.account_type != AccountType.WORKFORCE:
            return True
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return False
        return not get_org_operations_guard(organisation)['admin_mutations_blocked']


class ApprovalActionsAllowed(BasePermission):
    message = 'Approval actions are blocked because the organisation licence has expired.'

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        if request.user.account_type == AccountType.CONTROL_TOWER:
            return True
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            active_employee = get_active_employee(request, request.user)
            organisation = active_employee.organisation if active_employee else None
        if organisation is None:
            return False
        return not get_org_operations_guard(organisation)['approval_actions_blocked']


class HasPermission(BasePermission):
    message = 'You do not have permission to perform this action.'

    def _permission_code(self, request, view):
        resolver = getattr(view, 'get_permission_code', None)
        if callable(resolver):
            return resolver(request)
        return getattr(view, 'permission_code', None)

    def has_permission(self, request, view):
        permission_code = self._permission_code(request, view)
        if not permission_code:
            return True
        organisation = get_current_organisation(request, request.user)
        allowed = has_access_permission(
            request.user,
            permission_code,
            organisation=organisation,
            request=request,
        )
        if not allowed:
            self.message = f'Missing permission: {permission_code}'
        return allowed


class ScopedOrgAccess(HasPermission):
    pass


class ScopedControlTowerAccess(HasPermission):
    pass
