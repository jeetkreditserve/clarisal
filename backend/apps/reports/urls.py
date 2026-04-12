from django.urls import path

from .views import (
    OrgReportView,
    ReportDatasetListView,
    ReportExportView,
    ReportFolderListCreateView,
    ReportRunDetailView,
    ReportRunListView,
    ReportTemplateDetailView,
    ReportTemplateDraftPreviewView,
    ReportTemplateListCreateView,
    ReportTemplatePreviewView,
    ReportTemplateRunView,
)

urlpatterns = [
    path('reports/datasets/', ReportDatasetListView.as_view(), name='report-dataset-list'),
    path('reports/folders/', ReportFolderListCreateView.as_view(), name='report-folder-list-create'),
    path('reports/templates/', ReportTemplateListCreateView.as_view(), name='report-template-list-create'),
    path('reports/templates/preview-draft/', ReportTemplateDraftPreviewView.as_view(), name='report-template-preview-draft'),
    path('reports/templates/<uuid:pk>/', ReportTemplateDetailView.as_view(), name='report-template-detail'),
    path('reports/templates/<uuid:pk>/preview/', ReportTemplatePreviewView.as_view(), name='report-template-preview'),
    path('reports/templates/<uuid:pk>/run/', ReportTemplateRunView.as_view(), name='report-template-run'),
    path('reports/runs/', ReportRunListView.as_view(), name='report-run-list'),
    path('reports/runs/<uuid:pk>/', ReportRunDetailView.as_view(), name='report-run-detail'),
    path('reports/runs/<uuid:pk>/exports/<uuid:export_id>/', ReportExportView.as_view(), name='report-export-download'),
    path('reports/<str:report_type>/', OrgReportView.as_view(), name='org-report'),
]
