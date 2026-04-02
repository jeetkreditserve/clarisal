from django.urls import path

from .views import MyPayslipDetailView, MyPayslipListView

urlpatterns = [
    path('payroll/payslips/', MyPayslipListView.as_view(), name='my-payslip-list'),
    path('payroll/payslips/<uuid:pk>/', MyPayslipDetailView.as_view(), name='my-payslip-detail'),
]

