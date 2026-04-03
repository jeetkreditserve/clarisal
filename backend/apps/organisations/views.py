from django.db.models import Count, F, Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsControlTowerUser, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from apps.approvals.models import ApprovalAction, ApprovalActionStatus, ApprovalRun, ApprovalRunStatus, ApprovalWorkflow
from apps.approvals.serializers import ApprovalWorkflowSerializer, ApprovalWorkflowWriteSerializer
from apps.approvals.views import _upsert_workflow as upsert_approval_workflow
from apps.attendance.models import (
    AttendanceImportJob,
    AttendancePolicy,
    AttendanceRegularizationRequest,
    AttendanceRegularizationStatus,
    AttendanceSourceConfig,
)
from apps.attendance.services import get_org_attendance_dashboard
from apps.communications.models import Notice
from apps.communications.serializers import NoticeSerializer, NoticeWriteSerializer
from apps.communications.services import create_notice, publish_notice, update_notice
from apps.departments.models import Department
from apps.departments.repositories import list_departments
from apps.departments.serializers import DepartmentCreateUpdateSerializer, DepartmentSerializer
from apps.departments.services import create_department, deactivate_department, update_department
from apps.documents.models import EmployeeDocumentRequest, EmployeeDocumentRequestStatus
from apps.employees.models import Employee, EmployeeOnboardingStatus
from apps.employees.repositories import get_employee, list_employees
from apps.employees.serializers import CtEmployeeDetailSerializer, CtEmployeeListSerializer
from apps.locations.models import OfficeLocation
from apps.locations.repositories import list_locations
from apps.locations.serializers import LocationCreateUpdateSerializer, LocationSerializer
from apps.locations.services import create_location, deactivate_location, update_location
from apps.payroll.models import (
    CompensationAssignment,
    CompensationAssignmentStatus,
    CompensationTemplate,
    PayrollRun,
    PayrollRunItemStatus,
    PayrollTaxSlabSet,
    Payslip,
)
from apps.timeoff.models import HolidayCalendar, LeaveCycle, LeavePlan, LeaveType, OnDutyPolicy
from apps.timeoff.serializers import (
    HolidayCalendarSerializer,
    HolidayCalendarWriteSerializer,
    LeaveCycleSerializer,
    LeaveCycleWriteSerializer,
    LeavePlanSerializer,
    LeavePlanWriteSerializer,
    OnDutyPolicySerializer,
    OnDutyPolicyWriteSerializer,
)
from apps.timeoff.services import (
    create_holiday_calendar,
    create_leave_plan,
    publish_holiday_calendar,
    update_holiday_calendar,
    update_leave_plan,
    upsert_leave_cycle,
    upsert_on_duty_policy,
)

from .models import Organisation, OrganisationAddress, OrganisationLicenceBatch, OrganisationNote, OrganisationStatus
from .repositories import get_org_admins, get_organisations
from .serializers import (
    CreateOrganisationSerializer,
    CTDashboardStatsSerializer,
    LicenceBatchMarkPaidSerializer,
    LicenceBatchSerializer,
    LicenceBatchUpdateSerializer,
    LicenceBatchWriteSerializer,
    OrgAdminSerializer,
    OrgAdminSetupStateSerializer,
    OrgAdminSetupUpdateSerializer,
    OrganisationAddressSerializer,
    OrganisationAddressWriteSerializer,
    OrganisationDetailSerializer,
    OrganisationListSerializer,
    OrganisationNoteSerializer,
    OrganisationNoteWriteSerializer,
    OrgDashboardStatsSerializer,
    UpdateOrganisationSerializer,
)
from .services import (
    create_licence_batch,
    create_organisation,
    create_organisation_address,
    create_organisation_note,
    deactivate_org_admin_membership,
    deactivate_organisation_address,
    get_ct_dashboard_stats,
    get_org_admin_setup_state,
    get_org_dashboard_stats,
    get_org_licence_summary,
    mark_licence_batch_paid,
    reactivate_org_admin_membership,
    revoke_org_admin_membership_invitation,
    transition_organisation_state,
    update_licence_batch,
    update_org_admin_setup_state,
    update_organisation_address,
    update_organisation_profile,
)


