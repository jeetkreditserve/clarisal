from django.urls import path

from .views import (
    HolidayCalendarDetailView,
    HolidayCalendarListCreateView,
    HolidayCalendarPublishView,
    LeaveCycleDetailView,
    LeaveCycleListCreateView,
    LeavePlanDetailView,
    LeavePlanListCreateView,
    OnDutyPolicyDetailView,
    OnDutyPolicyListCreateView,
    OrgLeaveEncashmentListView,
    OrgLeaveRequestListView,
    OrgOnDutyRequestListView,
)

urlpatterns = [
    path('holiday-calendars/', HolidayCalendarListCreateView.as_view(), name='holiday-calendar-list-create'),
    path('holiday-calendars/<uuid:pk>/', HolidayCalendarDetailView.as_view(), name='holiday-calendar-detail'),
    path('holiday-calendars/<uuid:pk>/publish/', HolidayCalendarPublishView.as_view(), name='holiday-calendar-publish'),
    path('leave-cycles/', LeaveCycleListCreateView.as_view(), name='leave-cycle-list-create'),
    path('leave-cycles/<uuid:pk>/', LeaveCycleDetailView.as_view(), name='leave-cycle-detail'),
    path('leave-plans/', LeavePlanListCreateView.as_view(), name='leave-plan-list-create'),
    path('leave-plans/<uuid:pk>/', LeavePlanDetailView.as_view(), name='leave-plan-detail'),
    path('on-duty-policies/', OnDutyPolicyListCreateView.as_view(), name='on-duty-policy-list-create'),
    path('on-duty-policies/<uuid:pk>/', OnDutyPolicyDetailView.as_view(), name='on-duty-policy-detail'),
    path('leave-requests/', OrgLeaveRequestListView.as_view(), name='org-leave-request-list'),
    path('leave-encashments/', OrgLeaveEncashmentListView.as_view(), name='org-leave-encashment-list'),
    path('on-duty-requests/', OrgOnDutyRequestListView.as_view(), name='org-on-duty-request-list'),
]
