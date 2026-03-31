from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.employees.models import Employee, EmployeeStatus
from .models import (
    LifecycleEventType,
    LicenceLedgerReason,
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationLifecycleEvent,
    OrganisationLicenceLedger,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationOnboardingStage,
    OrganisationStateTransition,
    OrganisationStatus,
)

VALID_TRANSITIONS = {
    OrganisationStatus.PENDING: [OrganisationStatus.PAID],
    OrganisationStatus.PAID: [OrganisationStatus.ACTIVE],
    OrganisationStatus.ACTIVE: [OrganisationStatus.SUSPENDED],
    OrganisationStatus.SUSPENDED: [OrganisationStatus.ACTIVE],
}

STAGE_ORDER = {
    OrganisationOnboardingStage.ORG_CREATED: 1,
    OrganisationOnboardingStage.LICENCES_ASSIGNED: 2,
    OrganisationOnboardingStage.PAYMENT_CONFIRMED: 3,
    OrganisationOnboardingStage.ADMIN_INVITED: 4,
    OrganisationOnboardingStage.ADMIN_ACTIVATED: 5,
    OrganisationOnboardingStage.MASTER_DATA_CONFIGURED: 6,
    OrganisationOnboardingStage.EMPLOYEES_INVITED: 7,
}


def _bump_onboarding_stage(org, stage):
    if STAGE_ORDER[stage] > STAGE_ORDER.get(org.onboarding_stage, 0):
        org.onboarding_stage = stage


def _sync_legacy_status(org):
    if org.access_state == OrganisationAccessState.SUSPENDED:
        org.status = OrganisationStatus.SUSPENDED
    elif org.access_state == OrganisationAccessState.ACTIVE:
        org.status = OrganisationStatus.ACTIVE
    elif org.billing_status == OrganisationBillingStatus.PAID:
        org.status = OrganisationStatus.PAID
    else:
        org.status = OrganisationStatus.PENDING


def create_lifecycle_event(organisation, event_type, actor=None, payload=None):
    return OrganisationLifecycleEvent.objects.create(
        organisation=organisation,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )


def get_org_licence_summary(org):
    purchased = org.licence_count
    used = Employee.objects.filter(
        organisation=org,
        status__in=[EmployeeStatus.INVITED, EmployeeStatus.ACTIVE],
    ).count()
    available = max(purchased - used, 0)
    utilisation_percent = int((used / purchased) * 100) if purchased else 0
    return {
        'purchased': purchased,
        'allocated': used,
        'available': available,
        'utilisation_percent': utilisation_percent,
    }


def create_organisation(name, licence_count, created_by, address='', phone='', email='', country_code='IN', currency='INR'):
    with transaction.atomic():
        organisation = Organisation.objects.create(
            name=name,
            address=address,
            phone=phone,
            email=email,
            licence_count=licence_count,
            created_by=created_by,
            country_code=country_code,
            currency=currency,
            billing_status=OrganisationBillingStatus.PENDING_PAYMENT,
            access_state=OrganisationAccessState.PROVISIONING,
            onboarding_stage=OrganisationOnboardingStage.LICENCES_ASSIGNED,
        )
        OrganisationLicenceLedger.objects.create(
            organisation=organisation,
            delta=licence_count,
            reason=LicenceLedgerReason.OPENING_BALANCE,
            note='Initial licence allocation',
            created_by=created_by,
        )
        create_lifecycle_event(
            organisation,
            LifecycleEventType.ORGANISATION_CREATED,
            created_by,
            {'licence_count': licence_count},
        )
        log_audit_event(
            created_by,
            'organisation.created',
            organisation=organisation,
            target=organisation,
            payload={'licence_count': licence_count},
        )
    return organisation


