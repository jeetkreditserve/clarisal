from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import BelongsToActiveOrg, IsControlTowerUser, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from apps.approvals.models import ApprovalWorkflow
from apps.approvals.serializers import ApprovalWorkflowSerializer
from apps.communications.models import Notice
from apps.communications.serializers import NoticeSerializer
from apps.departments.models import Department
from apps.departments.repositories import list_departments
from apps.departments.serializers import DepartmentSerializer
from apps.employees.repositories import get_employee, list_employees
from apps.employees.serializers import EmployeeDetailSerializer, EmployeeListSerializer
from apps.locations.models import OfficeLocation
from apps.locations.repositories import list_locations
from apps.locations.serializers import LocationSerializer
from apps.timeoff.models import HolidayCalendar, LeaveCycle, LeavePlan, OnDutyPolicy
from apps.timeoff.serializers import (
    HolidayCalendarSerializer,
    HolidayCalendarWriteSerializer,
    LeaveCycleSerializer,
    LeavePlanSerializer,
    OnDutyPolicySerializer,
)
from apps.timeoff.services import create_holiday_calendar, publish_holiday_calendar, update_holiday_calendar
from .models import Organisation, OrganisationAddress, OrganisationLicenceBatch, OrganisationNote, OrganisationStatus
from .repositories import get_organisations, get_organisation_by_id, get_org_admins
from .serializers import (
    OrganisationListSerializer, OrganisationDetailSerializer,
    OrganisationAddressSerializer,
    OrganisationAddressWriteSerializer,
    CreateOrganisationSerializer, UpdateOrganisationSerializer,
    LicenceBatchMarkPaidSerializer,
    LicenceBatchSerializer,
    LicenceBatchUpdateSerializer,
    LicenceBatchWriteSerializer,
    OrgAdminSerializer, CTDashboardStatsSerializer, OrgDashboardStatsSerializer,
    OrganisationNoteSerializer, OrganisationNoteWriteSerializer,
)
from .services import (
    create_organisation_address,
    create_licence_batch,
    create_organisation_note,
    create_organisation, transition_organisation_state,
    deactivate_organisation_address,
    get_ct_dashboard_stats, get_org_dashboard_stats, get_org_licence_summary,
    mark_licence_batch_paid,
    update_organisation_address,
    update_licence_batch,
    update_organisation_profile,
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
        try:
            org = create_organisation(**serializer.validated_data, created_by=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(org).data, status=status.HTTP_201_CREATED)


class OrganisationDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        return Response(OrganisationDetailSerializer(org).data)

    def patch(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = UpdateOrganisationSerializer(data=request.data, partial=True, context={'organisation': org})
        serializer.is_valid(raise_exception=True)
        try:
            org = update_organisation_profile(org, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
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
            'total_count': summary['active_paid_quantity'],
            'used_count': summary['allocated'],
            'available_count': summary['available'],
            'overage_count': summary['overage'],
            'utilisation_percent': summary['utilisation_percent'],
        })


class OrganisationAddressListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        serializer = OrganisationAddressWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            address = create_organisation_address(
                organisation,
                actor=request.user,
                auto_create_location=True,
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationAddressSerializer(address).data, status=status.HTTP_201_CREATED)


class OrganisationAddressDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, address_id):
        organisation = get_object_or_404(Organisation, id=pk)
        address = get_object_or_404(OrganisationAddress, organisation=organisation, id=address_id)
        serializer = OrganisationAddressWriteSerializer(data=request.data, partial=True, context={'address': address})
        serializer.is_valid(raise_exception=True)
        try:
            address = update_organisation_address(address, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationAddressSerializer(address).data)

    def delete(self, request, pk, address_id):
        organisation = get_object_or_404(Organisation, id=pk)
        address = get_object_or_404(OrganisationAddress, organisation=organisation, id=address_id)
        try:
            address = deactivate_organisation_address(address, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationAddressSerializer(address).data)

class OrganisationAdminsView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        admins = get_org_admins(org)
        return Response(OrgAdminSerializer(admins, many=True).data)


class CtOrganisationEmployeesView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        queryset = list_employees(
            organisation,
            status=request.query_params.get('status'),
            search=request.query_params.get('search'),
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = EmployeeListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CtOrganisationEmployeeDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk, employee_id):
        organisation = get_object_or_404(Organisation, id=pk)
        employee = get_employee(organisation, employee_id)
        return Response(EmployeeDetailSerializer(employee).data)


class CtOrganisationHolidayCalendarListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        calendars = HolidayCalendar.objects.filter(organisation=organisation).prefetch_related('holidays', 'location_assignments')
        return Response(HolidayCalendarSerializer(calendars, many=True).data)

    def post(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        serializer = HolidayCalendarWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            calendar_obj = create_holiday_calendar(
                organisation,
                actor=request.user,
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(HolidayCalendarSerializer(calendar_obj).data, status=status.HTTP_201_CREATED)


class CtOrganisationHolidayCalendarDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, calendar_id):
        organisation = get_object_or_404(Organisation, id=pk)
        calendar_obj = get_object_or_404(HolidayCalendar, organisation=organisation, id=calendar_id)
        serializer = HolidayCalendarWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            calendar_obj = update_holiday_calendar(calendar_obj, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(HolidayCalendarSerializer(calendar_obj).data)


class CtOrganisationHolidayCalendarPublishView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, calendar_id):
        organisation = get_object_or_404(Organisation, id=pk)
        calendar_obj = get_object_or_404(HolidayCalendar, organisation=organisation, id=calendar_id)
        return Response(HolidayCalendarSerializer(publish_holiday_calendar(calendar_obj, actor=request.user)).data)


class CtOrganisationConfigurationView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        workflows = ApprovalWorkflow.objects.filter(organisation=organisation).prefetch_related(
            'rules',
            'stages__approvers__approver_employee__user',
            'stages__fallback_employee__user',
        )
        notices = Notice.objects.filter(organisation=organisation).prefetch_related('departments', 'office_locations', 'employees')
        return Response(
            {
                'locations': LocationSerializer(list_locations(organisation, include_inactive=True), many=True).data,
                'departments': DepartmentSerializer(list_departments(organisation, include_inactive=True), many=True).data,
                'leave_cycles': LeaveCycleSerializer(LeaveCycle.objects.filter(organisation=organisation), many=True).data,
                'leave_plans': LeavePlanSerializer(
                    LeavePlan.objects.filter(organisation=organisation).select_related('leave_cycle').prefetch_related('leave_types', 'rules'),
                    many=True,
                ).data,
                'on_duty_policies': OnDutyPolicySerializer(OnDutyPolicy.objects.filter(organisation=organisation), many=True).data,
                'approval_workflows': ApprovalWorkflowSerializer(workflows, many=True).data,
                'notices': NoticeSerializer(notices, many=True).data,
            }
        )


class CtOrganisationNotesView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        notes = OrganisationNote.objects.filter(organisation=organisation).select_related('created_by')
        return Response(OrganisationNoteSerializer(notes, many=True).data)

    def post(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        serializer = OrganisationNoteWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = create_organisation_note(
            organisation=organisation,
            body=serializer.validated_data['body'],
            created_by=request.user,
        )
        return Response(OrganisationNoteSerializer(note).data, status=status.HTTP_201_CREATED)


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


class OrgProfileView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(organisation).data)

    def patch(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = UpdateOrganisationSerializer(data=request.data, partial=True, context={'organisation': organisation})
        serializer.is_valid(raise_exception=True)
        try:
            organisation = update_organisation_profile(organisation, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationDetailSerializer(organisation).data)


class OrgProfileAddressListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = OrganisationAddressWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            address = create_organisation_address(
                organisation,
                actor=request.user,
                auto_create_location=False,
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationAddressSerializer(address).data, status=status.HTTP_201_CREATED)


class OrgProfileAddressDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, address_id):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        address = get_object_or_404(OrganisationAddress, organisation=organisation, id=address_id)
        serializer = OrganisationAddressWriteSerializer(data=request.data, partial=True, context={'address': address})
        serializer.is_valid(raise_exception=True)
        try:
            address = update_organisation_address(address, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationAddressSerializer(address).data)

    def delete(self, request, address_id):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        address = get_object_or_404(OrganisationAddress, organisation=organisation, id=address_id)
        try:
            address = deactivate_organisation_address(address, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrganisationAddressSerializer(address).data)


class OrganisationLicenceBatchListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        batches = org.licence_batches.select_related('created_by', 'paid_by')
        return Response(LicenceBatchSerializer(batches, many=True).data)

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        serializer = LicenceBatchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            batch = create_licence_batch(org, created_by=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LicenceBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class OrganisationLicenceBatchDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, batch_id):
        org = get_object_or_404(Organisation, id=pk)
        batch = get_object_or_404(OrganisationLicenceBatch, organisation=org, id=batch_id)
        serializer = LicenceBatchUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            batch = update_licence_batch(batch, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LicenceBatchSerializer(batch).data)


class OrganisationLicenceBatchMarkPaidView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, batch_id):
        org = get_object_or_404(Organisation, id=pk)
        batch = get_object_or_404(OrganisationLicenceBatch, organisation=org, id=batch_id)
        serializer = LicenceBatchMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            batch = mark_licence_batch_paid(
                batch,
                paid_by=request.user,
                paid_at=serializer.validated_data.get('paid_at'),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LicenceBatchSerializer(batch).data)
