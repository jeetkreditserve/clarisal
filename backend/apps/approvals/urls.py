from django.urls import path

from .views import (
    OrgApprovalActionApproveView,
    OrgApprovalActionRejectView,
    OrgApprovalDelegationDetailView,
    OrgApprovalDelegationListCreateView,
    OrgApprovalInboxView,
    OrgApprovalWorkflowDetailView,
    OrgApprovalWorkflowListCreateView,
)

urlpatterns = [
    path('approvals/workflows/', OrgApprovalWorkflowListCreateView.as_view(), name='approval-workflow-list-create'),
    path('approvals/workflows/<uuid:pk>/', OrgApprovalWorkflowDetailView.as_view(), name='approval-workflow-detail'),
    path('approvals/delegations/', OrgApprovalDelegationListCreateView.as_view(), name='approval-delegation-list-create'),
    path('approvals/delegations/<uuid:pk>/', OrgApprovalDelegationDetailView.as_view(), name='approval-delegation-detail'),
    path('approvals/inbox/', OrgApprovalInboxView.as_view(), name='approval-inbox'),
    path('approvals/actions/<uuid:action_id>/approve/', OrgApprovalActionApproveView.as_view(), name='approval-action-approve'),
    path('approvals/actions/<uuid:action_id>/reject/', OrgApprovalActionRejectView.as_view(), name='approval-action-reject'),
]
