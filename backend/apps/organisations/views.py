from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import BelongsToActiveOrg, IsControlTowerUser, IsOrgAdmin
from apps.accounts.workspaces import get_active_admin_organisation
from .models import Organisation, OrganisationStatus
from .repositories import get_organisations, get_organisation_by_id, get_org_admins
from .serializers import (
    OrganisationListSerializer, OrganisationDetailSerializer,
    CreateOrganisationSerializer, UpdateOrganisationSerializer,
    LicenceUpdateSerializer, OrgAdminSerializer, CTDashboardStatsSerializer, OrgDashboardStatsSerializer,
)
from .services import (
    create_organisation, transition_organisation_state,
    update_licence_count, get_ct_dashboard_stats, get_org_dashboard_stats, get_org_licence_summary,
)


class OrganisationListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request):
        qs = get_organisations()
        search = request.query_params.get('search')
        status_filter = request.query_params.get('status')
        if search:
            qs = qs.filter(name__icontains=search)
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = OrganisationListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateOrganisationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = create_organisation(**serializer.validated_data, created_by=request.user)
        return Response(OrganisationDetailSerializer(org).data, status=status.HTTP_201_CREATED)


class OrganisationDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        return Response(OrganisationDetailSerializer(org).data)

    def patch(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = UpdateOrganisationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(org, attr, value)
        org.save()
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationActivateView(APIView):
    """Mark organisation payment received (PENDING -> PAID)."""
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        note = request.data.get('note', '')
        try:
            transition_organisation_state(org, OrganisationStatus.PAID, request.user, note=note)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationSuspendView(APIView):
    """Suspend an active organisation."""
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        note = request.data.get('note', '')
        try:
            transition_organisation_state(org, OrganisationStatus.SUSPENDED, request.user, note=note)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationRestoreView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        note = request.data.get('note', '')
        try:
            transition_organisation_state(org, OrganisationStatus.ACTIVE, request.user, note=note)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(org).data)


class OrganisationLicencesView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        summary = get_org_licence_summary(org)
        return Response({
            'total_count': summary['purchased'],
            'used_count': summary['allocated'],
            'available_count': summary['available'],
            'utilisation_percent': summary['utilisation_percent'],
        })

    def patch(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = LicenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            update_licence_count(
                org,
                serializer.validated_data['licence_count'],
                changed_by=request.user,
                note=serializer.validated_data.get('note', ''),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        summary = get_org_licence_summary(org)
        return Response({
            'total_count': summary['purchased'],
            'used_count': summary['allocated'],
            'available_count': summary['available'],
            'utilisation_percent': summary['utilisation_percent'],
        })


class OrganisationAdminsView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        admins = get_org_admins(org)
        return Response(OrgAdminSerializer(admins, many=True).data)


class CTDashboardStatsView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request):
        stats = get_ct_dashboard_stats()
        return Response(CTDashboardStatsSerializer(stats).data)


class OrgDashboardStatsView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        stats = get_org_dashboard_stats(organisation)
        return Response(OrgDashboardStatsSerializer(stats).data)
