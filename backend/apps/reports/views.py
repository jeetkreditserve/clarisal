from __future__ import annotations

from datetime import date

from django.core.files.storage import default_storage
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, HasPermission, IsOrgAdmin
from apps.accounts.workspaces import get_active_admin_organisation

from .attendance_summary import AttendanceSummaryReport
from .headcount import AttritionReport, HeadcountReport
from .leave_utilization import LeaveUtilizationReport
from .models import ReportDataset, ReportFolder, ReportRun, ReportTemplate
from .payroll_register import PayrollRegisterReport
from .query_engine import ReportValidationError, preview_report
from .serializers import (
    ReportDatasetSerializer,
    ReportFolderSerializer,
    ReportRunSerializer,
    ReportTemplateSerializer,
    ReportTemplateWriteSerializer,
)
from .tasks import run_report_task
from .tax_summary import TaxSummaryReport

REPORT_REGISTRY = {
    'payroll-register': PayrollRegisterReport,
    'headcount': HeadcountReport,
    'attrition': AttritionReport,
    'leave-utilization': LeaveUtilizationReport,
    'attendance-summary': AttendanceSummaryReport,
    'tax-summary': TaxSummaryReport,
}


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('No active org workspace.')
    return organisation


class ReportDatasetListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.read'

    def get(self, request):
        datasets = ReportDataset.objects.filter(is_active=True).prefetch_related('fields')
        return Response(ReportDatasetSerializer(datasets, many=True).data)


class ReportFolderListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.builder.manage'

    def get(self, request):
        organisation = _get_admin_organisation(request)
        folders = ReportFolder.objects.filter(organisation=organisation)
        return Response(ReportFolderSerializer(folders, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ReportFolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        folder = ReportFolder.objects.create(
            organisation=organisation,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            created_by=request.user,
        )
        return Response(ReportFolderSerializer(folder).data, status=status.HTTP_201_CREATED)


def _template_payload(serializer, organisation, user, template=None):
    data = serializer.validated_data
    dataset = ReportDataset.objects.get(code=data['dataset_code'], is_active=True)
    folder = None
    if data.get('folder_id'):
        folder = ReportFolder.objects.get(organisation=organisation, id=data['folder_id'])
    attrs = {
        'organisation': organisation,
        'folder': folder,
        'dataset': dataset,
        'name': data['name'],
        'description': data.get('description', ''),
        'status': data.get('status', ReportTemplate.Status.DRAFT),
        'owner': user,
        'columns': data['columns'],
        'filters': data.get('filters', []),
        'filter_logic': data.get('filter_logic', ''),
        'groupings': data.get('groupings', []),
        'summaries': data.get('summaries', []),
        'formula_fields': data.get('formula_fields', []),
        'chart': data.get('chart', {}),
    }
    if template is None:
        return ReportTemplate(**attrs)
    for key, value in attrs.items():
        setattr(template, key, value)
    return template


class ReportTemplateListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]

    def get_permission_code(self, request):
        return 'org.reports.builder.manage' if request.method == 'POST' else 'org.reports.read'

    def get(self, request):
        organisation = _get_admin_organisation(request)
        templates = ReportTemplate.objects.filter(organisation=organisation).select_related('dataset', 'folder')
        return Response(ReportTemplateSerializer(templates, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ReportTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            template = _template_payload(serializer, organisation, request.user)
            preview_report(template, request.user, organisation, limit=1)
            template.save()
        except (ReportDataset.DoesNotExist, ReportFolder.DoesNotExist, ReportValidationError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReportTemplateSerializer(template).data, status=status.HTTP_201_CREATED)


class ReportTemplateDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]

    def get_permission_code(self, request):
        return 'org.reports.builder.manage' if request.method in {'PATCH', 'PUT'} else 'org.reports.read'

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        template = get_object_or_404_report_template(organisation, pk)
        return Response(ReportTemplateSerializer(template).data)

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        template = get_object_or_404_report_template(organisation, pk)
        serializer = ReportTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            template = _template_payload(serializer, organisation, request.user, template=template)
            preview_report(template, request.user, organisation, limit=1)
            template.version += 1
            template.save()
        except (ReportDataset.DoesNotExist, ReportFolder.DoesNotExist, ReportValidationError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReportTemplateSerializer(template).data)


def get_object_or_404_report_template(organisation, pk):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(
        ReportTemplate.objects.select_related('dataset', 'folder').filter(organisation=organisation),
        id=pk,
    )


class ReportTemplateDraftPreviewView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.read'

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ReportTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            template = _template_payload(serializer, organisation, request.user)
            result = preview_report(template, request.user, organisation)
        except (ReportDataset.DoesNotExist, ReportFolder.DoesNotExist, ReportValidationError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ReportTemplatePreviewView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.read'

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        template = get_object_or_404_report_template(organisation, pk)
        try:
            result = preview_report(template, request.user, organisation)
        except ReportValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ReportTemplateRunView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]

    def get_permission_code(self, request):
        file_format = request.data.get('file_format', 'xlsx')
        if file_format in {'csv', 'xlsx'}:
            return 'org.reports.export'
        return 'org.reports.read'

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        template = get_object_or_404_report_template(organisation, pk)
        file_format = request.data.get('file_format', 'xlsx')
        if file_format not in {'csv', 'xlsx'}:
            return Response({'error': 'Unsupported file format.'}, status=status.HTTP_400_BAD_REQUEST)
        run = ReportRun.objects.create(
            organisation=organisation,
            template=template,
            requested_by=request.user,
            parameters=request.data.get('parameters', {}),
        )
        run_report_task(str(run.id), file_format)
        run.refresh_from_db()
        return Response(ReportRunSerializer(run).data, status=status.HTTP_201_CREATED)


class ReportRunListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.read'

    def get(self, request):
        organisation = _get_admin_organisation(request)
        runs = (
            ReportRun.objects.filter(organisation=organisation)
            .select_related('template', 'requested_by')
            .prefetch_related('exports')
        )
        return Response(ReportRunSerializer(runs, many=True).data)


class ReportRunDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.read'

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        run = get_object_or_404_report_run(organisation, pk)
        return Response(ReportRunSerializer(run).data)


class ReportExportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]
    permission_code = 'org.reports.export'

    def get(self, request, pk, export_id):
        organisation = _get_admin_organisation(request)
        run = get_object_or_404_report_run(organisation, pk)
        export = get_object_or_404_report_export(run, export_id)
        return FileResponse(
            default_storage.open(export.storage_key, 'rb'),
            content_type=export.content_type,
            as_attachment=True,
            filename=export.file_name,
        )


def get_object_or_404_report_run(organisation, pk):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(
        ReportRun.objects.select_related('template', 'requested_by').prefetch_related('exports').filter(organisation=organisation),
        id=pk,
    )


def get_object_or_404_report_export(run, export_id):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(run.exports.all(), id=export_id)


class OrgReportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, HasPermission]

    def get_permission_code(self, request):
        report_format = request.query_params.get('file_format', 'json')
        if report_format in {'csv', 'xlsx'}:
            return 'org.reports.export'
        return 'org.reports.read'

    def get(self, request, report_type: str):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'No active org workspace.'}, status=status.HTTP_400_BAD_REQUEST)
        if report_type not in REPORT_REGISTRY:
            return Response({'error': 'Unknown report type.'}, status=status.HTTP_404_NOT_FOUND)

        kwargs: dict[str, object] = {'organisation': organisation}
        if report_type == 'payroll-register':
            pay_run_id = request.query_params.get('pay_run_id')
            if not pay_run_id:
                return Response({'error': 'pay_run_id is required for payroll-register.'}, status=status.HTTP_400_BAD_REQUEST)
            kwargs['pay_run_id'] = pay_run_id
        elif report_type == 'attendance-summary':
            kwargs['month'] = int(request.query_params.get('month', date.today().month))
            kwargs['year'] = int(request.query_params.get('year', date.today().year))
        elif report_type == 'tax-summary':
            kwargs['fiscal_year'] = request.query_params.get('fiscal_year', f'{date.today().year}-{date.today().year + 1}')
        elif report_type == 'attrition':
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            kwargs['start_date'] = date.fromisoformat(start_date) if start_date else None
            kwargs['end_date'] = date.fromisoformat(end_date) if end_date else None

        report = REPORT_REGISTRY[report_type](**kwargs)
        report_format = request.query_params.get('file_format', 'json')
        if report_format == 'csv':
            return report.to_csv_response()
        if report_format == 'xlsx':
            return report.to_excel_response()
        return Response(report.to_json())
