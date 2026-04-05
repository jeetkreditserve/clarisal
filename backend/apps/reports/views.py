from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin
from apps.accounts.workspaces import get_active_admin_organisation

from .attendance_summary import AttendanceSummaryReport
from .headcount import AttritionReport, HeadcountReport
from .leave_utilization import LeaveUtilizationReport
from .payroll_register import PayrollRegisterReport
from .tax_summary import TaxSummaryReport

REPORT_REGISTRY = {
    'payroll-register': PayrollRegisterReport,
    'headcount': HeadcountReport,
    'attrition': AttritionReport,
    'leave-utilization': LeaveUtilizationReport,
    'attendance-summary': AttendanceSummaryReport,
    'tax-summary': TaxSummaryReport,
}


class OrgReportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

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
