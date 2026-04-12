from django.urls import path

from .views import (
    OrgAccessControlAssignmentListCreateView,
    OrgAccessControlOverviewView,
    OrgAccessRoleListCreateView,
    OrgAccessSimulationView,
)

urlpatterns = [
    path('access-control/', OrgAccessControlOverviewView.as_view(), name='org-access-control-overview'),
    path('access-control/roles/', OrgAccessRoleListCreateView.as_view(), name='org-access-control-roles'),
    path('access-control/assignments/', OrgAccessControlAssignmentListCreateView.as_view(), name='org-access-control-assignments'),
    path('access-control/simulate/', OrgAccessSimulationView.as_view(), name='org-access-control-simulate'),
]
