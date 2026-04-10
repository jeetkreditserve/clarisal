from django.urls import path

from .views import (
    AssetAssignmentAcknowledgeView,
    AssetAssignmentDetailView,
    AssetAssignmentListCreateView,
    AssetAssignmentLostView,
    AssetAssignmentReturnView,
    AssetCategoryDetailView,
    AssetCategoryListCreateView,
    AssetIncidentListCreateView,
    AssetItemDetailView,
    AssetItemListCreateView,
    AssetMaintenanceDetailView,
    AssetMaintenanceListCreateView,
    EmployeeAssetAssignmentsView,
)

urlpatterns = [
    path('assets/categories/', AssetCategoryListCreateView.as_view(), name='asset-category-list'),
    path('assets/categories/<uuid:pk>/', AssetCategoryDetailView.as_view(), name='asset-category-detail'),
    path('assets/items/', AssetItemListCreateView.as_view(), name='asset-item-list'),
    path('assets/items/<uuid:pk>/', AssetItemDetailView.as_view(), name='asset-item-detail'),
    path('assets/assignments/', AssetAssignmentListCreateView.as_view(), name='asset-assignment-list'),
    path('assets/assignments/<uuid:pk>/', AssetAssignmentDetailView.as_view(), name='asset-assignment-detail'),
    path('assets/assignments/<uuid:pk>/acknowledge/', AssetAssignmentAcknowledgeView.as_view(), name='asset-assignment-acknowledge'),
    path('assets/assignments/<uuid:pk>/return/', AssetAssignmentReturnView.as_view(), name='asset-assignment-return'),
    path('assets/assignments/<uuid:pk>/lost/', AssetAssignmentLostView.as_view(), name='asset-assignment-lost'),
    path('employees/<uuid:employee_id>/assets/', EmployeeAssetAssignmentsView.as_view(), name='employee-assets'),
    path('assets/maintenance/', AssetMaintenanceListCreateView.as_view(), name='asset-maintenance-list'),
    path('assets/maintenance/<uuid:pk>/', AssetMaintenanceDetailView.as_view(), name='asset-maintenance-detail'),
    path('assets/incidents/', AssetIncidentListCreateView.as_view(), name='asset-incident-list'),
]
