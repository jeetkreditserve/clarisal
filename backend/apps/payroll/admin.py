from django.contrib import admin

from .models import (
    CompensationAssignment,
    CompensationTemplate,
    LabourWelfareFundRule,
    PayrollComponent,
    PayrollRun,
    PayrollTaxSlabSet,
    PayrollTDSChallan,
    Payslip,
    ProfessionalTaxRule,
)


@admin.register(PayrollTaxSlabSet)
class PayrollTaxSlabSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'fiscal_year', 'country_code', 'is_system_master', 'is_active')
    list_filter = ('country_code', 'is_system_master', 'is_active')
    search_fields = ('name', 'organisation__name')


@admin.register(ProfessionalTaxRule)
class ProfessionalTaxRuleAdmin(admin.ModelAdmin):
    list_display = ('state_code', 'state_name', 'income_basis', 'deduction_frequency', 'effective_from', 'is_active')
    list_filter = ('country_code', 'state_code', 'income_basis', 'deduction_frequency', 'is_active')
    search_fields = ('state_code', 'state_name', 'source_label')


@admin.register(LabourWelfareFundRule)
class LabourWelfareFundRuleAdmin(admin.ModelAdmin):
    list_display = ('state_code', 'state_name', 'wage_basis', 'deduction_frequency', 'effective_from', 'is_active')
    list_filter = ('country_code', 'state_code', 'wage_basis', 'deduction_frequency', 'is_active')
    search_fields = ('state_code', 'state_name', 'source_label')


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


@admin.register(PayrollTDSChallan)
class PayrollTDSChallanAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'fiscal_year', 'quarter', 'period_year', 'period_month', 'tax_deposited', 'deposit_date')
    list_filter = ('fiscal_year', 'quarter')
    search_fields = ('organisation__name', 'bsr_code', 'challan_serial_number', 'statement_receipt_number')
