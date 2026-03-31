from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation

from .models import Department
from .repositories import list_departments
from .serializers import DepartmentCreateUpdateSerializer, DepartmentSerializer
from .services import create_department, deactivate_department, update_department


class DepartmentListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        queryset = list_departments(
            organisation,
            include_inactive=request.query_params.get('include_inactive') == 'true',
        )
        return Response(DepartmentSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = DepartmentCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            department = create_department(organisation, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)


class DepartmentDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        department = get_object_or_404(Department, organisation=organisation, id=pk)
        serializer = DepartmentCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            department = update_department(department, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data)


class DepartmentDeactivateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        department = get_object_or_404(Department, organisation=organisation, id=pk)
        try:
            department = deactivate_department(department, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data)
