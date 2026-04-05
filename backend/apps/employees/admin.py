from django.contrib import admin

from .models import EducationRecord, Employee, EmployeeBankAccount, EmployeeGovernmentId, EmployeeProfile


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'user', 'organisation', 'designation', 'status', 'employment_type')
    list_filter = ('status', 'employment_type', 'organisation')
    search_fields = ('employee_code', 'user__email', 'user__first_name', 'user__last_name', 'designation')
    autocomplete_fields = ('user', 'organisation', 'department', 'office_location', 'reporting_to')


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('employee', 'phone_personal', 'city', 'state', 'country')
    search_fields = ('employee__employee_code', 'employee__user__email', 'city', 'state')
    autocomplete_fields = ('employee',)


@admin.register(EducationRecord)
class EducationRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'degree', 'institution', 'end_year', 'is_current')
    search_fields = ('employee__employee_code', 'employee__user__email', 'degree', 'institution')
    autocomplete_fields = ('employee',)


@admin.register(EmployeeGovernmentId)
class EmployeeGovernmentIdAdmin(admin.ModelAdmin):
    list_display = ('employee', 'id_type', 'masked_identifier', 'status', 'modified_at')
    list_filter = ('id_type', 'status')
    search_fields = ('employee__employee_code', 'employee__user__email', 'name_on_id', 'masked_identifier')
    autocomplete_fields = ('employee',)


@admin.register(EmployeeBankAccount)
class EmployeeBankAccountAdmin(admin.ModelAdmin):
    list_display = ('employee', 'bank_name', 'masked_account_number', 'account_type', 'is_primary')
    list_filter = ('account_type', 'is_primary')
    search_fields = ('employee__employee_code', 'employee__user__email', 'bank_name', 'masked_account_number')
    autocomplete_fields = ('employee',)
