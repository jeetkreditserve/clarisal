from django.urls import path

from .views import (
    EmployeeDeleteView,
    EmployeeDetailView,
    EmployeeEndEmploymentView,
    EmployeeListInviteView,
    EmployeeMarkJoinedView,
    EmployeeOffboardingCompleteView,
    EmployeeOffboardingDetailView,
    EmployeeOffboardingTaskDetailView,
    EmployeeProbationCompleteView,
)

urlpatterns = [
    path('employees/', EmployeeListInviteView.as_view(), name='employee-list-invite'),
    path('employees/<uuid:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<uuid:pk>/mark-joined/', EmployeeMarkJoinedView.as_view(), name='employee-mark-joined'),
    path('employees/<uuid:pk>/end-employment/', EmployeeEndEmploymentView.as_view(), name='employee-end-employment'),
    path('employees/<uuid:pk>/probation-complete/', EmployeeProbationCompleteView.as_view(), name='employee-probation-complete'),
    path('employees/<uuid:pk>/offboarding/', EmployeeOffboardingDetailView.as_view(), name='employee-offboarding-detail'),
    path('employees/<uuid:pk>/offboarding/complete/', EmployeeOffboardingCompleteView.as_view(), name='employee-offboarding-complete'),
    path('employees/<uuid:pk>/offboarding/tasks/<uuid:task_id>/', EmployeeOffboardingTaskDetailView.as_view(), name='employee-offboarding-task-detail'),
    path('employees/<uuid:pk>/delete/', EmployeeDeleteView.as_view(), name='employee-delete'),
]
