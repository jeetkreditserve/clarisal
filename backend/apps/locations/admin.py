from django.contrib import admin

from .models import OfficeLocation


@admin.register(OfficeLocation)
class OfficeLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'city', 'state', 'is_active', 'modified_at')
    list_filter = ('is_active', 'organisation', 'state')
    search_fields = ('name', 'organisation__name', 'city', 'state')
    autocomplete_fields = ('organisation',)
