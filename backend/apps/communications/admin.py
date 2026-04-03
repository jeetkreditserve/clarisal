from django.contrib import admin

from .models import Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'organisation', 'audience_type', 'status', 'scheduled_for', 'published_at')
    list_filter = ('status', 'audience_type', 'organisation')
    search_fields = ('title', 'organisation__name')
