from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.CTDashboardStatsView.as_view(), name='ct-dashboard'),
    path('organisations/', views.OrganisationListCreateView.as_view(), name='org-list-create'),
    path('organisations/<uuid:pk>/', views.OrganisationDetailView.as_view(), name='org-detail'),
    path('organisations/<uuid:pk>/activate/', views.OrganisationActivateView.as_view(), name='org-activate'),
    path('organisations/<uuid:pk>/suspend/', views.OrganisationSuspendView.as_view(), name='org-suspend'),
    path('organisations/<uuid:pk>/licences/', views.OrganisationLicencesView.as_view(), name='org-licences'),
    path('organisations/<uuid:pk>/admins/', views.OrganisationAdminsView.as_view(), name='org-admins'),
]
