from django.contrib import admin

from .models import (
    CompensationAssignment,
    CompensationTemplate,
    PayrollComponent,
    PayrollRun,
    PayrollTaxSlabSet,
    Payslip,
)


@admin.register(PayrollTaxSlabSet)
class PayrollTaxSlabSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'fiscal_year', 'country_code', 'is_system_master', 'is_active')
    list_filter = ('country_code', 'is_system_master', 'is_active')
    search_fields = ('name', 'organisation__name')


@admin.register(PayrollComponent)
class PayrollComponentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'organisation', 'component_type', 'is_taxable', 'is_system_default')
    list_filter = ('component_type', 'is_taxable', 'is_system_default')
    search_fields = ('code', 'name', 'organisation__name')


@admin.register(CompensationTemplate)
class CompensationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'organisation__name')


@admin.register(CompensationAssignment)
class CompensationAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'template', 'effective_from', 'version', 'status')
    list_filter = ('status',)
    search_fields = ('employee__employee_code', 'employee__user__email', 'template__name')


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'period_year', 'period_month', 'run_type', 'status')
    list_filter = ('run_type', 'status')
    search_fields = ('name', 'organisation__name')


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('slip_number', 'organisation', 'employee', 'period_year', 'period_month')
    search_fields = ('slip_number', 'employee__employee_code', 'employee__user__email')
