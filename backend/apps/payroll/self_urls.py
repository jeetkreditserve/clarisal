from django.urls import path

from .views import MyInvestmentDeclarationListCreateView, MyPayslipDetailView, MyPayslipDownloadView, MyPayslipListView

urlpatterns = [
    path('payroll/payslips/', MyPayslipListView.as_view(), name='my-payslip-list'),
    path('payroll/payslips/<uuid:pk>/', MyPayslipDetailView.as_view(), name='my-payslip-detail'),
    path('payroll/payslips/<uuid:pk>/download/', MyPayslipDownloadView.as_view(), name='my-payslip-download'),
    path('payroll/investment-declarations/', MyInvestmentDeclarationListCreateView.as_view(), name='my-investment-declaration-list-create'),
]
