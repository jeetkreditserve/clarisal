from django.db.models import Prefetch

from .models import Organisation


def get_organisations():
    return (
        Organisation.objects.select_related(
            'created_by',
            'primary_admin_user',
            'paid_marked_by',
            'bootstrap_admin',
        )
        .prefetch_related(
            'addresses',
            'legal_identifiers',
            'tax_registrations',
            'state_transitions',
            'lifecycle_events',
            'licence_ledger_entries',
            'licence_batches',
        )
        .order_by('-created_at')
    )


def get_organisation_by_id(pk):
    return get_organisations().get(id=pk)


def get_org_admins(organisation, include_inactive=False):
    from .models import OrganisationMembership, OrganisationMembershipStatus

    queryset = OrganisationMembership.objects.select_related('user').filter(
        organisation=organisation,
        is_org_admin=True,
    )
    if not include_inactive:
        queryset = queryset.filter(status=OrganisationMembershipStatus.ACTIVE)
    return queryset.order_by('created_at')
