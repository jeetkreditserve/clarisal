from django.urls import path

from .views import (
    OrgAdminSetupView,
    OrgBillingInvoiceDownloadView,
    OrgBillingInvoiceListView,
    OrgBillingPaymentOrderView,
    OrgBillingPaymentStatusView,
    OrgBillingSummaryView,
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
    path('billing/', OrgBillingSummaryView.as_view(), name='org-billing-summary'),
    path('billing/payment-orders/', OrgBillingPaymentOrderView.as_view(), name='org-billing-payment-order'),
    path('billing/payment-orders/<uuid:payment_id>/status/', OrgBillingPaymentStatusView.as_view(), name='org-billing-payment-status'),
    path('billing/invoices/', OrgBillingInvoiceListView.as_view(), name='org-billing-invoice-list'),
    path('billing/invoices/<uuid:invoice_id>/download/', OrgBillingInvoiceDownloadView.as_view(), name='org-billing-invoice-download'),
    path('exports/', OrgDataExportListCreateView.as_view(), name='org-data-export-list-create'),
    path('exports/<uuid:export_id>/', OrgDataExportDetailView.as_view(), name='org-data-export-detail'),
    path('exports/<uuid:export_id>/download-url/', OrgDataExportDownloadUrlView.as_view(), name='org-data-export-download-url'),
    path('setup/', OrgAdminSetupView.as_view(), name='org-setup'),
    path('profile/', OrgProfileView.as_view(), name='org-profile'),
    path('profile/addresses/', OrgProfileAddressListCreateView.as_view(), name='org-profile-address-list-create'),
    path('profile/addresses/<uuid:address_id>/', OrgProfileAddressDetailView.as_view(), name='org-profile-address-detail'),
]
