from django.urls import path

from .views import (
    CTDashboardStatsView,
    OrganisationActivateView,
    OrganisationAdminsView,
    OrganisationAddressDetailView,
    OrganisationAddressListCreateView,
    OrganisationDetailView,
    OrganisationLicenceBatchDetailView,
    OrganisationLicenceBatchListCreateView,
    OrganisationLicenceBatchMarkPaidView,
    OrganisationLicencesView,
    OrganisationListCreateView,
    OrganisationRestoreView,
    OrganisationSuspendView,
)

urlpatterns = [
    path('dashboard/', CTDashboardStatsView.as_view(), name='ct-dashboard'),
    path('organisations/', OrganisationListCreateView.as_view(), name='organisation-list-create'),
    path('organisations/<uuid:pk>/', OrganisationDetailView.as_view(), name='organisation-detail'),
    path('organisations/<uuid:pk>/activate/', OrganisationActivateView.as_view(), name='organisation-activate'),
    path('organisations/<uuid:pk>/restore/', OrganisationRestoreView.as_view(), name='organisation-restore'),
    path('organisations/<uuid:pk>/suspend/', OrganisationSuspendView.as_view(), name='organisation-suspend'),
    path('organisations/<uuid:pk>/licences/', OrganisationLicencesView.as_view(), name='organisation-licences'),
    path('organisations/<uuid:pk>/licence-batches/', OrganisationLicenceBatchListCreateView.as_view(), name='organisation-licence-batch-list-create'),
    path('organisations/<uuid:pk>/licence-batches/<uuid:batch_id>/', OrganisationLicenceBatchDetailView.as_view(), name='organisation-licence-batch-detail'),
    path('organisations/<uuid:pk>/licence-batches/<uuid:batch_id>/mark-paid/', OrganisationLicenceBatchMarkPaidView.as_view(), name='organisation-licence-batch-mark-paid'),
    path('organisations/<uuid:pk>/admins/', OrganisationAdminsView.as_view(), name='organisation-admins'),
    path('organisations/<uuid:pk>/addresses/', OrganisationAddressListCreateView.as_view(), name='organisation-address-list-create'),
    path('organisations/<uuid:pk>/addresses/<uuid:address_id>/', OrganisationAddressDetailView.as_view(), name='organisation-address-detail'),
]
