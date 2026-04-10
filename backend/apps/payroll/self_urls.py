from django.urls import path

from .views import (
    MyForm12BBDownloadView,
    MyInvestmentDeclarationDetailView,
    MyInvestmentDeclarationListCreateView,
    MyPayslipDetailView,
    MyPayslipDownloadView,
    MyPayslipFiscalYearDownloadView,
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
        "payroll/payslips/fiscal-year/<str:fiscal_year>/download/",
        MyPayslipFiscalYearDownloadView.as_view(),
        name="my-payslip-fiscal-year-download",
    ),
    path(
        "payroll/form12bb/<str:fiscal_year>/download/",
        MyForm12BBDownloadView.as_view(),
        name="my-form12bb-download",
    ),
    path(
        "payroll/form-12bb/<str:fiscal_year>/",
        MyForm12BBDownloadView.as_view(),
        name="my-form-12bb-download",
    ),
    path(
        "payroll/investment-declarations/",
        MyInvestmentDeclarationListCreateView.as_view(),
        name="my-investment-declaration-list-create",
    ),
    path(
        "payroll/investment-declarations/<uuid:pk>/",
        MyInvestmentDeclarationDetailView.as_view(),
        name="my-investment-declaration-detail",
    ),
]
