from django.urls import path

from .views import (
    OrgAdminSetupView,
    OrgDashboardStatsView,
    OrgDataExportDetailView,
    OrgDataExportDownloadUrlView,
    OrgDataExportListCreateView,
    OrgProfileAddressDetailView,
    OrgProfileAddressListCreateView,
    OrgProfileView,
)

urlpatterns = [
    path('dashboard/', OrgDashboardStatsView.as_view(), name='org-dashboard'),
    path('exports/', OrgDataExportListCreateView.as_view(), name='org-data-export-list-create'),
    path('exports/<uuid:export_id>/', OrgDataExportDetailView.as_view(), name='org-data-export-detail'),
    path('exports/<uuid:export_id>/download-url/', OrgDataExportDownloadUrlView.as_view(), name='org-data-export-download-url'),
    path('setup/', OrgAdminSetupView.as_view(), name='org-setup'),
    path('profile/', OrgProfileView.as_view(), name='org-profile'),
    path('profile/addresses/', OrgProfileAddressListCreateView.as_view(), name='org-profile-address-list-create'),
    path('profile/addresses/<uuid:address_id>/', OrgProfileAddressDetailView.as_view(), name='org-profile-address-detail'),
]
