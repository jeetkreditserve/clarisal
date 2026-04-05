from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation

from .models import AppraisalCycle, GoalCycle
from .serializers import AppraisalCycleSerializer, GoalCycleSerializer
from .services import create_appraisal_cycle, create_goal_cycle


def _get_admin_organisation(request):
    organisation = get_active_admin_organisation(request, request.user)
    if organisation is None:
        raise ValueError('Select an administrator organisation workspace to continue.')
    return organisation


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
        cycle = create_appraisal_cycle(
            organisation=organisation,
            name=data['name'],
            review_type=data['review_type'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            actor=request.user,
        )
        return Response(AppraisalCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)
