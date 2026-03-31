import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)


@pytest.fixture
def ct_client(db):
    user = User.objects.create_superuser(
        email='ct@test.com', password='pass123!',
        first_name='Control', last_name='Tower', role=UserRole.CONTROL_TOWER,
    )
    client = APIClient()
    client.post('/api/auth/control-tower/login/', {'email': 'ct@test.com', 'password': 'pass123!'}, format='json')
    return client, user


@pytest.fixture
def org(db):
    ct_user = User.objects.create_superuser(
        email='ct2@test.com', password='pass123!', role=UserRole.CONTROL_TOWER,
    )
    return Organisation.objects.create(name='Test Corp', licence_count=10, created_by=ct_user)


@pytest.mark.django_db
class TestOrganisationListCreate:
    def test_list_returns_paginated_orgs(self, ct_client, org):
        client, _ = ct_client
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_create_org(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {
            'name': 'New Org', 'licence_count': 5, 'email': 'org@test.com',
        }, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'New Org'
        assert response.data['status'] == OrganisationStatus.PENDING

    def test_create_requires_name_and_licence_count(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {'name': 'Org'}, format='json')
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 403

    def test_non_ct_user_returns_403(self, db):
        ct = User.objects.create_superuser(email='seed@test.com', password='pass', role=UserRole.CONTROL_TOWER)
        org = Organisation.objects.create(
            name='Org',
            licence_count=5,
            created_by=ct,
            status=OrganisationStatus.ACTIVE,
            billing_status=OrganisationBillingStatus.PAID,
            access_state=OrganisationAccessState.ACTIVE,
        )
        user = User.objects.create_user(email='org@test.com', password='pass', role=UserRole.ORG_ADMIN, is_active=True)
        OrganisationMembership.objects.create(
            user=user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        client = APIClient()
        client.post('/api/auth/login/', {'email': 'org@test.com', 'password': 'pass'}, format='json')
        response = client.get('/api/ct/organisations/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestOrganisationActivate:
    def test_pending_to_paid(self, ct_client, org):
        client, _ = ct_client
        response = client.post(f'/api/ct/organisations/{org.id}/activate/')
        assert response.status_code == 200
        assert response.data['status'] == OrganisationStatus.PAID

    def test_invalid_transition_returns_400(self, ct_client, org):
        client, _ = ct_client
        # PENDING cannot go to SUSPENDED
        response = client.post(f'/api/ct/organisations/{org.id}/suspend/')
        assert response.status_code == 400
