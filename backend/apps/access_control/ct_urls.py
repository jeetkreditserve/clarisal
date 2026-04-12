from django.urls import path

from .views import CtAccessControlOverviewView, CtAccessRoleAssignmentListCreateView, CtAccessRoleListCreateView

urlpatterns = [
    path('access-control/', CtAccessControlOverviewView.as_view(), name='ct-access-control-overview'),
    path('access-control/roles/', CtAccessRoleListCreateView.as_view(), name='ct-access-control-roles'),
    path('access-control/assignments/', CtAccessRoleAssignmentListCreateView.as_view(), name='ct-access-control-assignments'),
]
