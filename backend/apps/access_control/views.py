from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, HasPermission, IsOrgAdmin
from apps.accounts.workspaces import get_active_admin_organisation

from .models import AccessPermission, AccessRole, AccessRoleAssignment, AccessRoleScope
from .serializers import (
    AccessPermissionSerializer,
    AccessRoleAssignmentSerializer,
    AccessRoleAssignmentWriteSerializer,
    AccessRoleSerializer,
)


class OrgAccessControlOverviewView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.access_control.manage'

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        roles = AccessRole.objects.filter(scope=AccessRoleScope.ORGANISATION, is_active=True).prefetch_related(
            'role_permissions__permission',
        )
        assignments = (
            AccessRoleAssignment.objects.filter(organisation=organisation, role__scope=AccessRoleScope.ORGANISATION)
            .select_related('user', 'role')
            .prefetch_related('scopes__office_location', 'scopes__department', 'scopes__employee__user')
        )
        permissions = AccessPermission.objects.filter(domain='org', is_active=True)
        return Response(
            {
                'roles': AccessRoleSerializer(roles, many=True).data,
                'permissions': AccessPermissionSerializer(permissions, many=True).data,
                'assignments': AccessRoleAssignmentSerializer(assignments, many=True).data,
            }
        )


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
