from django.urls import path

from .views import (
    MyForm12BBDownloadView,
    MyInvestmentDeclarationListCreateView,
    MyPayslipDetailView,
    MyPayslipDownloadView,
    MyPayslipListView,
)

urlpatterns = [
    path("payroll/payslips/", MyPayslipListView.as_view(), name="my-payslip-list"),
    path(
        "payroll/payslips/<uuid:pk>/",
        MyPayslipDetailView.as_view(),
        name="my-payslip-detail",
    ),
    path(
        "payroll/payslips/<uuid:pk>/download/",
        MyPayslipDownloadView.as_view(),
        name="my-payslip-download",
    ),
    path(
        "payroll/form12bb/<str:fiscal_year>/download/",
        MyForm12BBDownloadView.as_view(),
        name="my-form12bb-download",
    ),
    path(
        "payroll/investment-declarations/",
        MyInvestmentDeclarationListCreateView.as_view(),
        name="my-investment-declaration-list-create",
    ),
]
