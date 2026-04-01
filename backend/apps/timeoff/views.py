from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee
from apps.departments.models import Department
from apps.employees.models import Employee
from apps.locations.models import OfficeLocation

from .models import HolidayCalendar, LeaveCycle, LeavePlan, LeaveRequest, LeaveType, OnDutyPolicy, OnDutyRequest
from .serializers import (
    HolidayCalendarSerializer,
    HolidayCalendarWriteSerializer,
    LeaveCycleSerializer,
    LeaveCycleWriteSerializer,
    LeavePlanSerializer,
    LeavePlanWriteSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
    OnDutyPolicySerializer,
    OnDutyPolicyWriteSerializer,
    OnDutyRequestCreateSerializer,
    OnDutyRequestSerializer,
)
from .services import (
    create_holiday_calendar,
    create_leave_plan,
    create_leave_request,
    create_on_duty_request,
    get_default_leave_cycle,
    get_employee_calendar_month,
    get_employee_leave_balances,
    publish_holiday_calendar,
    resolve_employee_leave_plan,
    update_holiday_calendar,
    update_leave_plan,
    upsert_leave_cycle,
    upsert_on_duty_policy,
    withdraw_leave_request,
    withdraw_on_duty_request,
)


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _get_employee(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        raise ValueError('Select an employee workspace to continue.')
    return employee


class HolidayCalendarListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        calendars = HolidayCalendar.objects.filter(organisation=organisation).prefetch_related('holidays', 'location_assignments')
        return Response(HolidayCalendarSerializer(calendars, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = HolidayCalendarWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            calendar_obj = create_holiday_calendar(
                organisation,
                actor=request.user,
                **serializer.validated_data,
            )
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(HolidayCalendarSerializer(calendar_obj).data, status=status.HTTP_201_CREATED)


class HolidayCalendarDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        calendar_obj = get_object_or_404(HolidayCalendar, organisation=organisation, id=pk)
        serializer = HolidayCalendarWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            calendar_obj = update_holiday_calendar(calendar_obj, actor=request.user, **serializer.validated_data)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(HolidayCalendarSerializer(calendar_obj).data)


class HolidayCalendarPublishView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        calendar_obj = get_object_or_404(HolidayCalendar, organisation=organisation, id=pk)
        calendar_obj = publish_holiday_calendar(calendar_obj, actor=request.user)
        return Response(HolidayCalendarSerializer(calendar_obj).data)


class LeaveCycleListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        cycles = LeaveCycle.objects.filter(organisation=organisation)
        return Response(LeaveCycleSerializer(cycles, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = LeaveCycleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = upsert_leave_cycle(organisation, actor=request.user, **serializer.validated_data)
        return Response(LeaveCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class LeaveCycleDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        cycle = get_object_or_404(LeaveCycle, organisation=organisation, id=pk)
        serializer = LeaveCycleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = upsert_leave_cycle(organisation, actor=request.user, cycle=cycle, **serializer.validated_data)
        return Response(LeaveCycleSerializer(cycle).data)


class LeavePlanListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        plans = LeavePlan.objects.filter(organisation=organisation).select_related('leave_cycle').prefetch_related('leave_types', 'rules')
        return Response(LeavePlanSerializer(plans, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = LeavePlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = get_object_or_404(LeaveCycle, organisation=organisation, id=serializer.validated_data['leave_cycle_id'])
        leave_types = serializer.validated_data.get('leave_types', [])
        rules = [
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
            for rule in serializer.validated_data.get('rules', [])
        ]
        plan = create_leave_plan(
            organisation,
            actor=request.user,
            leave_cycle=cycle,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            is_default=serializer.validated_data.get('is_default', False),
            is_active=serializer.validated_data.get('is_active', True),
            priority=serializer.validated_data.get('priority', 100),
            leave_types=leave_types,
            rules=rules,
        )
        return Response(LeavePlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class LeavePlanDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        plan = get_object_or_404(LeavePlan, organisation=organisation, id=pk)
        serializer = LeavePlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cycle = get_object_or_404(LeaveCycle, organisation=organisation, id=serializer.validated_data['leave_cycle_id'])
        rules = [
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
            for rule in serializer.validated_data.get('rules', [])
        ]
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
            rules=rules,
        )
        return Response(LeavePlanSerializer(plan).data)


class OnDutyPolicyListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        policies = OnDutyPolicy.objects.filter(organisation=organisation)
        return Response(OnDutyPolicySerializer(policies, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = OnDutyPolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = upsert_on_duty_policy(organisation, actor=request.user, **serializer.validated_data)
        return Response(OnDutyPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class OnDutyPolicyDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        policy = get_object_or_404(OnDutyPolicy, organisation=organisation, id=pk)
        serializer = OnDutyPolicyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = upsert_on_duty_policy(organisation, actor=request.user, policy=policy, **serializer.validated_data)
        return Response(OnDutyPolicySerializer(policy).data)


class OrgLeaveRequestListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        requests = LeaveRequest.objects.filter(employee__organisation=organisation).select_related('employee__user', 'leave_type')
        return Response(LeaveRequestSerializer(requests, many=True).data)


class OrgOnDutyRequestListView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        requests = OnDutyRequest.objects.filter(employee__organisation=organisation).select_related('employee__user', 'policy')
        return Response(OnDutyRequestSerializer(requests, many=True).data)


class MyLeaveOverviewView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        return Response(
            {
                'balances': get_employee_leave_balances(employee),
                'requests': LeaveRequestSerializer(
                    LeaveRequest.objects.filter(employee=employee).select_related('leave_type'),
                    many=True,
                ).data,
                'leave_plan': LeavePlanSerializer(resolve_employee_leave_plan(employee)).data
                if resolve_employee_leave_plan(employee)
                else None,
            }
        )


class MyLeaveRequestListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]
    throttle_scope = 'approval_action'

    def get(self, request):
        employee = _get_employee(request)
        requests = LeaveRequest.objects.filter(employee=employee).select_related('leave_type')
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        employee = _get_employee(request)
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_type = get_object_or_404(LeaveType, leave_plan__organisation=employee.organisation, id=serializer.validated_data['leave_type_id'])
        try:
            leave_request = create_leave_request(
                employee,
                leave_type,
                serializer.validated_data['start_date'],
                serializer.validated_data['end_date'],
                serializer.validated_data['start_session'],
                serializer.validated_data['end_session'],
                reason=serializer.validated_data.get('reason', ''),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED)


class MyLeaveRequestWithdrawView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee = _get_employee(request)
        leave_request = get_object_or_404(LeaveRequest, employee=employee, id=pk)
        try:
            leave_request = withdraw_leave_request(leave_request, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave_request).data)


class MyOnDutyPolicyListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        policies = OnDutyPolicy.objects.filter(organisation=employee.organisation, is_active=True)
        return Response(OnDutyPolicySerializer(policies, many=True).data)


class MyOnDutyRequestListCreateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]
    throttle_scope = 'approval_action'

    def get(self, request):
        employee = _get_employee(request)
        requests = OnDutyRequest.objects.filter(employee=employee).select_related('policy')
        return Response(OnDutyRequestSerializer(requests, many=True).data)

    def post(self, request):
        employee = _get_employee(request)
        serializer = OnDutyRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = OnDutyPolicy.objects.filter(organisation=employee.organisation, is_default=True, is_active=True).first()
        if serializer.validated_data.get('policy_id'):
            policy = get_object_or_404(OnDutyPolicy, organisation=employee.organisation, id=serializer.validated_data['policy_id'])
        if policy is None:
            return Response({'error': 'No active on-duty policy is configured for this organisation.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            on_duty_request = create_on_duty_request(
                employee,
                policy,
                serializer.validated_data['start_date'],
                serializer.validated_data['end_date'],
                serializer.validated_data['duration_type'],
                serializer.validated_data['purpose'],
                destination=serializer.validated_data.get('destination', ''),
                start_time=serializer.validated_data.get('start_time'),
                end_time=serializer.validated_data.get('end_time'),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OnDutyRequestSerializer(on_duty_request).data, status=status.HTTP_201_CREATED)


class MyOnDutyRequestWithdrawView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee = _get_employee(request)
        on_duty_request = get_object_or_404(OnDutyRequest, employee=employee, id=pk)
        try:
            on_duty_request = withdraw_on_duty_request(on_duty_request, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OnDutyRequestSerializer(on_duty_request).data)


class MyCalendarView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        return Response(get_employee_calendar_month(employee, calendar_month=request.query_params.get('month')))
