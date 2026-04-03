from django.urls import path

from .org_views import OrgAppraisalCycleListCreateView, OrgGoalCycleListCreateView

urlpatterns = [
    path('performance/goal-cycles/', OrgGoalCycleListCreateView.as_view(), name='performance-goal-cycle-list-create'),
    path('performance/appraisal-cycles/', OrgAppraisalCycleListCreateView.as_view(), name='performance-appraisal-cycle-list-create'),
]
