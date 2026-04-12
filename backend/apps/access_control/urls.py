from django.urls import path

from .views import OrgAccessControlAssignmentListCreateView, OrgAccessControlOverviewView

urlpatterns = [
    path('access-control/', OrgAccessControlOverviewView.as_view(), name='org-access-control-overview'),
    path('access-control/assignments/', OrgAccessControlAssignmentListCreateView.as_view(), name='org-access-control-assignments'),
]
