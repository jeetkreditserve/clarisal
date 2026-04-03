import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole


@pytest.mark.django_db
class TestJWTEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='jwt-user@test.com',
            password='testpass123',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )

    def test_obtain_token_returns_access_and_refresh(self):
        response = self.client.post(
            '/api/auth/token/',
            {
                'email': self.user.email,
                'password': 'testpass123',
            },
            format='json',
        )

        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_refresh_token_returns_new_access(self):
        obtain = self.client.post(
            '/api/auth/token/',
            {
                'email': self.user.email,
                'password': 'testpass123',
            },
            format='json',
        )
        refresh_token = obtain.data['refresh']

        response = self.client.post(
            '/api/auth/token/refresh/',
            {
                'refresh': refresh_token,
            },
            format='json',
        )

        assert response.status_code == 200
        assert 'access' in response.data

    def test_protected_endpoint_accepts_jwt(self):
        obtain = self.client.post(
            '/api/auth/token/',
            {
                'email': self.user.email,
                'password': 'testpass123',
            },
            format='json',
        )
        access_token = obtain.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.client.get('/api/auth/me/')

        assert response.status_code == 200
        assert response.data['email'] == self.user.email
