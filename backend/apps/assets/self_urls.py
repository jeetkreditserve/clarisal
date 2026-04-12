from django.urls import path

from .views import MyAssetAcknowledgementView, MyAssetAssignmentsView

urlpatterns = [
    path('assets/', MyAssetAssignmentsView.as_view(), name='asset-list'),
    path('assets/<uuid:assignment_id>/acknowledge/', MyAssetAcknowledgementView.as_view(), name='asset-acknowledge'),
]
