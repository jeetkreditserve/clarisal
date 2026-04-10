from django.urls import path

from .views import MyAssetAssignmentsView, MyAssetAcknowledgementView

urlpatterns = [
    path('my/assets/', MyAssetAssignmentsView.as_view(), name='my-assets'),
    path('my/assets/<uuid:assignment_id>/acknowledge/', MyAssetAcknowledgementView.as_view(), name='my-asset-acknowledge'),
]
