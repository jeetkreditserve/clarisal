from django.urls import path

from .views import (
    OrgExpenseClaimDetailView,
    OrgExpenseClaimListView,
    OrgExpenseClaimSummaryView,
    OrgExpensePolicyDetailView,
    OrgExpensePolicyListCreateView,
)

urlpatterns = [
    path('expenses/policies/', OrgExpensePolicyListCreateView.as_view(), name='org-expense-policy-list'),
    path('expenses/policies/<uuid:pk>/', OrgExpensePolicyDetailView.as_view(), name='org-expense-policy-detail'),
    path('expenses/claims/summary/', OrgExpenseClaimSummaryView.as_view(), name='org-expense-claim-summary'),
    path('expenses/claims/', OrgExpenseClaimListView.as_view(), name='org-expense-claim-list'),
    path('expenses/claims/<uuid:pk>/', OrgExpenseClaimDetailView.as_view(), name='org-expense-claim-detail'),
]
