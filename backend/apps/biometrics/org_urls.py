from django.urls import path

from .views import BiometricDeviceDetailView, BiometricDeviceListCreateView, BiometricSyncLogListView

urlpatterns = [
    path('biometrics/devices/', BiometricDeviceListCreateView.as_view(), name='org-biometric-device-list'),
    path('biometrics/devices/<uuid:pk>/', BiometricDeviceDetailView.as_view(), name='org-biometric-device-detail'),
    path('biometrics/devices/<uuid:pk>/sync-logs/', BiometricSyncLogListView.as_view(), name='org-biometric-device-sync-logs'),
]

