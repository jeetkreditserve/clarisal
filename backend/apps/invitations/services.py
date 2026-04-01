from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import NotFound

from apps.accounts.models import AccountType, User
from apps.accounts.workspaces import initialize_workforce_workspace, sync_user_role
from apps.audit.services import log_audit_event
from apps.common.security import generate_secure_token, hash_token
from apps.employees.models import Employee, EmployeeOnboardingStatus, EmployeeStatus
from apps.organisations.models import OrganisationMembershipStatus, OrganisationStatus
from apps.organisations.services import (
    ensure_org_admin_membership,
    set_primary_admin,
    transition_organisation_state,
)

from .models import Invitation, InvitationRole, InvitationStatus


def create_org_admin_invitation(organisation, email, first_name, last_name, invited_by):
    from .tasks import send_invite_email

    expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)
    raw_token = generate_secure_token()

    with transaction.atomic():
        Invitation.objects.filter(
            email=email,
            organisation=organisation,
            role=InvitationRole.ORG_ADMIN,
            status=InvitationStatus.PENDING,
        ).update(status=InvitationStatus.REVOKED, revoked_at=timezone.now())

        user, created = User.objects.get_or_create(
            email=email,
            account_type=AccountType.WORKFORCE,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'ORG_ADMIN',
                'is_active': False,
            },
        )
        if not created:
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=['first_name', 'last_name', 'updated_at'])

        ensure_org_admin_membership(
            organisation,
            user,
            invited_by=invited_by,
            status=OrganisationMembershipStatus.ACTIVE if user.is_active else OrganisationMembershipStatus.INVITED,
        )

        invite = Invitation.objects.create(
            email=email,
            organisation=organisation,
            role=InvitationRole.ORG_ADMIN,
            invited_by=invited_by,
            user=user,
            token_hash=hash_token(raw_token),
            status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=expiry_hours),
        )

        set_primary_admin(organisation, user, invited_by)
        sync_user_role(user)
        log_audit_event(
            invited_by,
            'organisation.invitation.created',
            organisation=organisation,
            target=user,
            payload={'role': InvitationRole.ORG_ADMIN, 'email': email},
        )
        transaction.on_commit(lambda: send_invite_email.delay(str(invite.id), raw_token))

    return user, invite


def create_employee_invitation(organisation, user, invited_by):
    from .tasks import send_invite_email

    expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)
    raw_token = generate_secure_token()
    with transaction.atomic():
        Invitation.objects.filter(
            email=user.email,
            organisation=organisation,
            role=InvitationRole.EMPLOYEE,
            status=InvitationStatus.PENDING,
        ).update(status=InvitationStatus.REVOKED, revoked_at=timezone.now())
        invite = Invitation.objects.create(
            email=user.email,
            organisation=organisation,
            role=InvitationRole.EMPLOYEE,
            invited_by=invited_by,
            user=user,
            token_hash=hash_token(raw_token),
            status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=expiry_hours),
        )
        transaction.on_commit(lambda: send_invite_email.delay(str(invite.id), raw_token))
    return invite


def validate_invite_token(token):
    token_hash = hash_token(token)
    try:
        invite = Invitation.objects.select_related('organisation', 'user').get(token_hash=token_hash)
    except Invitation.DoesNotExist:
        raise NotFound('Invitation not found.')

    if not invite.is_valid:
        if invite.is_expired:
            raise drf_serializers.ValidationError({'token': 'This invitation has expired.'})
        raise drf_serializers.ValidationError({'token': f'This invitation is {invite.status}.'})

    return invite


def accept_invitation(token, password='', request=None):
    invite = validate_invite_token(token)
    user = invite.user
    if user is None:
        raise drf_serializers.ValidationError({'token': 'Invitation has no associated user.'})

    if not user.is_active and not password:
        raise drf_serializers.ValidationError({'password': 'Password is required to activate this account.'})

    with transaction.atomic():
        if not user.is_active:
            user.set_password(password)
            user.is_active = True
            user.save(update_fields=['password', 'is_active', 'updated_at'])

        invite.status = InvitationStatus.ACCEPTED
        invite.accepted_at = timezone.now()
        invite.save(update_fields=['status', 'accepted_at'])

        if invite.role == InvitationRole.ORG_ADMIN and invite.organisation:
            ensure_org_admin_membership(
                invite.organisation,
                user,
                invited_by=invite.invited_by,
                status=OrganisationMembershipStatus.ACTIVE,
            )
            if invite.organisation.status == OrganisationStatus.PAID:
                transition_organisation_state(
                    invite.organisation,
                    OrganisationStatus.ACTIVE,
                    transitioned_by=user,
                    note='Org admin accepted invitation',
                )
            set_primary_admin(invite.organisation, user, user)

        if invite.role == InvitationRole.EMPLOYEE and invite.organisation:
            employee = Employee.objects.get(user=user, organisation=invite.organisation)
            if employee.status == EmployeeStatus.INVITED:
                employee.onboarding_status = EmployeeOnboardingStatus.BASIC_DETAILS_PENDING
                employee.save(update_fields=['onboarding_status', 'updated_at'])

        sync_user_role(user)

    log_audit_event(
        user,
        'invitation.accepted',
        organisation=invite.organisation,
        target=user,
        payload={'role': invite.role},
        request=request,
    )
    return user
