from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organisations.models import OrganisationAccessState, OrganisationBillingStatus

from .models import AccountType
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
    WorkspaceSwitchSerializer,
)
from .services import (
    confirm_password_reset,
    create_password_reset_request,
    validate_password_reset_token,
)
from .workspaces import (
    get_active_admin_organisation,
    get_active_employee,
    get_workspace_state,
    initialize_workforce_workspace,
    set_active_admin_organisation,
    set_active_employee_workspace,
)


def _serialize_user(user, request):
    return UserSerializer(user, context={'request': request}).data


def _complete_login(request, user):
    login(request, user)
    request.session.cycle_key()
    if user.account_type == AccountType.WORKFORCE:
        initialize_workforce_workspace(request, user)
    get_token(request)
    return Response({'user': _serialize_user(user, request)}, status=status.HTTP_200_OK)


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class WorkforceLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            account_type=AccountType.WORKFORCE,
        )
        if not user or not user.is_active:
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        workspace_state = get_workspace_state(user, request)
        if not workspace_state.admin_memberships and not workspace_state.employee_records:
            return Response({'error': 'No workforce access is configured for this account.'}, status=status.HTTP_403_FORBIDDEN)

        initialize_workforce_workspace(request, user)

        active_org = get_active_admin_organisation(request, user)
        if active_org is None:
            active_employee = get_active_employee(request, user)
            active_org = active_employee.organisation if active_employee else None

        if active_org and (
            active_org.billing_status != OrganisationBillingStatus.PAID
            or active_org.access_state != OrganisationAccessState.ACTIVE
        ):
            return Response(
                {'error': 'Your organisation is not active yet. Please contact your administrator.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return _complete_login(request, user)


class ControlTowerLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            account_type=AccountType.CONTROL_TOWER,
        )
        if not user or not user.is_active:
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_staff:
            return Response({'error': 'This account does not have Control Tower access.'}, status=status.HTTP_403_FORBIDDEN)

        return _complete_login(request, user)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class WorkspaceSelectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.account_type != AccountType.WORKFORCE:
            return Response({'error': 'Workspace switching is only available for workforce accounts.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WorkspaceSwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            if serializer.validated_data['workspace_kind'] == 'ADMIN':
                set_active_admin_organisation(request, request.user, serializer.validated_data['organisation_id'])
            else:
                set_active_employee_workspace(request, request.user, serializer.validated_data['organisation_id'])
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'user': _serialize_user(request.user, request)}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    account_type = AccountType.WORKFORCE

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        create_password_reset_request(
            serializer.validated_data['email'],
            account_type=self.account_type,
            requested_by_ip=request.META.get('REMOTE_ADDR'),
        )
        return Response(
            {'detail': 'If an account exists, a password reset link has been sent.'},
            status=status.HTTP_202_ACCEPTED,
        )


class ControlTowerPasswordResetRequestView(PasswordResetRequestView):
    account_type = AccountType.CONTROL_TOWER


class PasswordResetValidateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        try:
            reset_token = validate_password_reset_token(token)
        except Exception as exc:  # noqa: BLE001 - keep response shape compact
            detail = getattr(exc, 'detail', {'token': 'Invalid password reset link.'})
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'email': reset_token.user.email,
                'account_type': reset_token.user.account_type,
            }
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = confirm_password_reset(
                serializer.validated_data['token'],
                serializer.validated_data['password'],
            )
        except Exception as exc:  # noqa: BLE001 - keep response shape compact
            detail = getattr(exc, 'detail', {'token': 'Invalid password reset link.'})
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)

        return _complete_login(request, user)