def _get_ct_organisation(pk):
    return get_object_or_404(Organisation, id=pk)


def _resolve_leave_plan_rules(organisation, rules_payload):
    return [
        {
            'id': rule.get('id'),
            'name': rule['name'],
            'priority': rule.get('priority', 100),
            'is_active': rule.get('is_active', True),
            'department': get_object_or_404(Department, organisation=organisation, id=rule['department_id']) if rule.get('department_id') else None,
            'office_location': get_object_or_404(OfficeLocation, organisation=organisation, id=rule['office_location_id']) if rule.get('office_location_id') else None,
            'specific_employee': get_object_or_404(Employee, organisation=organisation, id=rule['specific_employee_id']) if rule.get('specific_employee_id') else None,
            'employment_type': rule.get('employment_type', ''),
            'designation': rule.get('designation', ''),
        }
        for rule in rules_payload
    ]


def _support_diagnostic(*, code, severity, title, detail, action):
    return {
        'code': code,
        'severity': severity,
        'title': title,
        'detail': detail,
        'action': action,
    }


def _build_ct_payroll_diagnostics(
    *,
    active_employee_count,
    tax_slab_set_count,
    compensation_template_count,
    approved_assignment_count,
    pending_assignment_count,
    payroll_runs,
):
    diagnostics = []
    if tax_slab_set_count == 0:
        diagnostics.append(
            _support_diagnostic(
                code='MISSING_TAX_SLAB_SET',
                severity='critical',
                title='Payroll tax slab set missing',
                detail='No organisation payroll tax slab set is configured, so statutory payroll deductions cannot be validated.',
                action='Create or derive an org tax slab set before running payroll.',
            )
        )
    if compensation_template_count == 0:
        diagnostics.append(
            _support_diagnostic(
                code='NO_COMPENSATION_TEMPLATES',
                severity='critical',
                title='No compensation templates configured',
                detail='The organisation has no reusable salary structures configured for payroll setup.',
                action='Create and approve at least one compensation template.',
            )
        )
    if active_employee_count > 0 and approved_assignment_count == 0:
        diagnostics.append(
            _support_diagnostic(
                code='NO_APPROVED_ASSIGNMENTS',
                severity='critical',
                title='No approved employee compensation assignments',
                detail=f'{active_employee_count} active employees exist, but none have an approved compensation assignment for payroll processing.',
                action='Approve employee compensation assignments before calculating payroll.',
            )
        )
    if pending_assignment_count > 0:
        diagnostics.append(
            _support_diagnostic(
                code='PENDING_ASSIGNMENTS',
                severity='warning',
                title='Compensation assignments still pending approval',
                detail=f'{pending_assignment_count} employee assignment(s) are waiting on approval and may block payroll readiness.',
                action='Review pending assignment approvals and finalize the intended effective versions.',
            )
        )
    exception_runs = [run for run in payroll_runs if run['exception_count'] > 0]
    if exception_runs:
        latest_exception_run = exception_runs[0]
        diagnostics.append(
            _support_diagnostic(
                code='RUN_EXCEPTIONS_PRESENT',
                severity='warning',
                title='Payroll run exceptions need investigation',
                detail=f"{latest_exception_run['name']} currently has {latest_exception_run['exception_count']} exception item(s).",
                action='Inspect the latest run exception messages before submission or finalization.',
            )
        )
    return diagnostics


