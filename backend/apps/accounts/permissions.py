from rest_framework.permissions import BasePermission

from apps.organisations.models import OrganisationAccessState, OrganisationBillingStatus

from .models import AccountType
from .workspaces import get_active_admin_organisation, get_active_employee, get_workspace_state


class IsControlTowerUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.account_type == AccountType.CONTROL_TOWER
        )


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
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

        return (
            organisation is not None
            and organisation.billing_status == OrganisationBillingStatus.PAID
            and organisation.access_state == OrganisationAccessState.ACTIVE
        )
