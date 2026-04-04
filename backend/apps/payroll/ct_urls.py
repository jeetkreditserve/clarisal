from django.urls import path

from .views import CtPayrollStatutoryMasterListView, CtPayrollTaxSlabSetListCreateView

urlpatterns = [
    path('payroll/tax-slab-sets/', CtPayrollTaxSlabSetListCreateView.as_view(), name='ct-payroll-tax-slab-set-list-create'),
    path('payroll/statutory-masters/', CtPayrollStatutoryMasterListView.as_view(), name='ct-payroll-statutory-master-list'),
]
