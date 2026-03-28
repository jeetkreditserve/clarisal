import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ct_user(db):
    return User.objects.create_user(
        email='ct@calrisal.com',
        password='TestPass@123',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_tokens_and_user(self, api_client, ct_user):
        response = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['role'] == UserRole.CONTROL_TOWER
        assert data['user']['email'] == 'ct@calrisal.com'

    def test_login_wrong_password_returns_401(self, api_client, ct_user):
        response = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'wrongpassword',
        }, format='json')
        assert response.status_code == 401

    def test_login_inactive_user_returns_401(self, api_client, db):
        User.objects.create_user(
            email='inactive@calrisal.com',
            password='TestPass@123',
            is_active=False,
        )
        response = api_client.post('/api/auth/login/', {
            'email': 'inactive@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        assert response.status_code == 401

    def test_me_returns_current_user(self, api_client, ct_user):
        login = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 200
        assert response.json()['email'] == 'ct@calrisal.com'

    def test_logout_blacklists_refresh_token(self, api_client, ct_user):
        login = api_client.post('/api/auth/login/', {
            'email': 'ct@calrisal.com',
            'password': 'TestPass@123',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        response = api_client.post('/api/auth/logout/', {
            'refresh': login.json()['refresh']
        }, format='json')
        assert response.status_code == 204
        # Attempt to refresh with blacklisted token
        refresh_response = api_client.post('/api/auth/refresh/', {
            'refresh': login.json()['refresh']
        }, format='json')
        assert refresh_response.status_code == 401
