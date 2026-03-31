from django.urls import path

from .views import (
    DocumentTypeListView,
    EmployeeDocumentListView,
    EmployeeDocumentRequestListCreateView,
    EmployeeDocumentDownloadView,
    EmployeeDocumentRejectView,
    EmployeeDocumentVerifyView,
)

urlpatterns = [
    path('document-types/', DocumentTypeListView.as_view(), name='document-types'),
    path('employees/<uuid:employee_id>/document-requests/', EmployeeDocumentRequestListCreateView.as_view(), name='employee-document-requests'),
    path('employees/<uuid:employee_id>/documents/', EmployeeDocumentListView.as_view(), name='employee-documents'),
    path('employees/<uuid:employee_id>/documents/<uuid:doc_id>/download/', EmployeeDocumentDownloadView.as_view(), name='employee-document-download'),
    path('employees/<uuid:employee_id>/documents/<uuid:doc_id>/verify/', EmployeeDocumentVerifyView.as_view(), name='employee-document-verify'),
    path('employees/<uuid:employee_id>/documents/<uuid:doc_id>/reject/', EmployeeDocumentRejectView.as_view(), name='employee-document-reject'),
]
