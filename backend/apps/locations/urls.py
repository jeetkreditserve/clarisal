from django.urls import path

from .views import LocationDeactivateView, LocationDetailView, LocationListCreateView

urlpatterns = [
    path('locations/', LocationListCreateView.as_view(), name='location-list-create'),
    path('locations/<uuid:pk>/', LocationDetailView.as_view(), name='location-detail'),
    path('locations/<uuid:pk>/deactivate/', LocationDeactivateView.as_view(), name='location-deactivate'),
]
