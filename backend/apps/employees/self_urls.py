from django.urls import path

from .views import (
    MyBankAccountDetailView,
    MyBankAccountListCreateView,
    MyDashboardView,
    MyEducationDetailView,
    MyEducationListCreateView,
    MyEmergencyContactDetailView,
    MyEmergencyContactListCreateView,
    MyFamilyMemberDetailView,
    MyFamilyMemberListCreateView,
    MyGovernmentIdListUpsertView,
    MyOnboardingView,
    MyProfileView,
)

urlpatterns = [
    path('onboarding/', MyOnboardingView.as_view(), name='my-onboarding'),
    path('dashboard/', MyDashboardView.as_view(), name='my-dashboard'),
    path('profile/', MyProfileView.as_view(), name='my-profile'),
    path('family-members/', MyFamilyMemberListCreateView.as_view(), name='my-family-members'),
    path('family-members/<uuid:pk>/', MyFamilyMemberDetailView.as_view(), name='my-family-member-detail'),
    path('emergency-contacts/', MyEmergencyContactListCreateView.as_view(), name='my-emergency-contacts'),
    path('emergency-contacts/<uuid:pk>/', MyEmergencyContactDetailView.as_view(), name='my-emergency-contact-detail'),
    path('education/', MyEducationListCreateView.as_view(), name='my-education-list-create'),
    path('education/<uuid:pk>/', MyEducationDetailView.as_view(), name='my-education-detail'),
    path('government-ids/', MyGovernmentIdListUpsertView.as_view(), name='my-government-ids'),
    path('bank-accounts/', MyBankAccountListCreateView.as_view(), name='my-bank-account-list-create'),
    path('bank-accounts/<uuid:pk>/', MyBankAccountDetailView.as_view(), name='my-bank-account-detail'),
]