def _build_ct_attendance_diagnostics(
    *,
    policy_count,
    active_source_count,
    pending_regularizations,
    incomplete_count,
    recent_imports,
):
    diagnostics = []
    if policy_count == 0:
        diagnostics.append(
            _support_diagnostic(
                code='NO_ATTENDANCE_POLICY',
                severity='critical',
                title='No default attendance policy configured',
                detail='Attendance calculations and punch interpretation have no configured default policy for this organisation.',
                action='Create and activate a default attendance policy before relying on attendance summaries.',
            )
        )
    if active_source_count == 0:
        diagnostics.append(
            _support_diagnostic(
                code='NO_ACTIVE_ATTENDANCE_SOURCE',
                severity='warning',
                title='No active attendance source connected',
                detail='The organisation has no active attendance source, so attendance capture depends on manual or import-driven workflows.',
                action='Configure and activate an attendance source or confirm the intended manual operating model.',
            )
        )
    if pending_regularizations > 0:
        diagnostics.append(
            _support_diagnostic(
                code='PENDING_REGULARIZATIONS',
                severity='warning',
                title='Attendance regularizations are waiting on review',
                detail=f'{pending_regularizations} attendance correction request(s) are still pending approval.',
                action='Review the regularization queue before attendance data is used for payroll.',
            )
        )
    failed_imports = [job for job in recent_imports if job.status == 'FAILED']
    if failed_imports:
        diagnostics.append(
            _support_diagnostic(
                code='FAILED_IMPORTS',
                severity='warning',
                title='Recent attendance import failures detected',
                detail=f'{len(failed_imports)} recent attendance import job(s) failed validation or posting.',
                action='Inspect the most recent failed import and correct workbook errors before retrying.',
            )
        )
    review_imports = [job for job in recent_imports if job.status == 'READY_FOR_REVIEW']
    if review_imports:
        diagnostics.append(
            _support_diagnostic(
                code='IMPORTS_NEED_REVIEW',
                severity='warning',
                title='Attendance imports need review before posting',
                detail=f'{len(review_imports)} import job(s) are waiting for review and posting.',
                action='Review incomplete or normalized punch rows before attendance is treated as final.',
            )
        )
    if incomplete_count > 0:
        diagnostics.append(
            _support_diagnostic(
                code='INCOMPLETE_ATTENDANCE_TODAY',
                severity='info',
                title='Incomplete punches present in today attendance',
                detail=f'{incomplete_count} employees currently have incomplete attendance for today.',
                action='Guide the org admin to review missed punch or regularization cases.',
            )
        )
    return diagnostics


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
        admins = get_org_admins(org, include_inactive=True)
        return Response(OrgAdminSerializer(admins, many=True).data)


class CtOrganisationAdminDeactivateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, admin_id):
        organisation = _get_ct_organisation(pk)
        membership = get_object_or_404(
            organisation.memberships.select_related('user'),
            user_id=admin_id,
            is_org_admin=True,
        )
        try:
            membership = deactivate_org_admin_membership(organisation, membership.user, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrgAdminSerializer(membership).data)


class CtOrganisationAdminReactivateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, admin_id):
        organisation = _get_ct_organisation(pk)
        membership = get_object_or_404(
            organisation.memberships.select_related('user'),
            user_id=admin_id,
            is_org_admin=True,
        )
        try:
            membership = reactivate_org_admin_membership(organisation, membership.user, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrgAdminSerializer(membership).data)


class CtOrganisationAdminRevokePendingView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, admin_id):
        organisation = _get_ct_organisation(pk)
        membership = get_object_or_404(
            organisation.memberships.select_related('user'),
            user_id=admin_id,
            is_org_admin=True,
        )
        try:
            membership = revoke_org_admin_membership_invitation(organisation, membership.user, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrgAdminSerializer(membership).data)


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
        serializer = CtEmployeeListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CtOrganisationEmployeeDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk, employee_id):
        organisation = get_object_or_404(Organisation, id=pk)
        employee = get_employee(organisation, employee_id)
        return Response(CtEmployeeDetailSerializer(employee).data)


