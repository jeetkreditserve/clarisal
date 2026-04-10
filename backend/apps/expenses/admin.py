from django.contrib import admin

from .models import ExpenseCategory, ExpenseClaim, ExpenseClaimLine, ExpensePolicy, ExpenseReceipt


class ExpenseClaimLineInline(admin.TabularInline):
    model = ExpenseClaimLine
    extra = 0


@admin.register(ExpensePolicy)
class ExpensePolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'currency', 'is_active')
    list_filter = ('is_active', 'currency')
    search_fields = ('name', 'organisation__name')


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'policy', 'per_claim_limit', 'requires_receipt', 'is_active')
    list_filter = ('is_active', 'requires_receipt')
    search_fields = ('name', 'code', 'policy__name')


@admin.register(ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'organisation', 'status', 'reimbursement_status', 'claim_date')
    list_filter = ('status', 'reimbursement_status', 'currency')
    search_fields = ('title', 'employee__employee_code', 'employee__user__email')
    inlines = [ExpenseClaimLineInline]


@admin.register(ExpenseReceipt)
class ExpenseReceiptAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'line', 'mime_type', 'file_size', 'uploaded_by')
    search_fields = ('file_name', 'file_key')
