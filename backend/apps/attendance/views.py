from datetime import date, datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.common.security import hash_token
from apps.employees.models import Employee

from .models import (
    AttendanceDay,
    AttendanceImportJob,
    AttendanceImportMode,
    AttendancePolicy,
    AttendancePunchActionType,
    AttendancePunchSource,
    AttendanceRegularizationRequest,
    AttendanceSourceConfig,
    GeoFencePolicy,
    Shift,
)
from .serializers import (
    AttendanceDayOverrideSerializer,
    AttendanceDaySerializer,
    AttendanceImportJobSerializer,
    AttendancePolicySerializer,
    AttendancePolicyWriteSerializer,
    AttendancePunchWriteSerializer,
    AttendanceRegularizationSerializer,
    AttendanceRegularizationUpdateSerializer,
    AttendanceRegularizationWriteSerializer,
    AttendanceSourceConfigSerializer,
    AttendanceSourceConfigWriteSerializer,
    AttendanceSourceIngestSerializer,
    GeoFencePolicySerializer,
    GeoFencePolicyWriteSerializer,
    ShiftAssignmentSerializer,
    ShiftAssignmentWriteSerializer,
    ShiftSerializer,
    ShiftWriteSerializer,
)
from .services import (
    XLSX_CONTENT_TYPE,
    assign_shift,
    build_attendance_sheet_sample,
    build_normalized_attendance_workbook,
    build_punch_sheet_sample,
    create_regularization_request,
    create_shift,
    create_source_config,
    get_default_attendance_policy,
    get_employee_attendance_calendar,
    get_employee_attendance_history,
    get_employee_attendance_summary,
    get_org_attendance_dashboard,
    get_org_attendance_report,
    import_attendance_sheet,
    import_punch_sheet,
    ingest_source_punches,
    list_attendance_regularizations_for_org,
    list_org_attendance_days,
    record_employee_punch,
    update_shift,
    update_source_config,
    upsert_attendance_override,
    upsert_attendance_policy,
    withdraw_regularization_request,
)


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError("Select an administrator organisation workspace to continue.")
    return organisation


def _get_self_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError("Select an employee workspace to continue.")
    return employee


def _build_download_response(content, filename):
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _query_date(request, key="date"):
    raw = request.query_params.get(key)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be a valid YYYY-MM-DD date.") from exc


class OrgAttendanceDashboardView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        try:
            target_date = _query_date(request)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload = get_org_attendance_dashboard(organisation, target_date=target_date)
        payload["days"] = AttendanceDaySerializer(payload["days"], many=True).data
        return Response(payload)


class OrgAttendancePolicyListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        policies = AttendancePolicy.objects.filter(organisation=organisation).order_by("name")
        if not policies.exists():
            get_default_attendance_policy(organisation)
            policies = AttendancePolicy.objects.filter(organisation=organisation).order_by("name")
        return Response(AttendancePolicySerializer(policies, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = AttendancePolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = upsert_attendance_policy(organisation, actor=request.user, **serializer.validated_data)
        return Response(AttendancePolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class OrgAttendancePolicyDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        policy = get_object_or_404(AttendancePolicy, organisation=organisation, id=pk)
        serializer = AttendancePolicyWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        policy = upsert_attendance_policy(organisation, actor=request.user, policy=policy, **serializer.validated_data)
        return Response(AttendancePolicySerializer(policy).data)


class OrgAttendanceShiftListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        shifts = Shift.objects.filter(organisation=organisation).order_by("name")
        return Response(ShiftSerializer(shifts, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ShiftWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = create_shift(organisation, actor=request.user, **serializer.validated_data)
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class OrgAttendanceShiftDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        shift = get_object_or_404(Shift, organisation=organisation, id=pk)
        serializer = ShiftWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        shift = update_shift(shift, actor=request.user, **serializer.validated_data)
        return Response(ShiftSerializer(shift).data)


class OrgAttendanceShiftAssignmentListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        assignments = organisation.shift_assignments.select_related("employee__user", "shift").order_by(
            "-start_date", "employee__employee_code"
        )
        return Response(ShiftAssignmentSerializer(assignments, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = ShiftAssignmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = get_object_or_404(Employee, organisation=organisation, id=serializer.validated_data["employee_id"])
        shift = get_object_or_404(Shift, organisation=organisation, id=serializer.validated_data["shift_id"])
        assignment = assign_shift(
            employee,
            shift,
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data.get("end_date"),
            actor=request.user,
        )
        return Response(ShiftAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class OrgAttendanceDayListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        try:
            target_date = _query_date(request)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        status_value = request.query_params.get("status", "")
        employee_id = request.query_params.get("employee_id")
        days = list_org_attendance_days(
            organisation,
            target_date=target_date,
            employee_id=employee_id,
            status_value=status_value,
        )
        return Response(AttendanceDaySerializer(days, many=True).data)


class OrgAttendanceDayDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        attendance_day = get_object_or_404(
            AttendanceDay.objects.select_related("employee"), organisation=organisation, id=pk
        )
        serializer = AttendanceDayOverrideSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        check_in = serializer.validated_data.get("check_in")
        check_out = serializer.validated_data.get("check_out")
        check_in_at = (
            attendance_day.check_in_at
            if check_in is None
            else timezone.make_aware(
                datetime.combine(attendance_day.attendance_date, check_in), timezone.get_default_timezone()
            )
        )
        check_out_at = (
            attendance_day.check_out_at
            if check_out is None
            else timezone.make_aware(
                datetime.combine(attendance_day.attendance_date, check_out), timezone.get_default_timezone()
            )
        )
        try:
            attendance_day = upsert_attendance_override(
                attendance_day.employee,
                attendance_day.attendance_date,
                check_in_at=check_in_at,
                check_out_at=check_out_at,
                actor=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceDaySerializer(attendance_day).data)


class OrgAttendanceRegularizationListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = list_attendance_regularizations_for_org(
            organisation, status_value=request.query_params.get("status", "")
        )
        return Response(AttendanceRegularizationSerializer(queryset, many=True).data)


class OrgAttendanceSourceConfigListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = AttendanceSourceConfig.objects.filter(organisation=organisation).order_by("name")
        return Response(AttendanceSourceConfigSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = AttendanceSourceConfigWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source, raw_api_key = create_source_config(
            organisation,
            name=serializer.validated_data["name"],
            kind=serializer.validated_data["kind"],
            configuration=serializer.validated_data.get("configuration") or {},
            is_active=serializer.validated_data.get("is_active", True),
            actor=request.user,
        )
        payload = AttendanceSourceConfigSerializer(source).data
        if raw_api_key:
            payload["raw_api_key"] = raw_api_key
        return Response(payload, status=status.HTTP_201_CREATED)


class OrgAttendanceSourceConfigDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        source = get_object_or_404(AttendanceSourceConfig, organisation=organisation, id=pk)
        serializer = AttendanceSourceConfigWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        source, raw_api_key = update_source_config(
            source,
            name=serializer.validated_data.get("name"),
            is_active=serializer.validated_data.get("is_active"),
            configuration=serializer.validated_data.get("configuration"),
            rotate_api_key=serializer.validated_data.get("rotate_api_key", False),
            actor=request.user,
        )
        payload = AttendanceSourceConfigSerializer(source).data
        if raw_api_key:
            payload["raw_api_key"] = raw_api_key
        return Response(payload)


class OrgAttendanceReportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        try:
            payload = get_org_attendance_report(organisation, month=request.query_params.get("month"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload["rows"] = AttendanceDaySerializer(payload["rows"], many=True).data
        return Response(payload)


class OrgAttendanceImportListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        queryset = (
            AttendanceImportJob.objects.filter(organisation=organisation)
            .select_related("uploaded_by")
            .prefetch_related("rows")
        )
        return Response(AttendanceImportJobSerializer(queryset, many=True).data)


class OrgAttendanceSheetSampleView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        return _build_download_response(build_attendance_sheet_sample(), "attendance-sheet-sample.xlsx")


class OrgAttendancePunchSampleView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        return _build_download_response(build_punch_sheet_sample(), "attendance-punch-sample.xlsx")


class OrgAttendanceSheetImportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request):
        organisation = _get_admin_organisation(request)
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"error": "Upload an Excel .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            job = import_attendance_sheet(
                organisation=organisation, uploaded_by=request.user, uploaded_file=uploaded_file
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class OrgAttendancePunchImportView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request):
        organisation = _get_admin_organisation(request)
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"error": "Upload an Excel .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            job = import_punch_sheet(organisation=organisation, uploaded_by=request.user, uploaded_file=uploaded_file)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class OrgAttendanceNormalizedWorkbookView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        job = get_object_or_404(
            AttendanceImportJob.objects.prefetch_related("rows"),
            organisation=organisation,
            id=pk,
            mode=AttendanceImportMode.PUNCH_SHEET,
        )
        if job.valid_rows == 0:
            return Response(
                {"error": "This import job does not have any normalized attendance rows to download."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filename = f"normalized-attendance-{job.created_at.date().isoformat()}.xlsx"
        return _build_download_response(build_normalized_attendance_workbook(job), filename)


class AttendanceSourceIngestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, source_id):
        source = get_object_or_404(AttendanceSourceConfig.objects.select_related("organisation"), id=source_id)
        provided_key = request.headers.get("X-Attendance-Source-Key", "")
        stored_hash = (source.configuration or {}).get("api_key_hash", "")
        if not source.is_active or source.kind != "API" or not provided_key or stored_hash != hash_token(provided_key):
            return Response({"error": "Invalid attendance source credentials."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AttendanceSourceIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = ingest_source_punches(source, punches=serializer.validated_data["punches"])
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_202_ACCEPTED)


class MyAttendanceSummaryView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        payload = get_employee_attendance_summary(employee)
        return Response(
            {
                "today": AttendanceDaySerializer(payload["today"]).data,
                "policy": AttendancePolicySerializer(payload["policy"]).data,
                "shift": ShiftSerializer(payload["shift"]).data if payload["shift"] else None,
                "shift_source": payload.get("shift_source", "POLICY_DEFAULT"),
                "pending_regularizations": AttendanceRegularizationSerializer(
                    payload["pending_regularizations"], many=True
                ).data,
            }
        )


class MyAttendanceHistoryView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        month = request.query_params.get("month")
        days = get_employee_attendance_history(employee, month=month)
        return Response(AttendanceDaySerializer(days, many=True).data)


class MyAttendanceCalendarView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        month = request.query_params.get("month")
        return Response(get_employee_attendance_calendar(employee, month=month))


class MyAttendancePolicyView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        policy = get_default_attendance_policy(employee.organisation)
        return Response(AttendancePolicySerializer(policy).data)


class MyAttendancePunchInView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = AttendancePunchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            _punch, attendance_day = record_employee_punch(
                employee,
                action_type=AttendancePunchActionType.CHECK_IN,
                actor=request.user,
                remote_ip=request.META.get("REMOTE_ADDR", ""),
                latitude=serializer.validated_data.get("latitude"),
                longitude=serializer.validated_data.get("longitude"),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceDaySerializer(attendance_day).data, status=status.HTTP_201_CREATED)


class MyAttendancePunchOutView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = AttendancePunchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            _punch, attendance_day = record_employee_punch(
                employee,
                action_type=AttendancePunchActionType.CHECK_OUT,
                actor=request.user,
                remote_ip=request.META.get("REMOTE_ADDR", ""),
                latitude=serializer.validated_data.get("latitude"),
                longitude=serializer.validated_data.get("longitude"),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceDaySerializer(attendance_day).data, status=status.HTTP_201_CREATED)


class MyAttendanceRegularizationListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_self_employee(request)
        queryset = employee.attendance_regularization_requests.select_related("approval_run").order_by("-created_at")
        return Response(AttendanceRegularizationSerializer(queryset, many=True).data)

    def post(self, request):
        employee = _get_self_employee(request)
        serializer = AttendanceRegularizationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_check_in_at = (
            None
            if serializer.validated_data.get("requested_check_in") is None
            else timezone.make_aware(
                datetime.combine(
                    serializer.validated_data["attendance_date"], serializer.validated_data["requested_check_in"]
                ),
                timezone.get_default_timezone(),
            )
        )
        requested_check_out_at = (
            None
            if serializer.validated_data.get("requested_check_out") is None
            else timezone.make_aware(
                datetime.combine(
                    serializer.validated_data["attendance_date"], serializer.validated_data["requested_check_out"]
                ),
                timezone.get_default_timezone(),
            )
        )
        try:
            regularization = create_regularization_request(
                employee,
                attendance_date=serializer.validated_data["attendance_date"],
                requested_check_in_at=requested_check_in_at,
                requested_check_out_at=requested_check_out_at,
                reason=serializer.validated_data["reason"],
                actor=request.user,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceRegularizationSerializer(regularization).data, status=status.HTTP_201_CREATED)


class MyAttendanceRegularizationDetailView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = _get_self_employee(request)
        regularization = get_object_or_404(
            AttendanceRegularizationRequest, organisation=employee.organisation, employee=employee, id=pk
        )
        if regularization.status != "PENDING":
            return Response(
                {"error": "Only pending regularization requests can be edited."}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = AttendanceRegularizationUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if "requested_check_in" in serializer.validated_data:
            regularization.requested_check_in_at = (
                None
                if serializer.validated_data["requested_check_in"] is None
                else timezone.make_aware(
                    datetime.combine(regularization.attendance_date, serializer.validated_data["requested_check_in"]),
                    timezone.get_default_timezone(),
                )
            )
        if "requested_check_out" in serializer.validated_data:
            regularization.requested_check_out_at = (
                None
                if serializer.validated_data["requested_check_out"] is None
                else timezone.make_aware(
                    datetime.combine(regularization.attendance_date, serializer.validated_data["requested_check_out"]),
                    timezone.get_default_timezone(),
                )
            )
        if "reason" in serializer.validated_data:
            regularization.reason = serializer.validated_data["reason"]
        regularization.save(update_fields=["requested_check_in_at", "requested_check_out_at", "reason", "modified_at"])
        return Response(AttendanceRegularizationSerializer(regularization).data)


class MyAttendanceRegularizationWithdrawView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee = _get_self_employee(request)
        regularization = get_object_or_404(
            AttendanceRegularizationRequest, organisation=employee.organisation, employee=employee, id=pk
        )
        try:
            regularization = withdraw_regularization_request(regularization, actor=request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceRegularizationSerializer(regularization).data)


class MyMobilePunchView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request):
        from .services import validate_mobile_punch_location

        employee = _get_self_employee(request)
        serializer = AttendancePunchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        latitude = serializer.validated_data.get("latitude")
        longitude = serializer.validated_data.get("longitude")
        action_type_str = serializer.validated_data.get("action_type", "CHECK_IN")
        action_type = (
            AttendancePunchActionType.CHECK_IN if action_type_str == "CHECK_IN" else AttendancePunchActionType.CHECK_OUT
        )

        is_allowed, enforcement, message = validate_mobile_punch_location(
            organisation_id=str(employee.organisation_id),
            latitude=latitude,
            longitude=longitude,
            location_id=str(employee.office_location_id) if employee.office_location_id else None,
        )

        if not is_allowed and enforcement == "BLOCK":
            return Response(
                {"error": message or "Location outside geo-fence. Punch blocked."}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            punch, attendance_day = record_employee_punch(
                employee,
                action_type=action_type,
                actor=request.user,
                remote_ip=request.META.get("REMOTE_ADDR", ""),
                latitude=latitude,
                longitude=longitude,
                source=AttendancePunchSource.MOBILE,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_data = AttendanceDaySerializer(attendance_day).data
        if message:
            response_data["location_warning"] = message
        return Response(response_data, status=status.HTTP_201_CREATED)


class GeoFencePolicyListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            raise ValueError("Select an administrator organisation workspace to continue.")
        policies = GeoFencePolicy.objects.filter(organisation=organisation).order_by("name")
        return Response(GeoFencePolicySerializer(policies, many=True).data)

    def post(self, request):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            raise ValueError("Select an administrator organisation workspace to continue.")
        serializer = GeoFencePolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save(organisation=organisation)
        return Response(GeoFencePolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class GeoFencePolicyDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            raise ValueError("Select an administrator organisation workspace to continue.")
        policy = get_object_or_404(GeoFencePolicy, organisation=organisation, id=pk)
        serializer = GeoFencePolicyWriteSerializer(policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()
        return Response(GeoFencePolicySerializer(policy).data)

    def delete(self, request, pk):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            raise ValueError("Select an administrator organisation workspace to continue.")
        policy = get_object_or_404(GeoFencePolicy, organisation=organisation, id=pk)
        policy.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
