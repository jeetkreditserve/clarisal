from django.contrib.auth import login
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsControlTowerUser
from apps.accounts.serializers import UserSerializer
from apps.accounts.workspaces import initialize_workforce_workspace
from apps.common.transactional_emails import build_frontend_url
from apps.organisations.models import Organisation, OrganisationMembership

from .serializers import AcceptInviteSerializer, InviteOrgAdminSerializer
from .services import accept_invitation, create_org_admin_invitation, validate_invite_token


class InviteOrgAdminView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk):
        org = get_object_or_404(Organisation, id=pk)
        if org.status not in ('PAID', 'ACTIVE'):
            return Response(
                {'error': 'Organisation must be in PAID or ACTIVE status to invite admins.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = InviteOrgAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, invite = create_org_admin_invitation(
            organisation=org,
            email=serializer.validated_data['email'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            invited_by=request.user,
        )
        return Response(
            {
                'user_id': str(user.id),
                'email': invite.email,
                'status': invite.status,
                'expires_at': invite.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class ResendOrgAdminInviteView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, uid):
        org = get_object_or_404(Organisation, id=pk)
        membership = get_object_or_404(
            OrganisationMembership.objects.select_related('user'),
            organisation=org,
            user_id=uid,
            is_org_admin=True,
        )
        _, invite = create_org_admin_invitation(
            organisation=org,
            email=membership.user.email,
            first_name=membership.user.first_name,
            last_name=membership.user.last_name,
            invited_by=request.user,
        )
        return Response({'email': invite.email, 'status': invite.status, 'expires_at': invite.expires_at})


class ValidateInviteTokenView(APIView):
    permission_classes = []
    authentication_classes = []
    throttle_scope = 'invite_validate'

    def get(self, request, token):
        from rest_framework import serializers as drf_serializers
        from rest_framework.exceptions import NotFound

        try:
            invite = validate_invite_token(token)
        except (drf_serializers.ValidationError, NotFound) as exc:
            return Response(getattr(exc, 'detail', str(exc)), status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'email': invite.email,
                'role': invite.role,
                'organisation_name': invite.organisation.name if invite.organisation else None,
                'requires_password_setup': not bool(invite.user and invite.user.is_active),
            }
        )


class AcceptInviteView(APIView):
    permission_classes = []
    authentication_classes = []
    throttle_scope = 'invite_accept'

    def post(self, request):
        from rest_framework import serializers as drf_serializers

        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = accept_invitation(
                token=serializer.validated_data['token'],
                password=serializer.validated_data.get('password', ''),
                request=request,
            )
        except drf_serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        user = result['user']
        if result.get('requires_login'):
            login_url = build_frontend_url('/auth/login')
            return Response(
                {
                    'requires_login': True,
                    'login_url': login_url,
                    'message': 'Password set successfully. Sign in from the workforce login page to continue.',
                }
            )

        login(request, user)
        request.session.cycle_key()
        initialize_workforce_workspace(request, user)
        get_token(request)
        return Response(
            {
                'requires_login': False,
                'user': UserSerializer(user, context={'request': request}).data,
            }
        )
