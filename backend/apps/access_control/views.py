from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AccountType, User
from apps.accounts.permissions import BelongsToActiveOrg, HasPermission, IsControlTowerUser, IsOrgAdmin
from apps.accounts.workspaces import get_active_admin_organisation
from apps.employees.models import Employee

from .models import AccessPermission, AccessRole, AccessRoleAssignment, AccessRoleScope
from .serializers import (
    AccessPermissionSerializer,
    AccessRoleAssignmentSerializer,
    AccessRoleAssignmentWriteSerializer,
    AccessRoleSerializer,
    AccessRoleWriteSerializer,
    AccessSimulationSerializer,
)
from .services import get_effective_permission_codes, scope_employee_queryset, summarize_effective_scopes


class OrgAccessControlOverviewView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.access_control.manage'

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        roles = _org_roles_queryset(organisation)
        assignments = (
            AccessRoleAssignment.objects.filter(organisation=organisation, role__scope=AccessRoleScope.ORGANISATION)
            .select_related('user', 'role')
            .prefetch_related('scopes__office_location', 'scopes__department', 'scopes__employee__user')
        )
        permissions = AccessPermission.objects.filter(domain='org', is_active=True)
        users = _org_access_users(organisation)
        return Response(
            {
                'roles': AccessRoleSerializer(roles, many=True).data,
                'permissions': AccessPermissionSerializer(permissions, many=True).data,
                'assignments': AccessRoleAssignmentSerializer(assignments, many=True).data,
                'users': users,
            }
        )


class OrgAccessRoleListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.access_control.manage'

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        return Response(AccessRoleSerializer(_org_roles_queryset(organisation), many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = AccessRoleWriteSerializer(data=request.data, context={'organisation': organisation})
        serializer.is_valid(raise_exception=True)
        role = serializer.save(organisation=organisation, actor=request.user)
        return Response(AccessRoleSerializer(role).data, status=status.HTTP_201_CREATED)


class OrgAccessControlAssignmentListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.access_control.manage'

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        assignments = (
            AccessRoleAssignment.objects.filter(organisation=organisation, role__scope=AccessRoleScope.ORGANISATION)
            .select_related('user', 'role')
            .prefetch_related('scopes__office_location', 'scopes__department', 'scopes__employee__user')
        )
        return Response(AccessRoleAssignmentSerializer(assignments, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = AccessRoleAssignmentWriteSerializer(data=request.data, context={'organisation': organisation})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(organisation=organisation, actor=request.user)
        return Response(AccessRoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class CtAccessControlOverviewView(APIView):
    permission_classes = [IsControlTowerUser, HasPermission]
    permission_code = 'ct.organisations.read'

    def get(self, request):
        roles = AccessRole.objects.filter(
            scope=AccessRoleScope.CONTROL_TOWER,
            organisation__isnull=True,
            is_active=True,
        ).prefetch_related('role_permissions__permission')
        assignments = (
            AccessRoleAssignment.objects.filter(
                organisation__isnull=True,
                role__scope=AccessRoleScope.CONTROL_TOWER,
            )
            .select_related('user', 'role')
            .prefetch_related('scopes')
        )
        permissions = AccessPermission.objects.filter(domain='ct', is_active=True)
        users = _ct_access_users()
        return Response(
            {
                'roles': AccessRoleSerializer(roles, many=True).data,
                'permissions': AccessPermissionSerializer(permissions, many=True).data,
                'assignments': AccessRoleAssignmentSerializer(assignments, many=True).data,
                'users': users,
            }
        )


class CtAccessRoleListCreateView(APIView):
    permission_classes = [IsControlTowerUser, HasPermission]

    def get_permission_code(self, request):
        return 'ct.organisations.write' if request.method == 'POST' else 'ct.organisations.read'

    def get(self, request):
        roles = AccessRole.objects.filter(
            scope=AccessRoleScope.CONTROL_TOWER,
            organisation__isnull=True,
            is_active=True,
        ).prefetch_related('role_permissions__permission')
        return Response(AccessRoleSerializer(roles, many=True).data)

    def post(self, request):
        serializer = AccessRoleWriteSerializer(data=request.data, context={})
        serializer.is_valid(raise_exception=True)
        role = serializer.save(organisation=None, actor=request.user)
        return Response(AccessRoleSerializer(role).data, status=status.HTTP_201_CREATED)


class CtAccessRoleAssignmentListCreateView(APIView):
    permission_classes = [IsControlTowerUser, HasPermission]

    def get_permission_code(self, request):
        return 'ct.organisations.write' if request.method == 'POST' else 'ct.organisations.read'

    def get(self, request):
        assignments = (
            AccessRoleAssignment.objects.filter(
                organisation__isnull=True,
                role__scope=AccessRoleScope.CONTROL_TOWER,
            )
            .select_related('user', 'role')
            .prefetch_related('scopes')
        )
        return Response(AccessRoleAssignmentSerializer(assignments, many=True).data)

    def post(self, request):
        serializer = AccessRoleAssignmentWriteSerializer(data=request.data, context={})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(organisation=None, actor=request.user)
        return Response(AccessRoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class OrgAccessSimulationView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.access_control.manage'

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = AccessSimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, id=serializer.validated_data['user_id'])
        employee = None
        employee_access = None
        if serializer.validated_data.get('employee_id'):
            employee = get_object_or_404(Employee, organisation=organisation, id=serializer.validated_data['employee_id'])
            employee_access = {
                'employee_id': str(employee.id),
                'allowed': scope_employee_queryset(
                    Employee.objects.filter(id=employee.id),
                    user,
                    organisation=organisation,
                    request=request,
                ).exists(),
            }
        return Response(
            {
                'user_id': str(user.id),
                'organisation_id': str(organisation.id),
                'effective_permissions': get_effective_permission_codes(user, organisation=organisation, request=request),
                'effective_scopes': summarize_effective_scopes(user, organisation=organisation, request=request),
                'employee_access': employee_access,
            }
        )


def _org_roles_queryset(organisation):
    return AccessRole.objects.filter(
        Q(organisation__isnull=True) | Q(organisation=organisation),
        scope=AccessRoleScope.ORGANISATION,
        is_active=True,
    ).prefetch_related('role_permissions__permission')


def _user_summary(user: User) -> dict[str, str]:
    return {
        'id': str(user.id),
        'email': user.email,
        'full_name': user.full_name,
        'account_type': user.account_type,
    }


def _org_access_users(organisation) -> list[dict[str, str]]:
    users: dict[str, dict[str, str]] = {}
    membership_users = User.objects.filter(organisation_memberships__organisation=organisation).distinct()
    employee_users = User.objects.filter(employee_records__organisation=organisation).distinct()
    for user in membership_users.union(employee_users):
        users[str(user.id)] = _user_summary(user)
    return sorted(users.values(), key=lambda item: (item['full_name'] or item['email']).lower())


def _ct_access_users() -> list[dict[str, str]]:
    return [_user_summary(user) for user in User.objects.filter(account_type=AccountType.CONTROL_TOWER, is_active=True).order_by('email')]
