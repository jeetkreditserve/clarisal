from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation

from .models import AttendanceImportJob, AttendanceImportMode
from .serializers import AttendanceImportJobSerializer
from .services import (
    XLSX_CONTENT_TYPE,
    build_attendance_sheet_sample,
    build_normalized_attendance_workbook,
    build_punch_sheet_sample,
    import_attendance_sheet,
    import_punch_sheet,
)


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _build_download_response(content, filename):
    response = HttpResponse(
        content,
        content_type=XLSX_CONTENT_TYPE,
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class OrgAttendanceImportListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = AttendanceImportJob.objects.filter(organisation=organisation).select_related('uploaded_by').prefetch_related('rows')
        return Response(AttendanceImportJobSerializer(queryset, many=True).data)


class OrgAttendanceSheetSampleView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        return _build_download_response(build_attendance_sheet_sample(), 'attendance-sheet-sample.xlsx')


class OrgAttendancePunchSampleView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        return _build_download_response(build_punch_sheet_sample(), 'attendance-punch-sample.xlsx')


class OrgAttendanceSheetImportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request):
        organisation = _get_admin_organisation(request)
        uploaded_file = request.FILES.get('file')
        if uploaded_file is None:
            return Response({'error': 'Upload an Excel .xlsx file.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            job = import_attendance_sheet(organisation=organisation, uploaded_by=request.user, uploaded_file=uploaded_file)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class OrgAttendancePunchImportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request):
        organisation = _get_admin_organisation(request)
        uploaded_file = request.FILES.get('file')
        if uploaded_file is None:
            return Response({'error': 'Upload an Excel .xlsx file.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            job = import_punch_sheet(organisation=organisation, uploaded_by=request.user, uploaded_file=uploaded_file)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class OrgAttendanceNormalizedWorkbookView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        job = get_object_or_404(AttendanceImportJob.objects.prefetch_related('rows'), organisation=organisation, id=pk, mode=AttendanceImportMode.PUNCH_SHEET)
        if job.valid_rows == 0:
            return Response({'error': 'This import job does not have any normalized attendance rows to download.'}, status=status.HTTP_400_BAD_REQUEST)
        filename = f'normalized-attendance-{job.created_at.date().isoformat()}.xlsx'
        return _build_download_response(build_normalized_attendance_workbook(job), filename)
