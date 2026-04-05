from django.urls import path

from .views import CtPayrollStatutoryMasterListView, CtPayrollTaxSlabSetDetailView, CtPayrollTaxSlabSetListCreateView

urlpatterns = [
    path('payroll/tax-slab-sets/', CtPayrollTaxSlabSetListCreateView.as_view(), name='ct-payroll-tax-slab-set-list-create'),
    path('payroll/tax-slab-sets/<uuid:pk>/', CtPayrollTaxSlabSetDetailView.as_view(), name='ct-payroll-tax-slab-set-detail'),
    path('payroll/statutory-masters/', CtPayrollStatutoryMasterListView.as_view(), name='ct-payroll-statutory-master-list'),
]
