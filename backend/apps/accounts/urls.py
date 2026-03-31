from django.urls import path
from .views import (
    CsrfTokenView,
    WorkforceLoginView,
    ControlTowerLoginView,
    LogoutView,
    MeView,
    PasswordResetRequestView,
    ControlTowerPasswordResetRequestView,
    PasswordResetValidateView,
    PasswordResetConfirmView,
    WorkspaceSelectionView,
)
from apps.invitations.views import ValidateInviteTokenView, AcceptInviteView

urlpatterns = [
    path('csrf/', CsrfTokenView.as_view(), name='auth-csrf'),
    path('login/', WorkforceLoginView.as_view(), name='auth-login'),
    path('control-tower/login/', ControlTowerLoginView.as_view(), name='control-tower-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('workspace/', WorkspaceSelectionView.as_view(), name='auth-workspace'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('control-tower/password-reset/request/', ControlTowerPasswordResetRequestView.as_view(), name='control-tower-password-reset-request'),
    path('password-reset/validate/<str:token>/', PasswordResetValidateView.as_view(), name='password-reset-validate'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('invite/validate/<str:token>/', ValidateInviteTokenView.as_view(), name='invite-validate'),
    path('invite/accept/', AcceptInviteView.as_view(), name='invite-accept'),
]
