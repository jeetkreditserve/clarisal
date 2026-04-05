from django.urls import path

from .self_views import MyAppraisalReviewListView, MyAppraisalReviewSubmitView, MyGoalListView, MyGoalProgressUpdateView

urlpatterns = [
    path('performance/goals/', MyGoalListView.as_view(), name='my-performance-goal-list'),
    path('performance/goals/<uuid:pk>/progress/', MyGoalProgressUpdateView.as_view(), name='my-performance-goal-progress'),
    path('performance/reviews/', MyAppraisalReviewListView.as_view(), name='my-performance-review-list'),
    path('performance/reviews/<uuid:pk>/submit/', MyAppraisalReviewSubmitView.as_view(), name='my-performance-review-submit'),
]
