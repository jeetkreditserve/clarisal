from django.contrib import admin

from .models import (
    Organisation,
    OrganisationLicenceBatch,
    OrganisationLifecycleEvent,
    OrganisationLicenceLedger,
    OrganisationMembership,
    OrganisationNote,
    OrganisationStateTransition,
)


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'billing_status', 'access_state', 'licence_count', 'primary_admin_user')
    list_filter = ('status', 'billing_status', 'access_state', 'country_code', 'currency')
    search_fields = ('name', 'email', 'slug')
    autocomplete_fields = ('created_by', 'primary_admin_user', 'paid_marked_by')


@admin.register(OrganisationMembership)
class OrganisationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organisation', 'is_org_admin', 'status', 'accepted_at', 'last_used_at')
    list_filter = ('is_org_admin', 'status', 'organisation')
    search_fields = ('user__email', 'organisation__name')
    autocomplete_fields = ('user', 'organisation', 'invited_by')


@admin.register(OrganisationStateTransition)
class OrganisationStateTransitionAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'from_status', 'to_status', 'transitioned_by', 'created_at')
    list_filter = ('from_status', 'to_status')
    search_fields = ('organisation__name', 'transitioned_by__email')
    autocomplete_fields = ('organisation', 'transitioned_by')


@admin.register(OrganisationLicenceLedger)
class OrganisationLicenceLedgerAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'delta', 'reason', 'effective_from', 'created_by', 'created_at')
    list_filter = ('reason',)
    search_fields = ('organisation__name', 'created_by__email', 'note')
    autocomplete_fields = ('organisation', 'created_by')


@admin.register(OrganisationLicenceBatch)
class OrganisationLicenceBatchAdmin(admin.ModelAdmin):
    list_display = (
        'organisation',
        'quantity',
        'price_per_licence_per_month',
        'payment_status',
        'start_date',
        'end_date',
        'paid_at',
    )
    list_filter = ('payment_status', 'start_date', 'end_date')
    search_fields = ('organisation__name', 'note')
    autocomplete_fields = ('organisation', 'created_by', 'paid_by')


@admin.register(OrganisationLifecycleEvent)
class OrganisationLifecycleEventAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('organisation__name', 'actor__email')
    autocomplete_fields = ('organisation', 'actor')


@admin.register(OrganisationNote)
class OrganisationNoteAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'created_by', 'created_at')
    search_fields = ('organisation__name', 'created_by__email', 'body')
    autocomplete_fields = ('organisation', 'created_by')
