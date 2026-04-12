from django.urls import path

from .org_views import (
    OrgAppraisalCycleActivateView,
    OrgAppraisalCycleAdvanceView,
    OrgAppraisalCycleListCreateView,
    OrgCalibrationEntryAdjustView,
    OrgCalibrationSessionCreateView,
    OrgCalibrationSessionLockView,
    OrgFeedbackSummaryView,
    OrgGoalCycleListCreateView,
)

urlpatterns = [
    path('performance/goal-cycles/', OrgGoalCycleListCreateView.as_view(), name='performance-goal-cycle-list-create'),
    path('performance/appraisal-cycles/', OrgAppraisalCycleListCreateView.as_view(), name='performance-appraisal-cycle-list-create'),
    path('performance/appraisal-cycles/<uuid:pk>/activate/', OrgAppraisalCycleActivateView.as_view(), name='performance-appraisal-cycle-activate'),
    path('performance/appraisal-cycles/<uuid:pk>/advance/', OrgAppraisalCycleAdvanceView.as_view(), name='performance-appraisal-cycle-advance'),
    path('performance/appraisal-cycles/<uuid:pk>/employees/<uuid:employee_id>/feedback-summary/', OrgFeedbackSummaryView.as_view(), name='performance-feedback-summary'),
    path('performance/appraisal-cycles/<uuid:pk>/calibration-sessions/', OrgCalibrationSessionCreateView.as_view(), name='performance-calibration-session-create'),
    path('performance/calibration-sessions/<uuid:session_id>/employees/<uuid:employee_id>/rating/', OrgCalibrationEntryAdjustView.as_view(), name='performance-calibration-entry-adjust'),
    path('performance/calibration-sessions/<uuid:session_id>/lock/', OrgCalibrationSessionLockView.as_view(), name='performance-calibration-session-lock'),
]