def transition_organisation_state(org, new_status, transitioned_by, note=''):
    allowed = VALID_TRANSITIONS.get(org.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{org.status}' to '{new_status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )
    with transaction.atomic():
        old_status = org.status
        now = timezone.now()
        if new_status == OrganisationStatus.PAID:
            org.billing_status = OrganisationBillingStatus.PAID
            org.access_state = OrganisationAccessState.PROVISIONING
            org.paid_marked_at = now
            org.paid_marked_by = transitioned_by
            _bump_onboarding_stage(org, OrganisationOnboardingStage.PAYMENT_CONFIRMED)
            event_type = LifecycleEventType.PAYMENT_MARKED
        elif new_status == OrganisationStatus.ACTIVE:
            org.access_state = OrganisationAccessState.ACTIVE
            org.activated_at = now
            org.suspended_at = None
            _bump_onboarding_stage(org, OrganisationOnboardingStage.ADMIN_ACTIVATED)
            event_type = (
                LifecycleEventType.ACCESS_RESTORED
                if old_status == OrganisationStatus.SUSPENDED
                else LifecycleEventType.ADMIN_ACTIVATED
            )
        elif new_status == OrganisationStatus.SUSPENDED:
            org.access_state = OrganisationAccessState.SUSPENDED
            org.suspended_at = now
            event_type = LifecycleEventType.ACCESS_SUSPENDED
        _sync_legacy_status(org)
        org.save()
        OrganisationStateTransition.objects.create(
            organisation=org,
            from_status=old_status,
            to_status=new_status,
            transitioned_by=transitioned_by,
            note=note,
        )
        create_lifecycle_event(
            org,
            event_type,
            transitioned_by,
            {'note': note, 'from_status': old_status, 'to_status': new_status},
        )
        log_audit_event(
            transitioned_by,
            f'organisation.status.{new_status.lower()}',
            organisation=org,
            target=org,
            payload={'from_status': old_status, 'to_status': new_status, 'note': note},
        )
    return org


def update_licence_count(org, new_count, changed_by=None, note=''):
    current_summary = get_org_licence_summary(org)
    if new_count < current_summary['allocated']:
        raise ValueError('Licence count cannot be lower than allocated employees.')

    delta = new_count - org.licence_count
    if delta == 0:
        return org

    with transaction.atomic():
        OrganisationLicenceLedger.objects.create(
            organisation=org,
            delta=delta,
            reason=LicenceLedgerReason.PURCHASE if delta > 0 else LicenceLedgerReason.ADJUSTMENT,
            note=note,
            created_by=changed_by,
        )
        org.licence_count = new_count
        _bump_onboarding_stage(org, OrganisationOnboardingStage.LICENCES_ASSIGNED)
        org.save(update_fields=['licence_count', 'onboarding_stage', 'updated_at'])
        create_lifecycle_event(
            org,
            LifecycleEventType.LICENCES_UPDATED,
            changed_by,
            {'delta': delta, 'new_count': new_count, 'note': note},
        )
        log_audit_event(
            changed_by,
            'organisation.licences.updated',
            organisation=org,
            target=org,
            payload={'delta': delta, 'new_count': new_count, 'note': note},
        )
    return org


def get_ct_dashboard_stats():
    agg = Organisation.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status=OrganisationStatus.ACTIVE)),
        pending=Count('id', filter=Q(status=OrganisationStatus.PENDING)),
        paid=Count('id', filter=Q(status=OrganisationStatus.PAID)),
        suspended=Count('id', filter=Q(status=OrganisationStatus.SUSPENDED)),
        licences=Sum('licence_count'),
    )
    return {
        'total_organisations': agg['total'],
        'active_organisations': agg['active'],
        'pending_organisations': agg['pending'],
        'paid_organisations': agg['paid'],
        'suspended_organisations': agg['suspended'],
        'total_employees': Employee.objects.filter(status=EmployeeStatus.ACTIVE).count(),
        'total_licences': agg['licences'] or 0,
        'allocated_licences': Employee.objects.filter(
            status__in=[EmployeeStatus.INVITED, EmployeeStatus.ACTIVE]
        ).count(),
    }


