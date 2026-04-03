from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee
from apps.accounts.workspaces import get_active_employee

from .models import AppraisalReview, Goal
from .serializers import AppraisalReviewSerializer, GoalSerializer
from .services import submit_appraisal_review, update_goal_progress


class MyGoalListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = get_active_employee(request, request.user)
        if employee is None:
            return Response({'error': 'No active employee workspace'}, status=status.HTTP_400_BAD_REQUEST)
        goals = Goal.objects.filter(employee=employee).select_related('cycle').order_by('-created_at')
        return Response(GoalSerializer(goals, many=True).data)


class MyGoalProgressUpdateView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def patch(self, request, pk):
        employee = get_active_employee(request, request.user)
        if employee is None:
            return Response({'error': 'No active employee workspace'}, status=status.HTTP_400_BAD_REQUEST)
        goal = get_object_or_404(Goal, id=pk, employee=employee)
        progress = int(request.data.get('progress_percent', goal.progress_percent))
        goal = update_goal_progress(goal, progress_percent=progress, actor=request.user)
        return Response(GoalSerializer(goal).data)


class MyAppraisalReviewListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = get_active_employee(request, request.user)
        if employee is None:
            return Response({'error': 'No active employee workspace'}, status=status.HTTP_400_BAD_REQUEST)
        reviews = AppraisalReview.objects.filter(
            employee=employee,
        ).select_related('cycle', 'reviewer__user').order_by('-created_at')
        return Response(AppraisalReviewSerializer(reviews, many=True).data)


class MyAppraisalReviewSubmitView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def post(self, request, pk):
        employee = get_active_employee(request, request.user)
        if employee is None:
            return Response({'error': 'No active employee workspace'}, status=status.HTTP_400_BAD_REQUEST)
        review = get_object_or_404(AppraisalReview, id=pk, reviewer=employee)
        review = submit_appraisal_review(
            review,
            ratings=request.data.get('ratings', {}),
            comments=request.data.get('comments', ''),
            actor=request.user,
        )
        return Response(AppraisalReviewSerializer(review).data)
