from django.urls import path

from .self_views import (
    MyAppraisalReviewListView,
    MyAppraisalReviewSubmitView,
    MyFeedbackSummaryView,
    MyGoalListView,
    MyGoalProgressUpdateView,
    MyReviewCycleListView,
    MySelfAssessmentSubmitView,
    MySelfAssessmentView,
)

urlpatterns = [
    path('performance/goals/', MyGoalListView.as_view(), name='my-performance-goal-list'),
    path('performance/goals/<uuid:pk>/progress/', MyGoalProgressUpdateView.as_view(), name='my-performance-goal-progress'),
    path('performance/review-cycles/', MyReviewCycleListView.as_view(), name='my-performance-review-cycle-list'),
    path('performance/review-cycles/<uuid:pk>/feedback-summary/', MyFeedbackSummaryView.as_view(), name='my-performance-feedback-summary'),
    path('performance/review-cycles/<uuid:pk>/self-assessment/', MySelfAssessmentView.as_view(), name='my-performance-self-assessment'),
    path('performance/review-cycles/<uuid:pk>/self-assessment/submit/', MySelfAssessmentSubmitView.as_view(), name='my-performance-self-assessment-submit'),
    path('performance/reviews/', MyAppraisalReviewListView.as_view(), name='my-performance-review-list'),
    path('performance/reviews/<uuid:pk>/submit/', MyAppraisalReviewSubmitView.as_view(), name='my-performance-review-submit'),
]
