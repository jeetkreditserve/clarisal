from django.urls import path

from .views import CtPayrollTaxSlabSetListCreateView

urlpatterns = [
    path('payroll/tax-slab-sets/', CtPayrollTaxSlabSetListCreateView.as_view(), name='ct-payroll-tax-slab-set-list-create'),
]

