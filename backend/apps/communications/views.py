from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import BelongsToActiveOrg, IsEmployee, IsOrgAdmin, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation, get_active_employee

from .models import Notice
from .serializers import NoticeSerializer, NoticeWriteSerializer
from .services import create_notice, get_employee_events, get_visible_notices, publish_notice, update_notice


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


class NoticeListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def get(self, request):
        organisation = _get_admin_organisation(request)
        notices = Notice.objects.filter(organisation=organisation).prefetch_related('departments', 'office_locations', 'employees')
        return Response(NoticeSerializer(notices, many=True).data)

    def post(self, request):
        organisation = _get_admin_organisation(request)
        serializer = NoticeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = create_notice(organisation, actor=request.user, **serializer.validated_data)
        return Response(NoticeSerializer(notice).data, status=status.HTTP_201_CREATED)


class NoticeDetailView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def patch(self, request, pk):
        organisation = _get_admin_organisation(request)
        notice = get_object_or_404(Notice, organisation=organisation, id=pk)
        serializer = NoticeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = update_notice(notice, actor=request.user, **serializer.validated_data)
        return Response(NoticeSerializer(notice).data)


class NoticePublishView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        notice = get_object_or_404(Notice, organisation=organisation, id=pk)
        notice = publish_notice(notice, actor=request.user)
        return Response(NoticeSerializer(notice).data)


class MyNoticeListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        notices = get_visible_notices(employee)
        return Response(NoticeSerializer(notices, many=True).data)


class MyEventListView(APIView):
    permission_classes = [IsEmployee, BelongsToActiveOrg]

    def get(self, request):
        employee = _get_employee(request)
        return Response(get_employee_events(employee))
