from django.urls import path

from .views import (
    OrgDashboardStatsView,
    OrgProfileAddressDetailView,
    OrgProfileAddressListCreateView,
    OrgProfileView,
)

urlpatterns = [
    path('dashboard/', OrgDashboardStatsView.as_view(), name='org-dashboard'),
    path('profile/', OrgProfileView.as_view(), name='org-profile'),
    path('profile/addresses/', OrgProfileAddressListCreateView.as_view(), name='org-profile-address-list-create'),
    path('profile/addresses/<uuid:address_id>/', OrgProfileAddressDetailView.as_view(), name='org-profile-address-detail'),
]
