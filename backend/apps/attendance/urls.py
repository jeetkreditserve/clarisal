from django.urls import path

from .views import (
    OrgAttendanceImportListView,
    OrgAttendanceNormalizedWorkbookView,
    OrgAttendancePunchImportView,
    OrgAttendancePunchSampleView,
    OrgAttendanceSheetImportView,
    OrgAttendanceSheetSampleView,
)

urlpatterns = [
    path('attendance/imports/', OrgAttendanceImportListView.as_view(), name='org-attendance-import-list'),
    path('attendance/imports/templates/attendance-sheet/', OrgAttendanceSheetSampleView.as_view(), name='org-attendance-template-attendance-sheet'),
    path('attendance/imports/templates/punch-sheet/', OrgAttendancePunchSampleView.as_view(), name='org-attendance-template-punch-sheet'),
    path('attendance/imports/attendance-sheet/', OrgAttendanceSheetImportView.as_view(), name='org-attendance-import-attendance-sheet'),
    path('attendance/imports/punch-sheet/', OrgAttendancePunchImportView.as_view(), name='org-attendance-import-punch-sheet'),
    path('attendance/imports/<uuid:pk>/normalized-file/', OrgAttendanceNormalizedWorkbookView.as_view(), name='org-attendance-import-normalized-file'),
]

