from django.urls import path

from .views import (
    EmployeeDocumentDownloadView,
    EmployeeDocumentListCreateView,
    EmployeeDocumentRejectView,
    EmployeeDocumentVerifyView,
)

urlpatterns = [
    path('employees/<uuid:employee_id>/documents/', EmployeeDocumentListCreateView.as_view(), name='employee-documents'),
    path('employees/<uuid:employee_id>/documents/<uuid:doc_id>/download/', EmployeeDocumentDownloadView.as_view(), name='employee-document-download'),
    path('employees/<uuid:employee_id>/documents/<uuid:doc_id>/verify/', EmployeeDocumentVerifyView.as_view(), name='employee-document-verify'),
    path('employees/<uuid:employee_id>/documents/<uuid:doc_id>/reject/', EmployeeDocumentRejectView.as_view(), name='employee-document-reject'),
]
