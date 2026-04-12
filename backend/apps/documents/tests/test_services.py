from datetime import timedelta

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import AccountType, User, UserRole
from apps.audit.models import AuditLog
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.documents.services import _validate_upload, generate_download_url, list_onboarding_document_types
from apps.notifications.models import Notification
from apps.organisations.models import Organisation


@pytest.mark.django_db
def test_generate_download_url_logs_access_event(monkeypatch):
    actor = User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    control_tower = User.objects.create_superuser(
        email='ct@test.com',
        password='pass123!',
        role=UserRole.CONTROL_TOWER,
    )
    organisation = Organisation.objects.create(name='Northstar', licence_count=5, created_by=control_tower)
    employee_user = User.objects.create_user(
        email='employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
        first_name='Riya',
        last_name='Sen',
    )
    employee = organisation.employees.create(
        user=employee_user,
        employee_code='EMP001',
        designation='Analyst',
        employment_type='FULL_TIME',
        status='ACTIVE',
    )
    document = Document.objects.create(
        employee=employee,
        document_type='PAN',
        file_key='organisations/northstar/employees/EMP001/pan/test.pdf',
        file_name='pan.pdf',
        file_size=128,
        mime_type='application/pdf',
        uploaded_by=employee_user,
    )

    captured = {}

    def fake_generate_presigned_url(key, expiry=900):
        captured['key'] = key
        captured['expiry'] = expiry
        return f'https://signed.example/{key}?expires={expiry}'

    monkeypatch.setattr('apps.documents.services.generate_presigned_url', fake_generate_presigned_url)

    url = generate_download_url(document, accessed_by=actor, access_context='ORG_ADMIN')

    assert url == 'https://signed.example/organisations/northstar/employees/EMP001/pan/test.pdf?expires=900'
    assert captured == {
        'key': 'organisations/northstar/employees/EMP001/pan/test.pdf',
        'expiry': 900,
    }
    audit_log = AuditLog.objects.get(action='document.download_url_generated')
    assert audit_log.actor == actor
    assert audit_log.organisation == organisation
    assert audit_log.target_type == 'Document'
    assert audit_log.target_id == document.id
    assert audit_log.payload == {
        'document_type': 'PAN',
        'access_context': 'ORG_ADMIN',
        'expires_in_seconds': 900,
    }


@pytest.mark.parametrize(
    ('name', 'payload', 'content_type'),
    [
        ('proof.pdf', b'%PDF-1.7\n1 0 obj\n', 'application/pdf'),
        ('proof.png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR', 'image/png'),
        ('proof.jpg', b'\xff\xd8\xff\xe0\x00\x10JFIF', 'image/jpeg'),
    ],
)
def test_validate_upload_accepts_supported_magic_bytes(name, payload, content_type):
    uploaded = SimpleUploadedFile(name, payload, content_type=content_type)

    _validate_upload(uploaded)


@pytest.mark.parametrize(
    ('name', 'payload'),
    [
        ('proof.pdf', b'MZ\x90\x00\x03\x00\x00\x00'),
        ('proof.png', b'PK\x03\x04\x14\x00\x00\x00'),
    ],
)
def test_validate_upload_rejects_disguised_binary_payloads(name, payload):
    uploaded = SimpleUploadedFile(name, payload, content_type='application/octet-stream')

    with pytest.raises(ValueError, match='content does not match'):
        _validate_upload(uploaded)


@pytest.mark.django_db
def test_list_onboarding_document_types_seeds_defaults_only_once(monkeypatch):
    calls = []

    def fake_seed():
        calls.append('seeded')

    cache.clear()
    monkeypatch.setattr('apps.documents.services.ensure_default_document_types', fake_seed)

    list_onboarding_document_types()
    list_onboarding_document_types()

    assert calls == ['seeded']


@pytest.mark.django_db
def test_document_serializer_marks_document_as_expiring_soon():
    actor = User.objects.create_user(
        email='admin-expiry@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    organisation = Organisation.objects.create(name='Expiry Org', licence_count=5, created_by=actor)
    employee_user = User.objects.create_user(
        email='expiry.employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
        first_name='Riya',
        last_name='Sen',
    )
    employee = organisation.employees.create(
        user=employee_user,
        employee_code='EMP009',
        designation='Analyst',
        employment_type='FULL_TIME',
        status='ACTIVE',
    )
    document = Document.objects.create(
        employee=employee,
        document_type='PAN',
        file_key='organisations/expiry-org/employees/EMP009/pan/test.pdf',
        file_name='pan.pdf',
        file_size=128,
        mime_type='application/pdf',
        uploaded_by=employee_user,
        expiry_date=timezone.localdate() + timedelta(days=15),
        alert_days_before=30,
    )

    data = DocumentSerializer(document).data

    assert data['expiry_date'] == (timezone.localdate() + timedelta(days=15)).isoformat()
    assert data['alert_days_before'] == 30
    assert data['expires_soon'] is True


@pytest.mark.django_db
def test_send_document_expiry_alerts_notifies_expiring_document_owners():
    actor = User.objects.create_user(
        email='admin-expiry-task@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    organisation = Organisation.objects.create(name='Alerts Org', licence_count=5, created_by=actor)
    employee_user = User.objects.create_user(
        email='alerts.employee@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        is_active=True,
        first_name='Asha',
        last_name='Rao',
    )
    employee = organisation.employees.create(
        user=employee_user,
        employee_code='EMP010',
        designation='Analyst',
        employment_type='FULL_TIME',
        status='ACTIVE',
    )
    Document.objects.create(
        employee=employee,
        document_type='PASSPORT',
        file_key='organisations/alerts-org/employees/EMP010/passport/passport.pdf',
        file_name='passport.pdf',
        file_size=128,
        mime_type='application/pdf',
        uploaded_by=employee_user,
        expiry_date=timezone.localdate() + timedelta(days=10),
        alert_days_before=30,
    )
    Document.objects.create(
        employee=employee,
        document_type='WORK_PERMIT',
        file_key='organisations/alerts-org/employees/EMP010/work-permit/work-permit.pdf',
        file_name='work-permit.pdf',
        file_size=128,
        mime_type='application/pdf',
        uploaded_by=employee_user,
        expiry_date=timezone.localdate() + timedelta(days=5),
        alert_days_before=30,
    )

    from apps.documents.tasks import send_document_expiry_alerts

    sent = send_document_expiry_alerts()

    assert sent == 2
    assert Notification.objects.filter(recipient=employee_user).count() == 2
