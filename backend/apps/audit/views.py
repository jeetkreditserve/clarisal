from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AccountType
from apps.accounts.permissions import BelongsToActiveOrg
from apps.accounts.workspaces import get_current_organisation

from .repositories import apply_audit_filters, get_audit_logs, get_audit_logs_for_organisation
from .serializers import AuditLogSerializer


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated, BelongsToActiveOrg]

    def get(self, request):
        if request.user.account_type == AccountType.CONTROL_TOWER:
            queryset = get_audit_logs()
            organisation_id = request.query_params.get('organisation_id')
            if organisation_id:
                queryset = queryset.filter(organisation_id=organisation_id)
        else:
            organisation = get_current_organisation(request, request.user)
            queryset = get_audit_logs_for_organisation(organisation)

        queryset = apply_audit_filters(queryset, request.query_params)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
