from django.urls import path

from .views import DepartmentDeactivateView, DepartmentDetailView, DepartmentListCreateView

urlpatterns = [
    path('departments/', DepartmentListCreateView.as_view(), name='department-list-create'),
    path('departments/<uuid:pk>/', DepartmentDetailView.as_view(), name='department-detail'),
    path('departments/<uuid:pk>/deactivate/', DepartmentDeactivateView.as_view(), name='department-deactivate'),
]
