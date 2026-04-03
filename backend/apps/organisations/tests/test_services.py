import pytest

from apps.accounts.models import User, UserRole
from apps.audit.models import AuditLog
from apps.organisations.models import Organisation, OrganisationStateTransition, OrganisationStatus
from apps.organisations.services import (
    create_organisation,
    get_ct_dashboard_stats,
    transition_organisation_state,
    update_licence_count,
)


def organisation_addresses():
    return [
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
    ]


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@test.com', password='pass123!',
        first_name='Control', last_name='Tower',
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def pending_org(ct_user):
    return Organisation.objects.create(
        name='Acme Corp', licence_count=10, created_by=ct_user,
    )


@pytest.mark.django_db
class TestCreateOrganisation:
    def test_creates_with_pending_status(self, ct_user):
        org = create_organisation(
            name='Test Corp',
            licence_count=5,
            created_by=ct_user,
            pan_number='ABCDE1234F',
            primary_admin={
                'first_name': 'Alice',
                'last_name': 'Smith',
                'email': 'admin@testcorp.com',
                'phone': '+919999999999',
            },
            addresses=organisation_addresses(),
        )
        assert org.status == OrganisationStatus.PENDING
        assert org.name == 'Test Corp'
        assert org.licence_count == 5
        assert org.pan_number == 'ABCDE1234F'
        assert org.addresses.count() == 2

    def test_auto_generates_slug(self, ct_user):
        org = create_organisation(
            name='Hello World Corp',
            licence_count=1,
            created_by=ct_user,
            pan_number='ABCDE1234F',
            primary_admin={
                'first_name': 'Alice',
                'last_name': 'Smith',
                'email': 'admin@helloworld.com',
                'phone': '+919999999999',
            },
            addresses=organisation_addresses(),
        )
        assert 'hello' in org.slug
        assert org.slug != ''

    def test_stores_optional_fields(self, ct_user):
        org = create_organisation(
            name='Test', licence_count=1, created_by=ct_user,
            pan_number='ABCDE1234F',
            addresses=organisation_addresses(),
            primary_admin={
                'first_name': 'Aditi',
                'last_name': 'Rao',
                'email': 'admin@test.com',
                'phone': '+919999999999',
            },
            country_code='IN', currency='INR', entity_type='PRIVATE_LIMITED',
        )
        assert org.address == '123 Main St'
        assert org.email == ''
        assert org.phone == ''
        assert org.entity_type == 'PRIVATE_LIMITED'
        assert org.bootstrap_admin.email == 'admin@test.com'

    def test_audit_log_redacts_pan_number_in_creation_payload(self, ct_user):
        create_organisation(
            name='Audit Safe Corp',
            licence_count=1,
            created_by=ct_user,
            pan_number='ABCDE1234F',
            primary_admin={
                'first_name': 'Alice',
                'last_name': 'Smith',
                'email': 'admin@auditsafe.com',
                'phone': '+919999999999',
            },
            addresses=organisation_addresses(),
        )

        audit_log = AuditLog.objects.get(action='organisation.created')
        assert audit_log.payload['pan_number'] == '[REDACTED]'
        assert audit_log.payload['primary_admin_email'] == 'admin@auditsafe.com'


@pytest.mark.django_db
class TestTransitionOrganisationState:
    def test_pending_to_paid_succeeds(self, ct_user, pending_org):
        result = transition_organisation_state(pending_org, OrganisationStatus.PAID, ct_user)
        assert result.status == OrganisationStatus.PAID
        pending_org.refresh_from_db()
        assert pending_org.status == OrganisationStatus.PAID

    def test_creates_state_transition_record(self, ct_user, pending_org):
        transition_organisation_state(pending_org, OrganisationStatus.PAID, ct_user, note='Payment received')
        t = OrganisationStateTransition.objects.get(organisation=pending_org)
        assert t.from_status == OrganisationStatus.PENDING
        assert t.to_status == OrganisationStatus.PAID
        assert t.note == 'Payment received'
        assert t.transitioned_by == ct_user

    def test_invalid_transition_raises_value_error(self, ct_user, pending_org):
        with pytest.raises(ValueError, match='Cannot transition'):
            transition_organisation_state(pending_org, OrganisationStatus.ACTIVE, ct_user)

    def test_paid_to_active_succeeds(self, ct_user, pending_org):
        pending_org.status = OrganisationStatus.PAID
        pending_org.save()
        result = transition_organisation_state(pending_org, OrganisationStatus.ACTIVE, ct_user)
        assert result.status == OrganisationStatus.ACTIVE

    def test_active_to_suspended_succeeds(self, ct_user, pending_org):
        pending_org.status = OrganisationStatus.ACTIVE
        pending_org.save()
        result = transition_organisation_state(pending_org, OrganisationStatus.SUSPENDED, ct_user)
        assert result.status == OrganisationStatus.SUSPENDED

    def test_suspended_to_active_succeeds(self, ct_user, pending_org):
        pending_org.status = OrganisationStatus.SUSPENDED
        pending_org.save()
        result = transition_organisation_state(pending_org, OrganisationStatus.ACTIVE, ct_user)
        assert result.status == OrganisationStatus.ACTIVE


@pytest.mark.django_db
class TestUpdateLicenceCount:
    def test_updates_licence_count(self, ct_user, pending_org):
        result = update_licence_count(pending_org, 25)
        assert result.licence_count == 25
        pending_org.refresh_from_db()
        assert pending_org.licence_count == 25


@pytest.mark.django_db
class TestGetCtDashboardStats:
    def test_returns_correct_counts(self, ct_user):
        Organisation.objects.create(name='Org1', licence_count=5, created_by=ct_user, status=OrganisationStatus.ACTIVE)
        Organisation.objects.create(name='Org2', licence_count=5, created_by=ct_user, status=OrganisationStatus.PENDING)
        stats = get_ct_dashboard_stats()
        assert stats['total_organisations'] == 2
        assert stats['active_organisations'] == 1
        assert stats['pending_organisations'] == 1
        assert stats['paid_organisations'] == 0
        assert stats['suspended_organisations'] == 0
        assert stats['total_employees'] == 0
