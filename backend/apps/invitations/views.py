from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsControlTowerUser
from apps.organisations.models import Organisation
from apps.organisations.repositories import get_org_admins
from apps.organisations.serializers import OrgAdminSerializer
from .serializers import InviteOrgAdminSerializer, AcceptInviteSerializer
from .services import create_org_admin_invitation, validate_invite_token, accept_invitation


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
        return Response({
            'user_id': str(user.id),
            'email': invite.email,
            'status': invite.status,
            'expires_at': invite.expires_at,
        }, status=status.HTTP_201_CREATED)


class ResendOrgAdminInviteView(APIView):
    permission_classes = [IsControlTowerUser]

    def post(self, request, pk, uid):
        from apps.accounts.models import User, UserRole
        org = get_object_or_404(Organisation, id=pk)
        user = get_object_or_404(User, id=uid, organisation=org, role=UserRole.ORG_ADMIN)
        _, invite = create_org_admin_invitation(
            organisation=org,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            invited_by=request.user,
        )
        return Response({'email': invite.email, 'status': invite.status, 'expires_at': invite.expires_at})


class ValidateInviteTokenView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        from rest_framework import serializers as drf_serializers
        from rest_framework.exceptions import NotFound
        try:
            invite = validate_invite_token(token)
        except (drf_serializers.ValidationError, NotFound) as e:
            return Response(getattr(e, 'detail', str(e)), status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'email': invite.email,
            'role': invite.role,
            'organisation_name': invite.organisation.name if invite.organisation else None,
        })


class AcceptInviteView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        from rest_framework import serializers as drf_serializers
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = accept_invitation(
                token=serializer.validated_data['token'],
                password=serializer.validated_data['password'],
            )
        except drf_serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
