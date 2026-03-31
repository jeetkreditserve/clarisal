from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

from .models import AccountType

UserModel = get_user_model()


class AudienceEmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, account_type=None, **kwargs):
        email = kwargs.get(UserModel.USERNAME_FIELD, username)
        if not email or not password:
            return None

        resolved_account_type = account_type or self._resolve_account_type(request)

        try:
            user = UserModel.objects.get(email__iexact=email, account_type=resolved_account_type)
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        return getattr(user, 'is_active', False)

    def _resolve_account_type(self, request):
        if request and request.path.startswith('/admin/'):
            return AccountType.CONTROL_TOWER
        return AccountType.WORKFORCE
