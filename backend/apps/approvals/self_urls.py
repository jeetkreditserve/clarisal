from django.urls import path

from .views import (
    MyApprovalActionApproveView,
    MyApprovalActionRejectView,
    MyApprovalInboxView,
)

urlpatterns = [
    path('approvals/inbox/', MyApprovalInboxView.as_view(), name='my-approval-inbox'),
    path('approvals/actions/<uuid:action_id>/approve/', MyApprovalActionApproveView.as_view(), name='my-approval-action-approve'),
    path('approvals/actions/<uuid:action_id>/reject/', MyApprovalActionRejectView.as_view(), name='my-approval-action-reject'),
]