class CtOrganisationPayrollSummaryView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        pay_runs = PayrollRun.objects.filter(organisation=organisation).prefetch_related('items').order_by('-period_year', '-period_month', '-created_at')
        runs_payload = []
        for pay_run in pay_runs:
            ready_count = 0
            exception_count = 0
            exception_messages = []
            for item in pay_run.items.all():
                if item.status == PayrollRunItemStatus.READY:
                    ready_count += 1
                elif item.status == PayrollRunItemStatus.EXCEPTION:
                    exception_count += 1
                    if item.message and item.message not in exception_messages and len(exception_messages) < 3:
                        exception_messages.append(item.message)

            runs_payload.append(
                {
                    'id': str(pay_run.id),
                    'name': pay_run.name,
                    'period_year': pay_run.period_year,
                    'period_month': pay_run.period_month,
                    'run_type': pay_run.run_type,
                    'status': pay_run.status,
                    'created_at': pay_run.created_at,
                    'calculated_at': pay_run.calculated_at,
                    'submitted_at': pay_run.submitted_at,
                    'finalized_at': pay_run.finalized_at,
                    'ready_count': ready_count,
                    'exception_count': exception_count,
                    'exception_messages': exception_messages,
                    'attendance_snapshot_summary': {
                        'attendance_source': (pay_run.attendance_snapshot or {}).get('attendance_source', ''),
                        'period_start': (pay_run.attendance_snapshot or {}).get('period_start'),
                        'period_end': (pay_run.attendance_snapshot or {}).get('period_end'),
                        'use_attendance_inputs': (pay_run.attendance_snapshot or {}).get('use_attendance_inputs', False),
                        'employee_count': (pay_run.attendance_snapshot or {}).get('employee_count', 0),
                        'ready_item_count': (pay_run.attendance_snapshot or {}).get('ready_item_count', 0),
                        'exception_item_count': (pay_run.attendance_snapshot or {}).get('exception_item_count', 0),
                        'total_attendance_paid_days': (pay_run.attendance_snapshot or {}).get('total_attendance_paid_days', '0.00'),
                        'total_lop_days': (pay_run.attendance_snapshot or {}).get('total_lop_days', '0.00'),
                        'total_overtime_minutes': (pay_run.attendance_snapshot or {}).get('total_overtime_minutes', 0),
                    },
                }
            )
        active_employee_count = Employee.objects.filter(organisation=organisation, status='ACTIVE').count()
        tax_slab_set_count = PayrollTaxSlabSet.objects.filter(organisation=organisation).count()
        compensation_template_count = CompensationTemplate.objects.filter(organisation=organisation).count()
        approved_assignment_count = CompensationAssignment.objects.filter(
            employee__organisation=organisation,
            status=CompensationAssignmentStatus.APPROVED,
        ).count()
        pending_assignment_count = CompensationAssignment.objects.filter(
            employee__organisation=organisation,
            status=CompensationAssignmentStatus.PENDING_APPROVAL,
        ).count()

        return Response(
            {
                'tax_slab_set_count': tax_slab_set_count,
                'compensation_template_count': compensation_template_count,
                'approved_assignment_count': approved_assignment_count,
                'pending_assignment_count': pending_assignment_count,
                'payslip_count': Payslip.objects.filter(organisation=organisation).count(),
                'diagnostics': _build_ct_payroll_diagnostics(
                    active_employee_count=active_employee_count,
                    tax_slab_set_count=tax_slab_set_count,
                    compensation_template_count=compensation_template_count,
                    approved_assignment_count=approved_assignment_count,
                    pending_assignment_count=pending_assignment_count,
                    payroll_runs=runs_payload,
                ),
                'payroll_runs': runs_payload,
            }
        )


