from django.urls import path

from .views import (
    MyCalendarView,
    MyLeaveOverviewView,
    MyLeaveRequestListCreateView,
    MyLeaveRequestWithdrawView,
    MyOnDutyPolicyListView,
    MyOnDutyRequestListCreateView,
    MyOnDutyRequestWithdrawView,
)

urlpatterns = [
    path('leave/', MyLeaveOverviewView.as_view(), name='my-leave-overview'),
    path('leave/requests/', MyLeaveRequestListCreateView.as_view(), name='my-leave-request-list-create'),
    path('leave/requests/<uuid:pk>/withdraw/', MyLeaveRequestWithdrawView.as_view(), name='my-leave-request-withdraw'),
    path('on-duty/policies/', MyOnDutyPolicyListView.as_view(), name='my-on-duty-policy-list'),
    path('on-duty/requests/', MyOnDutyRequestListCreateView.as_view(), name='my-on-duty-request-list-create'),
    path('on-duty/requests/<uuid:pk>/withdraw/', MyOnDutyRequestWithdrawView.as_view(), name='my-on-duty-request-withdraw'),
    path('calendar/', MyCalendarView.as_view(), name='my-calendar'),
]
