from django.urls import path

from .views import (
    OrgApprovalActionApproveView,
    OrgApprovalActionRejectView,
    OrgApprovalDelegationDetailView,
    OrgApprovalDelegationListCreateView,
    OrgApprovalInboxView,
    OrgApprovalWorkflowCatalogView,
    OrgApprovalWorkflowDetailView,
    OrgApprovalWorkflowListCreateView,
    OrgApprovalWorkflowPresetView,
    OrgApprovalWorkflowReadinessView,
    OrgApprovalWorkflowSimulationView,
)

urlpatterns = [
    path('approvals/workflows/', OrgApprovalWorkflowListCreateView.as_view(), name='approval-workflow-list-create'),
    path('approvals/workflows/catalog/', OrgApprovalWorkflowCatalogView.as_view(), name='approval-workflow-catalog'),
    path('approvals/workflows/readiness/', OrgApprovalWorkflowReadinessView.as_view(), name='approval-workflow-readiness'),
    path('approvals/workflows/simulate/', OrgApprovalWorkflowSimulationView.as_view(), name='approval-workflow-simulate'),
    path('approvals/workflows/presets/<str:request_kind>/', OrgApprovalWorkflowPresetView.as_view(), name='approval-workflow-presets'),
    path('approvals/workflows/<uuid:pk>/', OrgApprovalWorkflowDetailView.as_view(), name='approval-workflow-detail'),
    path('approvals/delegations/', OrgApprovalDelegationListCreateView.as_view(), name='approval-delegation-list-create'),
    path('approvals/delegations/<uuid:pk>/', OrgApprovalDelegationDetailView.as_view(), name='approval-delegation-detail'),
    path('approvals/inbox/', OrgApprovalInboxView.as_view(), name='approval-inbox'),
    path('approvals/actions/<uuid:action_id>/approve/', OrgApprovalActionApproveView.as_view(), name='approval-action-approve'),
    path('approvals/actions/<uuid:action_id>/reject/', OrgApprovalActionRejectView.as_view(), name='approval-action-reject'),
]
