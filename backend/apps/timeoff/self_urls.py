from django.urls import path

from .views import (
    MyCalendarView,
    MyLeaveEncashmentListCreateView,
    MyLeaveOverviewView,
    MyLeaveRequestListCreateView,
    MyLeaveRequestWithdrawView,
    MyOnDutyPolicyListView,
    MyOnDutyRequestListCreateView,
    MyOnDutyRequestWithdrawView,
    MyTeamLeaveView,
)

urlpatterns = [
    path('leave/', MyLeaveOverviewView.as_view(), name='my-leave-overview'),
    path('my-team/leave/', MyTeamLeaveView.as_view(), name='my-team-leave'),
    path('leave/requests/', MyLeaveRequestListCreateView.as_view(), name='my-leave-request-list-create'),
    path('leave/requests/<uuid:pk>/withdraw/', MyLeaveRequestWithdrawView.as_view(), name='my-leave-request-withdraw'),
    path('leave-encashments/', MyLeaveEncashmentListCreateView.as_view(), name='my-leave-encashment-list-create'),
    path('on-duty/policies/', MyOnDutyPolicyListView.as_view(), name='my-on-duty-policy-list'),
    path('on-duty/requests/', MyOnDutyRequestListCreateView.as_view(), name='my-on-duty-request-list-create'),
    path('on-duty/requests/<uuid:pk>/withdraw/', MyOnDutyRequestWithdrawView.as_view(), name='my-on-duty-request-withdraw'),
    path('calendar/', MyCalendarView.as_view(), name='my-calendar'),
]
