import secrets
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers as drf_serializers
from apps.accounts.models import User, UserRole
from apps.organisations.models import Organisation, OrganisationStatus
from apps.organisations.services import transition_organisation_state
from .models import Invitation, InvitationRole, InvitationStatus


def create_org_admin_invitation(organisation, email, first_name, last_name, invited_by):
    from .tasks import send_invite_email

    expiry_hours = getattr(settings, 'INVITE_TOKEN_EXPIRY_HOURS', 48)

    with transaction.atomic():
        # Revoke any existing pending invitations for this email + org
        Invitation.objects.filter(
            email=email,
            organisation=organisation,
            role=InvitationRole.ORG_ADMIN,
            status=InvitationStatus.PENDING,
        ).update(status=InvitationStatus.REVOKED)

        # Create or get user (may already exist if re-inviting)
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': UserRole.ORG_ADMIN,
                'organisation': organisation,
                'is_active': False,
            },
        )
        if not user.is_active:
            user.first_name = first_name
            user.last_name = last_name
            user.organisation = organisation
            user.role = UserRole.ORG_ADMIN
            user.save(update_fields=['first_name', 'last_name', 'organisation', 'role'])

        invite = Invitation.objects.create(
            token=secrets.token_urlsafe(32),
            email=email,
            organisation=organisation,
            role=InvitationRole.ORG_ADMIN,
            invited_by=invited_by,
            user=user,
            status=InvitationStatus.PENDING,
            expires_at=timezone.now() + timezone.timedelta(hours=expiry_hours),
        )

    transaction.on_commit(lambda: send_invite_email.delay(str(invite.id)))
    return user, invite


def validate_invite_token(token):
    try:
        invite = Invitation.objects.select_related('organisation', 'user').get(token=token)
    except Invitation.DoesNotExist:
        raise drf_serializers.ValidationError({'token': 'Invitation not found.'})

    if not invite.is_valid:
        if invite.is_expired:
            raise drf_serializers.ValidationError({'token': 'This invitation has expired.'})
        raise drf_serializers.ValidationError({'token': f'This invitation is {invite.status}.'})

    return invite


def accept_invitation(token, password):
    from rest_framework_simplejwt.tokens import RefreshToken

    invite = validate_invite_token(token)
    user = invite.user

    with transaction.atomic():
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=['password', 'is_active', 'updated_at'])

        invite.status = InvitationStatus.ACCEPTED
        invite.save(update_fields=['status'])

        # Transition org PAID -> ACTIVE when org admin onboards
        if (invite.role == InvitationRole.ORG_ADMIN
                and invite.organisation
                and invite.organisation.status == OrganisationStatus.PAID):
            transition_organisation_state(
                invite.organisation,
                OrganisationStatus.ACTIVE,
                transitioned_by=user,
                note='Org admin accepted invitation',
            )

    # Generate JWT tokens with custom claims
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['org_id'] = str(user.organisation_id) if user.organisation_id else None
    refresh['email'] = user.email

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'org_id': str(user.organisation_id) if user.organisation_id else None,
        },
    }
