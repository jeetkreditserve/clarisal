from .models import Organisation


def get_organisations():
    return Organisation.objects.select_related('created_by').prefetch_related('state_transitions').order_by('-created_at')


def get_organisation_by_id(pk):
    return Organisation.objects.select_related('created_by').prefetch_related('state_transitions').get(id=pk)


def get_org_admins(organisation):
    from apps.accounts.models import User, UserRole
    return User.objects.filter(organisation=organisation, role=UserRole.ORG_ADMIN)
