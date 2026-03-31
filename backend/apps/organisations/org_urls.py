from django.urls import path

from .views import OrgDashboardStatsView

urlpatterns = [
    path('dashboard/', OrgDashboardStatsView.as_view(), name='org-dashboard'),
]
