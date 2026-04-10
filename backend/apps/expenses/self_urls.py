from django.urls import path

from .views import MyExpenseClaimDetailView, MyExpenseClaimListCreateView, MyExpenseClaimStatusView, MyExpenseClaimSubmitView


urlpatterns = [
    path('expenses/claims/', MyExpenseClaimListCreateView.as_view(), name='my-expense-claim-list'),
    path('expenses/claims/<uuid:pk>/', MyExpenseClaimDetailView.as_view(), name='my-expense-claim-detail'),
    path('expenses/claims/<uuid:pk>/submit/', MyExpenseClaimSubmitView.as_view(), name='my-expense-claim-submit'),
    path('expenses/claims/<uuid:pk>/status/', MyExpenseClaimStatusView.as_view(), name='my-expense-claim-status'),
]