class CtOrganisationAttendanceSupportView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        dashboard = get_org_attendance_dashboard(organisation)
        recent_imports = AttendanceImportJob.objects.filter(organisation=organisation).order_by('-created_at')[:5]
        policy_count = AttendancePolicy.objects.filter(organisation=organisation).count()
        source_count = AttendanceSourceConfig.objects.filter(organisation=organisation).count()
        active_source_count = AttendanceSourceConfig.objects.filter(organisation=organisation, is_active=True).count()
        pending_regularizations = AttendanceRegularizationRequest.objects.filter(
            organisation=organisation,
            status=AttendanceRegularizationStatus.PENDING,
        ).count()
        return Response(
            {
                'policy_count': policy_count,
                'source_count': source_count,
                'active_source_count': active_source_count,
                'pending_regularizations': pending_regularizations,
                'today_summary': {
                    'date': dashboard['date'],
                    'total_employees': dashboard['total_employees'],
                    'present_count': dashboard['present_count'],
                    'half_day_count': dashboard['half_day_count'],
                    'absent_count': dashboard['absent_count'],
                    'incomplete_count': dashboard['incomplete_count'],
                    'on_leave_count': dashboard['on_leave_count'],
                    'on_duty_count': dashboard['on_duty_count'],
                },
                'recent_imports': [
                    {
                        'id': str(job.id),
                        'mode': job.mode,
                        'status': job.status,
                        'original_filename': job.original_filename,
                        'valid_rows': job.valid_rows,
                        'error_rows': job.error_rows,
                        'posted_rows': job.posted_rows,
                        'created_at': job.created_at,
                    }
                    for job in recent_imports
                ],
                'diagnostics': _build_ct_attendance_diagnostics(
                    policy_count=policy_count,
                    active_source_count=active_source_count,
                    pending_regularizations=pending_regularizations,
                    incomplete_count=dashboard['incomplete_count'],
                    recent_imports=recent_imports,
                ),
            }
        )


class CtOrganisationOnboardingSupportView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        onboarding_status_counts = {
            status_value: Employee.objects.filter(organisation=organisation, onboarding_status=status_value).count()
            for status_value in EmployeeOnboardingStatus.values
        }
        document_request_status_counts = {
            status_value: EmployeeDocumentRequest.objects.filter(
                employee__organisation=organisation,
                status=status_value,
            ).count()
            for status_value in EmployeeDocumentRequestStatus.values
        }
        blocked_request_statuses = [
            EmployeeDocumentRequestStatus.REQUESTED,
            EmployeeDocumentRequestStatus.SUBMITTED,
            EmployeeDocumentRequestStatus.REJECTED,
        ]
        blocked_employees = (
            Employee.objects.filter(organisation=organisation)
            .select_related('user')
            .annotate(
                pending_document_requests=Count(
                    'document_requests',
                    filter=Q(document_requests__status__in=blocked_request_statuses),
                    distinct=True,
                ),
                latest_document_activity_at=Max('documents__created_at'),
            )
            .filter(
                Q(onboarding_status__in=[
                    EmployeeOnboardingStatus.NOT_STARTED,
                    EmployeeOnboardingStatus.BASIC_DETAILS_PENDING,
                    EmployeeOnboardingStatus.DOCUMENTS_PENDING,
                ])
                | Q(pending_document_requests__gt=0)
            )
            .order_by('-pending_document_requests', 'user__first_name', 'user__last_name')[:12]
        )
        top_blocker_types = (
            EmployeeDocumentRequest.objects.filter(
                employee__organisation=organisation,
                status__in=blocked_request_statuses,
            )
            .values(
                document_type_code=F('document_type_ref__code'),
                document_type_name=F('document_type_ref__name'),
            )
            .annotate(blocked_employee_count=Count('employee_id', distinct=True))
            .order_by('-blocked_employee_count', 'document_type_name')[:5]
        )
        return Response(
            {
                'onboarding_status_counts': onboarding_status_counts,
                'document_request_status_counts': document_request_status_counts,
                'blocked_employees': [
                    {
                        'id': str(employee.id),
                        'employee_code': employee.employee_code,
                        'full_name': employee.user.full_name,
                        'designation': employee.designation,
                        'status': employee.status,
                        'onboarding_status': employee.onboarding_status,
                        'pending_document_requests': employee.pending_document_requests,
                        'latest_document_activity_at': employee.latest_document_activity_at,
                    }
                    for employee in blocked_employees
                ],
                'top_blocker_types': list(top_blocker_types),
            }
        )


