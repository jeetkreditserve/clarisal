from django.contrib import admin

from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'is_active', 'modified_at')
    list_filter = ('is_active', 'organisation')
    search_fields = ('name', 'organisation__name')
    autocomplete_fields = ('organisation',)
