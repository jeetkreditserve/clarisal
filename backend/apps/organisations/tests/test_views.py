import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import AccountType, User, UserRole
from apps.organisations.models import (
    Organisation,
    OrganisationAddress,
    OrganisationAddressType,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationNote,
    OrganisationStatus,
)


def organisation_create_payload(name='New Org'):
    return {
        'name': name,
        'pan_number': 'ABCDE1234F',
        'country_code': 'IN',
        'currency': 'INR',
        'entity_type': 'PRIVATE_LIMITED',
        'primary_admin': {
            'first_name': 'Aditi',
            'last_name': 'Rao',
            'email': 'admin@test.com',
            'phone': '+919876543210',
        },
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
    client.force_authenticate(user=user)
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
        assert response.data['phone'] == ''
        assert response.data['country_code'] == 'IN'
        assert response.data['currency'] == 'INR'
        assert response.data['entity_type'] == 'PRIVATE_LIMITED'
        assert response.data['bootstrap_admin']['email'] == 'admin@test.com'

    def test_create_requires_name(self, ct_client):
        client, _ = ct_client
        response = client.post('/api/ct/organisations/', {}, format='json')
        assert response.status_code == 400

    def test_create_rejects_phone_with_wrong_country_dial_code(self, ct_client):
        client, _ = ct_client
        payload = organisation_create_payload()
        payload['primary_admin']['phone'] = '+447700900123'
        payload['country_code'] = 'IN'
        response = client.post('/api/ct/organisations/', payload, format='json')
        assert response.status_code == 400
        assert 'primary_admin' in response.data

    def test_create_returns_400_for_duplicate_gstin(self, ct_client):
        client, _ = ct_client
        first_response = client.post('/api/ct/organisations/', organisation_create_payload(name='Existing Org'), format='json')
        assert first_response.status_code == 201
        payload = organisation_create_payload(name='Conflicting Org')
        payload['addresses'][0]['gstin'] = '29ABCDE1234F1Z5'
        response = client.post('/api/ct/organisations/', payload, format='json')
        assert response.status_code == 400
        assert 'error' in response.data

    def test_create_reuses_existing_person_for_bootstrap_admin_email(self, ct_client):
        client, _ = ct_client
        user = User.objects.create_user(
            email='admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )

        response = client.post('/api/ct/organisations/', organisation_create_payload(name='Shared Person Org'), format='json')

        assert response.status_code == 201
        organisation = Organisation.objects.get(id=response.data['id'])
        assert organisation.bootstrap_admin.person_id == user.person_id

    def test_create_rejects_email_and_phone_that_resolve_to_different_people(self, ct_client):
        client, _ = ct_client
        User.objects.create_user(
            email='someoneelse@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        User.objects.create_user(
            email='new-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        payload = organisation_create_payload(name='Phone Conflict Org')
        payload['primary_admin']['email'] = 'new-admin@test.com'
        payload['primary_admin']['phone'] = '+919900001111'
        conflicting_user = User.objects.get(email='someoneelse@test.com', account_type=AccountType.WORKFORCE)
        conflicting_user.person.phone_numbers.create(
            e164_number='+919900001111',
            display_number='+91 99000 01111',
            kind='WORK',
            is_primary=True,
        )

        response = client.post('/api/ct/organisations/', payload, format='json')

        assert response.status_code == 400
        assert 'error' in response.data

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


@pytest.mark.django_db
class TestCtOrganisationDetailTabsSupport:
    def test_org_detail_includes_tab_summary_counts(self, ct_client, org):
        client, ct_user = ct_client
        response = client.get(f'/api/ct/organisations/{org.id}/')

        assert response.status_code == 200
        assert 'admin_count' in response.data
        assert 'employee_count' in response.data
        assert 'holiday_calendar_count' in response.data
        assert 'note_count' in response.data
        assert 'configuration_summary' in response.data

    def test_ct_can_create_and_list_notes(self, ct_client, org):
        client, ct_user = ct_client

        create_response = client.post(
            f'/api/ct/organisations/{org.id}/notes/',
            {'body': 'Payment follow-up scheduled with finance.'},
            format='json',
        )

        assert create_response.status_code == 201
        assert create_response.data['body'] == 'Payment follow-up scheduled with finance.'
        assert create_response.data['created_by']['email'] == ct_user.email
        assert OrganisationNote.objects.filter(organisation=org).count() == 1

        list_response = client.get(f'/api/ct/organisations/{org.id}/notes/')

        assert list_response.status_code == 200
        assert len(list_response.data) == 1
        assert list_response.data[0]['created_by']['email'] == ct_user.email
        assert list_response.data[0]['created_at']

    def test_ct_can_list_employees_for_org(self, ct_client, org):
        client, _ = ct_client
        workforce_user = User.objects.create_user(
            email='employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            is_active=True,
            first_name='Riya',
            last_name='Sen',
        )
        from apps.employees.models import Employee

        employee = Employee.objects.create(
            organisation=org,
            user=workforce_user,
            designation='Analyst',
            employment_type='FULL_TIME',
            status='ACTIVE',
        )

        response = client.get(f'/api/ct/organisations/{org.id}/employees/')

        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['email'] == 'employee@test.com'

        detail_response = client.get(f'/api/ct/organisations/{org.id}/employees/{employee.id}/')
        assert detail_response.status_code == 200
        assert detail_response.data['full_name'] == 'Riya Sen'

    def test_ct_can_manage_holiday_calendars(self, ct_client, org):
        client, _ = ct_client

        create_response = client.post(
            f'/api/ct/organisations/{org.id}/holiday-calendars/',
            {
                'name': 'FY 2026 Calendar',
                'year': 2026,
                'description': '',
                'is_default': True,
                'holidays': [
                    {
                        'name': 'Founders Day',
                        'holiday_date': '2026-07-15',
                        'classification': 'COMPANY',
                        'session': 'FULL_DAY',
                        'description': '',
                    }
                ],
                'location_ids': [],
            },
            format='json',
        )

        assert create_response.status_code == 201
        calendar_id = create_response.data['id']

        publish_response = client.post(f'/api/ct/organisations/{org.id}/holiday-calendars/{calendar_id}/publish/')
        assert publish_response.status_code == 200
        assert publish_response.data['status'] == 'PUBLISHED'

    def test_ct_can_fetch_configuration_snapshot(self, ct_client, org):
        client, _ = ct_client

        response = client.get(f'/api/ct/organisations/{org.id}/configuration/')

        assert response.status_code == 200
        assert set(response.data.keys()) == {
            'locations',
            'departments',
            'leave_cycles',
            'leave_plans',
            'on_duty_policies',
            'approval_workflows',
            'notices',
        }


@pytest.mark.django_db
class TestCtOrganisationEditingParity:
    def test_ct_admin_list_includes_invited_and_inactive_memberships(self, ct_client, org):
        client, _ = ct_client
        invited_user = User.objects.create_user(
            email='pending-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=False,
        )
        inactive_user = User.objects.create_user(
            email='inactive-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            user=invited_user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INVITED,
        )
        OrganisationMembership.objects.create(
            user=inactive_user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INACTIVE,
        )

        response = client.get(f'/api/ct/organisations/{org.id}/admins/')

        assert response.status_code == 200
        assert {item['membership_status'] for item in response.data} >= {'INVITED', 'INACTIVE'}

    def test_ct_can_deactivate_and_reactivate_additional_org_admin(self, ct_client, org):
        client, ct_user = ct_client
        primary = User.objects.create_user(
            email='primary@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        secondary = User.objects.create_user(
            email='secondary@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        org.primary_admin_user = primary
        org.save(update_fields=['primary_admin_user', 'modified_at'])
        OrganisationMembership.objects.create(
            user=primary,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
            invited_by=ct_user,
        )
        OrganisationMembership.objects.create(
            user=secondary,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
            invited_by=ct_user,
        )

        deactivate_response = client.post(f'/api/ct/organisations/{org.id}/admins/{secondary.id}/deactivate/')
        reactivate_response = client.post(f'/api/ct/organisations/{org.id}/admins/{secondary.id}/reactivate/')

        assert deactivate_response.status_code == 200
        assert deactivate_response.data['membership_status'] == 'INACTIVE'
        assert reactivate_response.status_code == 200
        assert reactivate_response.data['membership_status'] == 'ACTIVE'

    def test_ct_can_revoke_pending_admin_invite(self, ct_client, org):
        client, ct_user = ct_client
        pending_user = User.objects.create_user(
            email='revoke-admin@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.ORG_ADMIN,
            is_active=False,
        )
        OrganisationMembership.objects.create(
            user=pending_user,
            organisation=org,
            is_org_admin=True,
            status=OrganisationMembershipStatus.INVITED,
            invited_by=ct_user,
        )

        response = client.post(f'/api/ct/organisations/{org.id}/admins/{pending_user.id}/revoke-pending/')

        assert response.status_code == 200
        assert response.data['membership_status'] == 'REVOKED'

    def test_ct_can_manage_locations_and_departments(self, ct_client, org):
        client, _ = ct_client
        registered_address = OrganisationAddress.objects.create(
            organisation=org,
            address_type=OrganisationAddressType.REGISTERED,
            label='Registered Office',
            line1='1 Residency Road',
            city='Bengaluru',
            state='Karnataka',
            state_code='KA',
            country='India',
            country_code='IN',
            pincode='560001',
            is_active=True,
        )
        OrganisationAddress.objects.create(
            organisation=org,
            address_type=OrganisationAddressType.BILLING,
            label='Billing Address',
            line1='2 MG Road',
            city='Bengaluru',
            state='Karnataka',
            state_code='KA',
            country='India',
            country_code='IN',
            pincode='560002',
            gstin='29ABCDE1234F1Z5',
            is_active=True,
        )

        location_response = client.post(
            f'/api/ct/organisations/{org.id}/locations/',
            {'name': 'HQ', 'organisation_address_id': str(registered_address.id), 'is_remote': False},
            format='json',
        )
        department_response = client.post(
            f'/api/ct/organisations/{org.id}/departments/',
            {'name': 'Engineering', 'description': 'Product engineering'},
            format='json',
        )

        assert location_response.status_code == 201
        assert location_response.data['name'] == 'HQ'
        assert department_response.status_code == 201
        assert department_response.data['name'] == 'Engineering'

    def test_ct_can_manage_leave_and_notice_configuration(self, ct_client, org):
        client, _ = ct_client
        cycle_response = client.post(
            f'/api/ct/organisations/{org.id}/leave-cycles/',
            {
                'name': 'Calendar Year',
                'cycle_type': 'CALENDAR_YEAR',
                'start_month': 1,
                'start_day': 1,
                'is_default': True,
                'is_active': True,
            },
            format='json',
        )
        assert cycle_response.status_code == 201

        plan_response = client.post(
            f'/api/ct/organisations/{org.id}/leave-plans/',
            {
                'leave_cycle_id': cycle_response.data['id'],
                'name': 'General Plan',
                'description': '',
                'is_default': True,
                'is_active': True,
                'priority': 100,
                'leave_types': [
                    {
                        'code': 'CL',
                        'name': 'Casual Leave',
                        'annual_entitlement': '12.00',
                        'credit_frequency': 'MONTHLY',
                    }
                ],
                'rules': [],
            },
            format='json',
        )
        policy_response = client.post(
            f'/api/ct/organisations/{org.id}/on-duty-policies/',
            {
                'name': 'Default Policy',
                'description': '',
                'is_default': True,
                'is_active': True,
                'allow_half_day': True,
                'allow_time_range': True,
                'requires_attachment': False,
            },
            format='json',
        )
        workflow_response = client.post(
            f'/api/ct/organisations/{org.id}/approval-workflows/',
            {
                'name': 'Default Workflow',
                'description': '',
                'is_default': True,
                'default_request_kind': 'LEAVE',
                'is_active': True,
                'rules': [{'name': 'Default leave rule', 'request_kind': 'LEAVE', 'priority': 100, 'is_active': True}],
                'stages': [
                    {
                        'name': 'Primary admin approval',
                        'sequence': 1,
                        'mode': 'ALL',
                        'fallback_type': 'PRIMARY_ORG_ADMIN',
                        'approvers': [{'approver_type': 'PRIMARY_ORG_ADMIN'}],
                    }
                ],
            },
            format='json',
        )
        notice_response = client.post(
            f'/api/ct/organisations/{org.id}/notices/',
            {
                'title': 'Office advisory',
                'body': 'Quarter-end blackout window',
                'audience_type': 'ALL_EMPLOYEES',
                'status': 'DRAFT',
            },
            format='json',
        )

        assert plan_response.status_code == 201
        assert policy_response.status_code == 201
        assert workflow_response.status_code == 201
        assert notice_response.status_code == 201

        publish_response = client.post(
            f"/api/ct/organisations/{org.id}/notices/{notice_response.data['id']}/publish/"
        )
        assert publish_response.status_code == 200
        assert publish_response.data['status'] == 'PUBLISHED'
