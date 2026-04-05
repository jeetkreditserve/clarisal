from django.urls import path

from .views import OrgReportView

urlpatterns = [
    path('reports/<str:report_type>/', OrgReportView.as_view(), name='org-report'),
]
