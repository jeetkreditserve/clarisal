from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AccountType
from apps.accounts.permissions import BelongsToActiveOrg

from .models import Notification
from .serializers import NotificationSerializer
from .services import mark_all_read, mark_notification_read


class IsWorkforceUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.account_type == AccountType.WORKFORCE


class MyNotificationListView(APIView):
    permission_classes = [IsWorkforceUser, BelongsToActiveOrg]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        unread_count = queryset.filter(is_read=False).count()
        serializer = NotificationSerializer(queryset[:50], many=True)
        return Response({
            'unread_count': unread_count,
            'results': serializer.data,
        })


class MyNotificationMarkReadView(APIView):
    permission_classes = [IsWorkforceUser, BelongsToActiveOrg]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, id=pk, recipient=request.user)
        notification = mark_notification_read(notification, request.user)
        return Response(NotificationSerializer(notification).data)


class MyNotificationMarkAllReadView(APIView):
    permission_classes = [IsWorkforceUser, BelongsToActiveOrg]

    def post(self, request):
        count = mark_all_read(request.user)
        return Response({'marked_read': count})
