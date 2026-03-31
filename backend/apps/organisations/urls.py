from django.urls import path

from .views import (
    CTDashboardStatsView,
    OrganisationActivateView,
    OrganisationAdminsView,
    OrganisationDetailView,
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
    path('organisations/<uuid:pk>/admins/', OrganisationAdminsView.as_view(), name='organisation-admins'),
]
