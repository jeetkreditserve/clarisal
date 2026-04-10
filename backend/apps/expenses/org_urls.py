from django.urls import path

from .views import OrgExpenseClaimDetailView, OrgExpenseClaimListView


urlpatterns = [
    path('expenses/claims/', OrgExpenseClaimListView.as_view(), name='org-expense-claim-list'),
    path('expenses/claims/<uuid:pk>/', OrgExpenseClaimDetailView.as_view(), name='org-expense-claim-detail'),
]
