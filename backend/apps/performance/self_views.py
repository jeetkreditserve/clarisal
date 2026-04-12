from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee
from apps.accounts.workspaces import get_active_employee

from .models import AppraisalCycle, AppraisalReview, Goal
from .serializers import AppraisalReviewSerializer, FeedbackSummarySerializer, GoalSerializer, MyReviewCycleSerializer
from .services import (
    aggregate_360_feedback,
    get_or_create_self_assessment,
    save_appraisal_review_draft,
    submit_appraisal_review,
    update_goal_progress,
)


def _get_active_employee_or_response(request):
    employee = get_active_employee(request, request.user)
    if employee is None:
        return None, Response({'error': 'No active employee workspace'}, status=status.HTTP_400_BAD_REQUEST)
    return employee, None


class MyGoalListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        goals = Goal.objects.filter(employee=employee).select_related('cycle').order_by('-created_at')
        return Response(GoalSerializer(goals, many=True).data)


class MyGoalProgressUpdateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        goal = get_object_or_404(Goal, id=pk, employee=employee)
        progress = int(request.data.get('progress_percent', goal.progress_percent))
        goal = update_goal_progress(goal, progress_percent=progress, actor=request.user)
        return Response(GoalSerializer(goal).data)


class MyReviewCycleListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        cycles = AppraisalCycle.objects.filter(
            organisation=employee.organisation,
            reviews__employee=employee,
        ).distinct().order_by('-start_date', '-created_at')
        serializer = MyReviewCycleSerializer(cycles, many=True, context={'employee': employee})
        return Response(serializer.data)


class MyFeedbackSummaryView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        cycle = get_object_or_404(AppraisalCycle, id=pk, organisation=employee.organisation)
        if cycle.status not in {'MANAGER_REVIEW', 'CALIBRATION', 'COMPLETED'}:
            return Response(
                {'error': 'Feedback summaries are available after manager review starts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        summary = aggregate_360_feedback(cycle, employee)
        return Response(FeedbackSummarySerializer(summary).data)


class MySelfAssessmentView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request, pk):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        cycle = get_object_or_404(AppraisalCycle, id=pk, organisation=employee.organisation)
        review = get_or_create_self_assessment(cycle, employee=employee, actor=request.user)
        return Response(AppraisalReviewSerializer(review).data)

    def put(self, request, pk):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        cycle = get_object_or_404(AppraisalCycle, id=pk, organisation=employee.organisation)
        review = get_or_create_self_assessment(cycle, employee=employee, actor=request.user)
        try:
            review = save_appraisal_review_draft(
                review,
                ratings=request.data.get('ratings', {}),
                comments=request.data.get('comments', ''),
                actor=request.user,
            )
        except ValueError:
            return Response(
                {'error': 'Submitted self-assessments cannot be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AppraisalReviewSerializer(review).data)


class MySelfAssessmentSubmitView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        cycle = get_object_or_404(AppraisalCycle, id=pk, organisation=employee.organisation)
        review = get_or_create_self_assessment(cycle, employee=employee, actor=request.user)
        try:
            review = submit_appraisal_review(
                review,
                ratings=request.data.get('ratings', review.ratings),
                comments=request.data.get('comments', review.comments),
                actor=request.user,
            )
        except ValueError:
            return Response(
                {'error': 'Submitted self-assessments cannot be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AppraisalReviewSerializer(review).data)


class MyAppraisalReviewListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        reviews = AppraisalReview.objects.filter(
            employee=employee,
        ).select_related('cycle', 'reviewer__user').order_by('-created_at')
        return Response(AppraisalReviewSerializer(reviews, many=True).data)


class MyAppraisalReviewSubmitView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee, error_response = _get_active_employee_or_response(request)
        if error_response is not None:
            return error_response
        review = get_object_or_404(AppraisalReview, id=pk, reviewer=employee)
        try:
            review = submit_appraisal_review(
                review,
                ratings=request.data.get('ratings', {}),
                comments=request.data.get('comments', ''),
                actor=request.user,
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppraisalReviewSerializer(review).data)
