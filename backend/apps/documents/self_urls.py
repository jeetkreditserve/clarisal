from django.urls import path

from .views import MyDocumentDownloadView, MyDocumentListCreateView

urlpatterns = [
    path('documents/', MyDocumentListCreateView.as_view(), name='my-documents'),
    path('documents/<uuid:doc_id>/download/', MyDocumentDownloadView.as_view(), name='my-document-download'),
]
