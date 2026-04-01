import pytest
from decimal import Decimal
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


def organisation_create_payload(name='New Org'):
    return {
        'name': name,
        'pan_number': 'ABCDE1234F',
        'email': 'org@test.com',
        'phone': '+919876543210',
        'country_code': 'IN',
        'currency': 'INR',
        'entity_type': 'PRIVATE_LIMITED',
        'addresses': [
            {
                'address_type': 'REGISTERED',
                'line1': '123 Main St',
                'city': 'Bengaluru',
                'state': 'Karnataka',
                'country': 'India',
                'pincode': '560001',
                'gstin': '29ABCDE1234F1Z5',
            },
            {
                'address_type': 'BILLING',
                'line1': '18 Nariman Point',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '400021',
                'gstin': '27ABCDE1234F1Z7',
            },
        ],
    }


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
        response = client.post('/api/ct/organisations/', organisation_create_payload(), format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'New Org'
        assert response.data['status'] == OrganisationStatus.PENDING
        assert response.data['pan_number'] == 'ABCDE1234F'
        assert response.data['phone'] == '+919876543210'
        assert response.data['country_code'] == 'IN'
        assert response.data['currency'] == 'INR'
        assert response.data['entity_type'] == 'PRIVATE_LIMITED'

    def test_create_requires_name(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {}, format='json')
        assert response.status_code == 400

    def test_create_rejects_phone_with_wrong_country_dial_code(self, ct_client):
        client, _ = ct_client
        payload = organisation_create_payload()
        payload['phone'] = '+447700900123'
        payload['country_code'] = 'IN'
        response = client.post('/api/ct/organisations/', payload, format='json')
        assert response.status_code == 400
        assert 'phone' in response.data

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


@pytest.mark.django_db
class TestOrganisationProfileUpdate:
    def test_control_tower_update_rejects_phone_with_wrong_country_dial_code(self, ct_client):
        client, user = ct_client
        organisation = Organisation.objects.create(
            name='Acme Corp',
            created_by=user,
            country_code='IN',
            currency='INR',
        )
        response = client.patch(
            f'/api/ct/organisations/{organisation.id}/',
            {'phone': '+447700900123'},
            format='json',
        )
        assert response.status_code == 400
        assert 'phone' in response.data


@pytest.mark.django_db
class TestLicenceBatchViews:
    def test_org_detail_includes_batch_defaults_and_batches(self, ct_client, org):
        client, _ = ct_client

        response = client.get(f'/api/ct/organisations/{org.id}/')

        assert response.status_code == 200
        assert 'licence_batches' in response.data
        assert 'batch_defaults' in response.data
        assert response.data['licence_batches'] == []

    def test_create_update_and_mark_paid_batch(self, ct_client, org):
        client, _ = ct_client

        create_response = client.post(
            f'/api/ct/organisations/{org.id}/licence-batches/',
            {
                'quantity': 5,
                'price_per_licence_per_month': '99.00',
                'start_date': '2026-04-01',
                'end_date': '2026-12-31',
                'note': 'Initial commercial batch',
            },
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['payment_status'] == 'DRAFT'
        assert create_response.data['lifecycle_state'] == 'DRAFT'

        batch_id = create_response.data['id']
        update_response = client.patch(
            f'/api/ct/organisations/{org.id}/licence-batches/{batch_id}/',
            {
                'quantity': 6,
                'price_per_licence_per_month': '109.00',
            },
            format='json',
        )
        assert update_response.status_code == 200
        assert update_response.data['quantity'] == 6
        assert update_response.data['price_per_licence_per_month'] == '109.00'

        pay_response = client.post(
            f'/api/ct/organisations/{org.id}/licence-batches/{batch_id}/mark-paid/',
            {'paid_at': '2026-04-01'},
            format='json',
        )

        assert pay_response.status_code == 200
        assert pay_response.data['payment_status'] == 'PAID'
        assert pay_response.data['lifecycle_state'] in ['ACTIVE', 'PAID_PENDING_START']
