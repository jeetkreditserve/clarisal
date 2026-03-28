from rest_framework.permissions import BasePermission
from .models import UserRole


class IsControlTowerUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.CONTROL_TOWER
        )


class IsOrgAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.ORG_ADMIN
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.EMPLOYEE
        )


class IsOrgAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [UserRole.CONTROL_TOWER, UserRole.ORG_ADMIN]
        )


class BelongsToActiveOrg(BasePermission):
    """
    Ensures Org Admin and Employee users can only act if their org is PAID or ACTIVE.
    Control Tower users always pass.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == UserRole.CONTROL_TOWER:
            return True
        org = request.user.organisation
        return org is not None and org.status in ['PAID', 'ACTIVE']
