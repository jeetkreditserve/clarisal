from django.urls import path

from .views import (
    MyDocumentDownloadView,
    MyDocumentListCreateView,
    MyDocumentRequestListView,
    MyDocumentRequestUploadView,
)

urlpatterns = [
    path('document-requests/', MyDocumentRequestListView.as_view(), name='my-document-requests'),
    path('document-requests/<uuid:request_id>/upload/', MyDocumentRequestUploadView.as_view(), name='my-document-request-upload'),
    path('documents/', MyDocumentListCreateView.as_view(), name='my-documents'),
    path('documents/<uuid:doc_id>/download/', MyDocumentDownloadView.as_view(), name='my-document-download'),
]
