from django.urls import path

from .views import EmployeeDetailView, EmployeeListInviteView, EmployeeTerminateView

urlpatterns = [
    path('employees/', EmployeeListInviteView.as_view(), name='employee-list-invite'),
    path('employees/<uuid:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<uuid:pk>/terminate/', EmployeeTerminateView.as_view(), name='employee-terminate'),
]