class CtOrganisationApprovalSupportView(APIView):
    permission_classes = [IsControlTowerUser]

    def get(self, request, pk):
        organisation = get_object_or_404(Organisation, id=pk)
        workflows = ApprovalWorkflow.objects.filter(organisation=organisation)
        approval_runs = ApprovalRun.objects.filter(organisation=organisation).prefetch_related('actions', 'workflow').order_by('-created_at')
        recent_runs = []
        for approval_run in approval_runs[:12]:
            pending_actions_count = approval_run.actions.filter(status=ApprovalActionStatus.PENDING).count()
            recent_runs.append(
                {
                    'id': str(approval_run.id),
                    'request_kind': approval_run.request_kind,
                    'status': approval_run.status,
                    'subject_label': approval_run.subject_label,
                    'requester_name': approval_run.requester_name,
                    'current_stage_sequence': approval_run.current_stage_sequence,
                    'workflow_name': approval_run.workflow.name,
                    'pending_actions_count': pending_actions_count,
                    'created_at': approval_run.created_at,
                    'modified_at': approval_run.modified_at,
                }
            )

        return Response(
            {
                'workflows_count': workflows.count(),
                'active_workflows_count': workflows.filter(is_active=True).count(),
                'default_workflows_count': workflows.filter(is_default=True).count(),
                'pending_runs_count': approval_runs.filter(status=ApprovalRunStatus.PENDING).count(),
                'approved_runs_count': approval_runs.filter(status=ApprovalRunStatus.APPROVED).count(),
                'rejected_runs_count': approval_runs.filter(status=ApprovalRunStatus.REJECTED).count(),
                'pending_actions_count': ApprovalAction.objects.filter(
                    approval_run__organisation=organisation,
                    status=ApprovalActionStatus.PENDING,
                ).count(),
                'recent_runs': recent_runs,
            }
        )


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


class CtOrganisationLocationListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = LocationCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            location = create_location(organisation, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)


class CtOrganisationLocationDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, location_id):
        organisation = _get_ct_organisation(pk)
        location = get_object_or_404(OfficeLocation, organisation=organisation, id=location_id)
        serializer = LocationCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            location = update_location(location, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LocationSerializer(location).data)


class CtOrganisationLocationDeactivateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, location_id):
        organisation = _get_ct_organisation(pk)
        location = get_object_or_404(OfficeLocation, organisation=organisation, id=location_id)
        try:
            location = deactivate_location(location, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LocationSerializer(location).data)


class CtOrganisationDepartmentListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = DepartmentCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            department = create_department(organisation, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)


class CtOrganisationDepartmentDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, department_id):
        organisation = _get_ct_organisation(pk)
        department = get_object_or_404(Department, organisation=organisation, id=department_id)
        serializer = DepartmentCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            department = update_department(department, actor=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data)


class CtOrganisationDepartmentDeactivateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, department_id):
        organisation = _get_ct_organisation(pk)
        department = get_object_or_404(Department, organisation=organisation, id=department_id)
        try:
            department = deactivate_department(department, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DepartmentSerializer(department).data)


class CtOrganisationLeaveCycleListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = LeaveCycleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = upsert_leave_cycle(organisation, actor=request.user, **serializer.validated_data)
        return Response(LeaveCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class CtOrganisationLeaveCycleDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, cycle_id):
        organisation = _get_ct_organisation(pk)
        cycle = get_object_or_404(LeaveCycle, organisation=organisation, id=cycle_id)
        serializer = LeaveCycleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = upsert_leave_cycle(organisation, actor=request.user, cycle=cycle, **serializer.validated_data)
        return Response(LeaveCycleSerializer(cycle).data)


class CtOrganisationLeavePlanListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = LeavePlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = get_object_or_404(LeaveCycle, organisation=organisation, id=serializer.validated_data['leave_cycle_id'])
        plan = create_leave_plan(
            organisation,
            actor=request.user,
            leave_cycle=cycle,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_default=serializer.validated_data.get('is_default', False),
            is_active=serializer.validated_data.get('is_active', True),
            priority=serializer.validated_data.get('priority', 100),
            leave_types=serializer.validated_data.get('leave_types', []),
            rules=_resolve_leave_plan_rules(organisation, serializer.validated_data.get('rules', [])),
        )
        return Response(LeavePlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class CtOrganisationLeavePlanDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, plan_id):
        organisation = _get_ct_organisation(pk)
        plan = get_object_or_404(LeavePlan, organisation=organisation, id=plan_id)
        serializer = LeavePlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = get_object_or_404(LeaveCycle, organisation=organisation, id=serializer.validated_data['leave_cycle_id'])
        plan = update_leave_plan(
            plan,
            actor=request.user,
            leave_cycle=cycle,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_default=serializer.validated_data.get('is_default', False),
            is_active=serializer.validated_data.get('is_active', True),
            priority=serializer.validated_data.get('priority', 100),
            leave_types=serializer.validated_data.get('leave_types', []),
            rules=_resolve_leave_plan_rules(organisation, serializer.validated_data.get('rules', [])),
        )
        return Response(LeavePlanSerializer(plan).data)


class CtOrganisationOnDutyPolicyListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = OnDutyPolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = upsert_on_duty_policy(organisation, actor=request.user, **serializer.validated_data)
        return Response(OnDutyPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class CtOrganisationOnDutyPolicyDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, policy_id):
        organisation = _get_ct_organisation(pk)
        policy = get_object_or_404(OnDutyPolicy, organisation=organisation, id=policy_id)
        serializer = OnDutyPolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = upsert_on_duty_policy(organisation, actor=request.user, policy=policy, **serializer.validated_data)
        return Response(OnDutyPolicySerializer(policy).data)


class CtOrganisationApprovalWorkflowListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = ApprovalWorkflowWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            workflow = upsert_approval_workflow(organisation, serializer.validated_data, request.user)
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist, Employee.DoesNotExist, LeaveType.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalWorkflowSerializer(workflow).data, status=status.HTTP_201_CREATED)


class CtOrganisationApprovalWorkflowDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, workflow_id):
        organisation = _get_ct_organisation(pk)
        workflow = get_object_or_404(ApprovalWorkflow, organisation=organisation, id=workflow_id)
        serializer = ApprovalWorkflowWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            workflow = upsert_approval_workflow(organisation, serializer.validated_data, request.user, workflow=workflow)
        except (ValueError, Department.DoesNotExist, OfficeLocation.DoesNotExist, Employee.DoesNotExist, LeaveType.DoesNotExist) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApprovalWorkflowSerializer(workflow).data)


class CtOrganisationNoticeListCreateView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        organisation = _get_ct_organisation(pk)
        serializer = NoticeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = create_notice(organisation, actor=request.user, **serializer.validated_data)
        return Response(NoticeSerializer(notice).data, status=status.HTTP_201_CREATED)


class CtOrganisationNoticeDetailView(APIView):
    permission_classes = [IsControlTowerUser]

    def patch(self, request, pk, notice_id):
        organisation = _get_ct_organisation(pk)
        notice = get_object_or_404(Notice, organisation=organisation, id=notice_id)
        serializer = NoticeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = update_notice(notice, actor=request.user, **serializer.validated_data)
        return Response(NoticeSerializer(notice).data)


class CtOrganisationNoticePublishView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, notice_id):
        organisation = _get_ct_organisation(pk)
        notice = get_object_or_404(Notice, organisation=organisation, id=notice_id)
        notice = publish_notice(notice, actor=request.user)
        return Response(NoticeSerializer(notice).data)


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


class OrgAdminSetupView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrgAdminSetupStateSerializer(get_org_admin_setup_state(organisation)).data)

    def patch(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'Select an administrator organisation workspace to continue.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = OrgAdminSetupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            organisation = update_org_admin_setup_state(
                organisation,
                actor=request.user,
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrgAdminSetupStateSerializer(get_org_admin_setup_state(organisation)).data)


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
