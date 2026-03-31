from django.urls import path

from .views import (
    EmployeeDeleteView,
    EmployeeDetailView,
    EmployeeEndEmploymentView,
    EmployeeListInviteView,
    EmployeeMarkJoinedView,
)

urlpatterns = [
    path('employees/', EmployeeListInviteView.as_view(), name='employee-list-invite'),
    path('employees/<uuid:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<uuid:pk>/mark-joined/', EmployeeMarkJoinedView.as_view(), name='employee-mark-joined'),
    path('employees/<uuid:pk>/end-employment/', EmployeeEndEmploymentView.as_view(), name='employee-end-employment'),
    path('employees/<uuid:pk>/delete/', EmployeeDeleteView.as_view(), name='employee-delete'),
]
