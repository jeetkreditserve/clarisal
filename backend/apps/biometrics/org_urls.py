from django.urls import path

from .event_stream import AttendanceEventStreamView, DeviceEventStreamView
from .views import (
    BiometricDeviceDetailView,
    BiometricDeviceListCreateView,
    BiometricHealthCheckView,
    BiometricSyncLogListView,
)

urlpatterns = [
    path("biometrics/devices/", BiometricDeviceListCreateView.as_view(), name="org-biometric-device-list"),
    path("biometrics/devices/<uuid:pk>/", BiometricDeviceDetailView.as_view(), name="org-biometric-device-detail"),
    path(
        "biometrics/devices/<uuid:pk>/sync-logs/",
        BiometricSyncLogListView.as_view(),
        name="org-biometric-device-sync-logs",
    ),
    path(
        "biometrics/devices/<uuid:pk>/health/", BiometricHealthCheckView.as_view(), name="org-biometric-device-health"
    ),
    path("biometrics/events/", AttendanceEventStreamView.as_view(), name="biometric-attendance-events"),
    path(
        "biometrics/devices/<uuid:device_id>/events/", DeviceEventStreamView.as_view(), name="biometric-device-events"
    ),
]
