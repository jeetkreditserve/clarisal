import pytest

from apps.accounts.models import User, UserRole
from apps.organisations.models import Organisation, OrganisationStatus
from apps.organisations.tasks import aggregate_daily_usage_stats, generate_tenant_data_export


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct-task@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.CONTROL_TOWER,
    )


@pytest.mark.django_db
def test_aggregate_daily_usage_stats_keeps_processing_after_one_org_fails(ct_user, monkeypatch):
    org_one = Organisation.objects.create(name='Org One', created_by=ct_user, status=OrganisationStatus.ACTIVE)
    org_two = Organisation.objects.create(name='Org Two', created_by=ct_user, status=OrganisationStatus.ACTIVE)
    org_three = Organisation.objects.create(name='Org Three', created_by=ct_user, status=OrganisationStatus.ACTIVE)

    processed = []

    def fake_aggregate(org):
        processed.append(org.name)
        if org == org_two:
            raise ValueError('boom')

    monkeypatch.setattr('apps.organisations.tasks.aggregate_org_usage_stat', fake_aggregate)

    result = aggregate_daily_usage_stats()

    assert result == 3
    assert processed == [org_one.name, org_two.name, org_three.name]


def test_generate_tenant_data_export_uses_retry_policy():
    assert getattr(generate_tenant_data_export, 'max_retries', None) == 3
    assert getattr(generate_tenant_data_export, 'retry_backoff', None) is True
    assert getattr(generate_tenant_data_export, 'retry_backoff_max', None) == 300
    assert Exception in getattr(generate_tenant_data_export, 'autoretry_for', ())
