from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, MeView
from apps.invitations.views import ValidateInviteTokenView, AcceptInviteView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('invite/validate/<str:token>/', ValidateInviteTokenView.as_view(), name='invite-validate'),
    path('invite/accept/', AcceptInviteView.as_view(), name='invite-accept'),
]
