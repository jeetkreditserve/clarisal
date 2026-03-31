from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation

from .models import OfficeLocation
from .repositories import list_locations
from .serializers import LocationCreateUpdateSerializer, LocationSerializer
from .services import create_location, deactivate_location, update_location


class LocationListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        queryset = list_locations(
            organisation,
            include_inactive=request.query_params.get('include_inactive') == 'true',
        )
        return Response(LocationSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        serializer = LocationCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            location = create_location(organisation, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)


class LocationDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        location = get_object_or_404(OfficeLocation, organisation=organisation, id=pk)
        serializer = LocationCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            location = update_location(location, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LocationSerializer(location).data)


class LocationDeactivateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        location = get_object_or_404(OfficeLocation, organisation=organisation, id=pk)
        try:
            deactivate_location(location, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LocationSerializer(location).data)
