from django.contrib import admin

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'organisation', 'role', 'status', 'expires_at', 'accepted_at', 'created_at')
    list_filter = ('role', 'status', 'organisation')
    search_fields = ('email', 'organisation__name', 'user__email')
    autocomplete_fields = ('organisation', 'invited_by', 'user')
    readonly_fields = ('token_hash', 'created_at', 'accepted_at', 'revoked_at')
