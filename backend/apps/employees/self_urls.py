from django.urls import path

from .views import (
    MyBankAccountDetailView,
    MyBankAccountListCreateView,
    MyDashboardView,
    MyEducationDetailView,
    MyEducationListCreateView,
    MyGovernmentIdListUpsertView,
    MyProfileView,
)

urlpatterns = [
    path('dashboard/', MyDashboardView.as_view(), name='my-dashboard'),
    path('profile/', MyProfileView.as_view(), name='my-profile'),
    path('education/', MyEducationListCreateView.as_view(), name='my-education-list-create'),
    path('education/<uuid:pk>/', MyEducationDetailView.as_view(), name='my-education-detail'),
    path('government-ids/', MyGovernmentIdListUpsertView.as_view(), name='my-government-ids'),
    path('bank-accounts/', MyBankAccountListCreateView.as_view(), name='my-bank-account-list-create'),
    path('bank-accounts/<uuid:pk>/', MyBankAccountDetailView.as_view(), name='my-bank-account-detail'),
]