def get_org_dashboard_stats(organisation):
    employees = Employee.objects.filter(organisation=organisation)
    return {
        'total_employees': employees.count(),
        'active_employees': employees.filter(status=EmployeeStatus.ACTIVE).count(),
        'invited_employees': employees.filter(status=EmployeeStatus.INVITED).count(),
        'inactive_employees': employees.filter(status=EmployeeStatus.INACTIVE).count(),
        'terminated_employees': employees.filter(status=EmployeeStatus.TERMINATED).count(),
        'by_department': list(
            employees.filter(status=EmployeeStatus.ACTIVE)
            .exclude(department__isnull=True)
            .values(department_name=F('department__name'))
            .annotate(count=Count('id'))
            .order_by('-count', 'department_name')
        ),
        'by_location': list(
            employees.filter(status=EmployeeStatus.ACTIVE)
            .exclude(office_location__isnull=True)
            .values(location_name=F('office_location__name'))
            .annotate(count=Count('id'))
            .order_by('-count', 'location_name')
        ),
        'recent_joins': list(
            employees.exclude(date_of_joining__isnull=True)
            .order_by('-date_of_joining')
            .values('id', 'employee_code', 'designation', 'date_of_joining', 'user__first_name', 'user__last_name')[:10]
        ),
        'licence_used': get_org_licence_summary(organisation)['allocated'],
        'licence_total': organisation.licence_count,
        'onboarding_stage': organisation.onboarding_stage,
    }


def set_primary_admin(organisation, user, actor=None):
    organisation.primary_admin_user = user
    _bump_onboarding_stage(organisation, OrganisationOnboardingStage.ADMIN_INVITED)
    organisation.save(update_fields=['primary_admin_user', 'onboarding_stage', 'updated_at'])
    create_lifecycle_event(
        organisation,
        LifecycleEventType.ADMIN_INVITED,
        actor,
        {'user_id': str(user.id), 'email': user.email},
    )
    log_audit_event(
        actor,
        'organisation.primary_admin.assigned',
        organisation=organisation,
        target=user,
        payload={'email': user.email},
    )
    return organisation


def ensure_org_admin_membership(organisation, user, invited_by=None, status=OrganisationMembershipStatus.ACTIVE):
    membership, _ = OrganisationMembership.objects.get_or_create(
        organisation=organisation,
        user=user,
        defaults={
            'is_org_admin': True,
            'status': status,
            'invited_by': invited_by,
            'accepted_at': timezone.now() if status == OrganisationMembershipStatus.ACTIVE else None,
        },
    )
    changed = False
    if not membership.is_org_admin:
        membership.is_org_admin = True
        changed = True
    if membership.status != status:
        membership.status = status
        changed = True
    if invited_by and membership.invited_by_id is None:
        membership.invited_by = invited_by
        changed = True
    if status == OrganisationMembershipStatus.ACTIVE and membership.accepted_at is None:
        membership.accepted_at = timezone.now()
        changed = True
    if changed:
        membership.save()
    return membership


def mark_master_data_configured(organisation, actor=None):
    if organisation.locations.filter(is_active=True).exists() and organisation.departments.filter(is_active=True).exists():
        if organisation.onboarding_stage != OrganisationOnboardingStage.MASTER_DATA_CONFIGURED:
            organisation.onboarding_stage = OrganisationOnboardingStage.MASTER_DATA_CONFIGURED
            organisation.save(update_fields=['onboarding_stage', 'updated_at'])
            create_lifecycle_event(organisation, LifecycleEventType.MASTER_DATA_CONFIGURED, actor)
            log_audit_event(
                actor,
                'organisation.master_data.configured',
                organisation=organisation,
                target=organisation,
            )
    return organisation


def mark_employee_invited(organisation, actor=None, employee=None):
    _bump_onboarding_stage(organisation, OrganisationOnboardingStage.EMPLOYEES_INVITED)
    organisation.save(update_fields=['onboarding_stage', 'updated_at'])
    create_lifecycle_event(
        organisation,
        LifecycleEventType.EMPLOYEE_INVITED,
        actor,
        {'employee_id': str(employee.id) if employee else None},
    )
    log_audit_event(
        actor,
        'organisation.employee.invited',
        organisation=organisation,
        target=employee,
        payload={'employee_id': str(employee.id) if employee else None},
    )
    return organisation
