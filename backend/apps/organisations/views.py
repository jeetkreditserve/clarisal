from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsControlTowerUser
from .models import Organisation, OrganisationStatus
from .repositories import get_organisations, get_organisation_by_id, get_org_admins
from .serializers import (
    OrganisationListSerializer, OrganisationDetailSerializer,
    CreateOrganisationSerializer, UpdateOrganisationSerializer,
    LicenceUpdateSerializer, OrgAdminSerializer, CTDashboardStatsSerializer,
)
from .services import (
    create_organisation, transition_organisation_state,
    update_licence_count, get_ct_dashboard_stats,
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


class OrganisationLicencesView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        return Response({'total_count': org.licence_count, 'used_count': 0})

    def patch(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = LicenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_licence_count(org, serializer.validated_data['licence_count'])
        return Response({'total_count': org.licence_count, 'used_count': 0})


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
