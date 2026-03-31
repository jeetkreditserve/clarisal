from django.urls import path

from .views import InviteOrgAdminView, ResendOrgAdminInviteView

urlpatterns = [
    path('organisations/<uuid:pk>/admins/invite/', InviteOrgAdminView.as_view(), name='invite-org-admin'),
    path('organisations/<uuid:pk>/admins/<uuid:uid>/resend-invite/', ResendOrgAdminInviteView.as_view(), name='resend-org-admin-invite'),
]
