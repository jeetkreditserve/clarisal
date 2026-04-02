import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.audit.models import AuditLog
from apps.documents.models import Document
from apps.documents.services import generate_download_url
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
