import io
import zipfile

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.audit.models import AuditLog
from apps.employees.models import Employee
from apps.organisations.models import (
    Organisation,
    OrganisationStateTransition,
    OrganisationStatus,
    TenantDataExportStatus,
    TenantDataExportType,
)
from apps.organisations.services import (
    create_organisation,
    generate_tenant_data_export_batch,
    generate_tenant_data_export_download_url,
    get_ct_dashboard_stats,
    request_tenant_data_export,
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


@pytest.mark.django_db
class TestTenantDataExportServices:
    def test_generate_tenant_data_export_batch_uploads_zip_and_download_url(self, ct_user, pending_org, monkeypatch):
        workforce_user = User.objects.create_user(
            email='export.employee@test.com',
            password='pass123!',
            account_type=AccountType.WORKFORCE,
            role=UserRole.EMPLOYEE,
            organisation=pending_org,
            is_active=True,
        )
        Employee.objects.create(
            organisation=pending_org,
            user=workforce_user,
            employee_code='EMP-EXPORT-1',
            designation='Analyst',
            status='ACTIVE',
        )
        uploaded = {}

        def fake_upload(file_obj, key, content_type):
            uploaded['payload'] = file_obj.getvalue()
            uploaded['key'] = key
            uploaded['content_type'] = content_type

        monkeypatch.setattr('apps.organisations.services.upload_file', fake_upload)
        monkeypatch.setattr(
            'apps.organisations.services.generate_presigned_url',
            lambda key, expiry=900: f'https://downloads.test/{key}?expiry={expiry}',
        )

        batch = request_tenant_data_export(
            pending_org,
            export_type=TenantDataExportType.EMPLOYEES,
            requested_by=ct_user,
        )

        generated = generate_tenant_data_export_batch(batch)
        download_url = generate_tenant_data_export_download_url(generated, actor=ct_user)

        assert generated.status == TenantDataExportStatus.COMPLETED
        assert generated.metadata['row_count'] == 1
        assert uploaded['content_type'] == 'application/zip'
        assert generated.artifact_key == uploaded['key']
        assert download_url == f'https://downloads.test/{generated.artifact_key}?expiry=900'
        with zipfile.ZipFile(io.BytesIO(uploaded['payload'])) as archive:
            exported_csv = archive.read('employees.csv').decode('utf-8')
        assert 'export.employee@test.com' in exported_csv
        assert 'EMP-EXPORT-1' in exported_csv

    def test_generate_tenant_data_export_batch_marks_failure_when_upload_fails(self, ct_user, pending_org, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError('upload failed')

        monkeypatch.setattr('apps.organisations.services.upload_file', boom)

        batch = request_tenant_data_export(
            pending_org,
            export_type=TenantDataExportType.EMPLOYEES,
            requested_by=ct_user,
        )

        generated = generate_tenant_data_export_batch(batch)

        assert generated.status == TenantDataExportStatus.FAILED
        assert generated.failure_reason == 'upload failed'
