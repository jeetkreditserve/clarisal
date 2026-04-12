from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from apps.employees.models import Employee

from .models import AppraisalCycle, CalibrationSession, GoalCycle
from .serializers import (
    AppraisalCycleSerializer,
    CalibrationSessionEntrySerializer,
    CalibrationSessionSerializer,
    FeedbackSummarySerializer,
    GoalCycleSerializer,
)
from .services import (
    activate_appraisal_cycle,
    adjust_calibration_rating,
    advance_appraisal_cycle_phase,
    aggregate_360_feedback,
    create_appraisal_cycle,
    create_calibration_session,
    create_goal_cycle,
    lock_calibration_session,
)


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


def _get_org_cycle(request, pk):
    organisation = _get_admin_organisation(request)
    cycle = get_object_or_404(AppraisalCycle, id=pk, organisation=organisation)
    return organisation, cycle


class OrgGoalCycleListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        cycles = GoalCycle.objects.filter(organisation=organisation).order_by('-created_at')
        return Response(GoalCycleSerializer(cycles, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = GoalCycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cycle = create_goal_cycle(
            organisation=organisation,
            name=data['name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            auto_create_review_cycle=data.get('auto_create_review_cycle', False),
            actor=request.user,
        )
        return Response(GoalCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class OrgAppraisalCycleListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        cycles = AppraisalCycle.objects.filter(organisation=organisation).order_by('-created_at')
        return Response(AppraisalCycleSerializer(cycles, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = AppraisalCycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        goal_cycle = None
        if data.get('goal_cycle_id'):
            goal_cycle = GoalCycle.objects.filter(id=data['goal_cycle_id'], organisation=organisation).first()
        cycle = create_appraisal_cycle(
            organisation=organisation,
            name=data['name'],
            review_type=data['review_type'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            goal_cycle=goal_cycle,
            self_assessment_deadline=data.get('self_assessment_deadline'),
            peer_review_deadline=data.get('peer_review_deadline'),
            manager_review_deadline=data.get('manager_review_deadline'),
            calibration_deadline=data.get('calibration_deadline'),
            actor=request.user,
        )
        return Response(AppraisalCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class OrgAppraisalCycleActivateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        _, cycle = _get_org_cycle(request, pk)
        try:
            cycle = activate_appraisal_cycle(cycle, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppraisalCycleSerializer(cycle).data)


class OrgAppraisalCycleAdvanceView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        _, cycle = _get_org_cycle(request, pk)
        try:
            cycle = advance_appraisal_cycle_phase(cycle, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppraisalCycleSerializer(cycle).data)


class OrgFeedbackSummaryView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk, employee_id):
        organisation, cycle = _get_org_cycle(request, pk)
        if cycle.status not in {'MANAGER_REVIEW', 'CALIBRATION', 'COMPLETED'}:
            return Response(
                {'error': 'Feedback summaries are available after manager review starts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        employee = get_object_or_404(Employee, id=employee_id, organisation=organisation)
        summary = aggregate_360_feedback(cycle, employee)
        return Response(FeedbackSummarySerializer(summary).data)


class OrgCalibrationSessionCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        _, cycle = _get_org_cycle(request, pk)
        try:
            session = create_calibration_session(cycle, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CalibrationSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class OrgCalibrationEntryAdjustView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, session_id, employee_id):
        organisation = _get_admin_organisation(request)
        session = get_object_or_404(CalibrationSession, id=session_id, cycle__organisation=organisation)
        employee = get_object_or_404(Employee, id=employee_id, organisation=organisation)
        try:
            entry = adjust_calibration_rating(
                session,
                employee,
                new_rating=request.data.get('rating'),
                reason=request.data.get('reason', ''),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CalibrationSessionEntrySerializer(entry).data)


class OrgCalibrationSessionLockView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, session_id):
        organisation = _get_admin_organisation(request)
        session = get_object_or_404(CalibrationSession, id=session_id, cycle__organisation=organisation)
        try:
            session = lock_calibration_session(session, actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CalibrationSessionSerializer(session).data)
