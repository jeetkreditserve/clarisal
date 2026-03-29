from django.db import transaction
from django.db.models import Count, Q
from apps.accounts.models import User, UserRole
from .models import Organisation, OrganisationStateTransition, OrganisationStatus

VALID_TRANSITIONS = {
    OrganisationStatus.PENDING: [OrganisationStatus.PAID],
    OrganisationStatus.PAID: [OrganisationStatus.ACTIVE],
    OrganisationStatus.ACTIVE: [OrganisationStatus.SUSPENDED],
    OrganisationStatus.SUSPENDED: [OrganisationStatus.ACTIVE],
}


def create_organisation(name, licence_count, created_by, address='', phone='', email=''):
    return Organisation.objects.create(
        name=name,
        address=address,
        phone=phone,
        email=email,
        licence_count=licence_count,
        created_by=created_by,
    )


def transition_organisation_state(org, new_status, transitioned_by, note=''):
    allowed = VALID_TRANSITIONS.get(org.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{org.status}' to '{new_status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )
    with transaction.atomic():
        old_status = org.status
        org.status = new_status
        org.save(update_fields=['status', 'updated_at'])
        OrganisationStateTransition.objects.create(
            organisation=org,
            from_status=old_status,
            to_status=new_status,
            transitioned_by=transitioned_by,
            note=note,
        )
    return org


def update_licence_count(org, new_count):
    org.licence_count = new_count
    org.save(update_fields=['licence_count', 'updated_at'])
    return org


def get_ct_dashboard_stats():
    agg = Organisation.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status=OrganisationStatus.ACTIVE)),
        pending=Count('id', filter=Q(status=OrganisationStatus.PENDING)),
        paid=Count('id', filter=Q(status=OrganisationStatus.PAID)),
        suspended=Count('id', filter=Q(status=OrganisationStatus.SUSPENDED)),
    )
    return {
        'total_organisations': agg['total'],
        'active_organisations': agg['active'],
        'pending_organisations': agg['pending'],
        'paid_organisations': agg['paid'],
        'suspended_organisations': agg['suspended'],
        'total_employees': User.objects.filter(role=UserRole.EMPLOYEE, is_active=True).count(),
    }
