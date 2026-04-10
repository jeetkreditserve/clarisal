from django.urls import path

from .views import (
    MyAttendanceCalendarView,
    MyAttendanceHistoryView,
    MyAttendancePolicyView,
    MyAttendancePunchInView,
    MyAttendancePunchOutView,
    MyAttendanceRegularizationDetailView,
    MyAttendanceRegularizationListView,
    MyAttendanceRegularizationWithdrawView,
    MyAttendanceSummaryView,
    MyMobilePunchView,
)

urlpatterns = [
    path("attendance/summary/", MyAttendanceSummaryView.as_view(), name="my-attendance-summary"),
    path("attendance/history/", MyAttendanceHistoryView.as_view(), name="my-attendance-history"),
    path("attendance/calendar/", MyAttendanceCalendarView.as_view(), name="my-attendance-calendar"),
    path("attendance/policy/", MyAttendancePolicyView.as_view(), name="my-attendance-policy"),
    path("attendance/punch-in/", MyAttendancePunchInView.as_view(), name="my-attendance-punch-in"),
    path("attendance/punch-out/", MyAttendancePunchOutView.as_view(), name="my-attendance-punch-out"),
    path("attendance/mobile-punch/", MyMobilePunchView.as_view(), name="my-attendance-mobile-punch"),
    path(
        "attendance/regularizations/",
        MyAttendanceRegularizationListView.as_view(),
        name="my-attendance-regularization-list",
    ),
    path(
        "attendance/regularizations/<uuid:pk>/",
        MyAttendanceRegularizationDetailView.as_view(),
        name="my-attendance-regularization-detail",
    ),
    path(
        "attendance/regularizations/<uuid:pk>/withdraw/",
        MyAttendanceRegularizationWithdrawView.as_view(),
        name="my-attendance-regularization-withdraw",
    ),
]
