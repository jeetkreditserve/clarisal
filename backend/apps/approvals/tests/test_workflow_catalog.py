import pytest

from apps.accounts.models import User, UserRole
from apps.approvals.models import ApprovalRequestKind, ApprovalWorkflow
from apps.approvals.services import ensure_default_workflow_configured, get_workflow_readiness
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)


@pytest.fixture
def organisation(db):
    owner = User.objects.create_user(
        email='catalog-owner@test.com',
        password='pass123!',  # pragma: allowlist secret
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    return Organisation.objects.create(
        name='Catalog Org',
        created_by=owner,
        primary_admin_user=owner,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.mark.django_db
def test_catalog_covers_request_kind_enum_and_required_defaults():
    from apps.approvals.catalog import APPROVAL_REQUEST_KIND_CATALOG, get_required_default_request_kinds

    enum_kinds = {choice.value for choice in ApprovalRequestKind}

    assert set(APPROVAL_REQUEST_KIND_CATALOG) == enum_kinds
    assert set(get_required_default_request_kinds()) == enum_kinds
    assert len(get_required_default_request_kinds()) == 9


@pytest.mark.django_db
def test_readiness_requires_all_catalog_request_kinds(organisation):
    ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Default Leave',
        is_default=True,
        default_request_kind=ApprovalRequestKind.LEAVE,
        is_active=True,
    )

    readiness = get_workflow_readiness(organisation)
    required = {item['kind'] for item in readiness if item['requires_default_workflow']}
    leave_row = next(item for item in readiness if item['kind'] == ApprovalRequestKind.LEAVE)
    promotion_row = next(item for item in readiness if item['kind'] == ApprovalRequestKind.PROMOTION)

    assert required == {choice.value for choice in ApprovalRequestKind}
    assert leave_row['ready'] is True
    assert leave_row['has_default_workflow'] is True
    assert promotion_row['ready'] is False
    assert promotion_row['has_default_workflow'] is False


@pytest.mark.django_db
def test_default_workflow_guard_requires_every_catalog_kind(organisation):
    for request_kind in ApprovalRequestKind:
        if request_kind == ApprovalRequestKind.TRANSFER:
            continue
        ApprovalWorkflow.objects.create(
            organisation=organisation,
            name=f'Default {request_kind}',
            is_default=True,
            default_request_kind=request_kind,
            is_active=True,
        )

    with pytest.raises(ValueError, match='default approval workflow'):
        ensure_default_workflow_configured(organisation)

    ApprovalWorkflow.objects.create(
        organisation=organisation,
        name='Default transfer',
        is_default=True,
        default_request_kind=ApprovalRequestKind.TRANSFER,
        is_active=True,
    )

    ensure_default_workflow_configured(organisation)
