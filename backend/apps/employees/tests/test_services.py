from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.models import User, UserRole
from apps.employees.services import invite_employee
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@test.com',
        password='pass123!',
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def org_admin(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='pass123!',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(
        name='Acme Corp',
        created_by=ct_user,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.mark.django_db
class TestInviteEmployee:
    @patch('apps.invitations.services.transaction.on_commit')
    def test_invite_blocks_when_active_paid_capacity_is_exhausted(self, mock_on_commit, organisation, org_admin):
        mock_on_commit.side_effect = lambda fn: None
        batch = create_licence_batch(
            organisation,
            quantity=1,
            price_per_licence_per_month=Decimal('100.00'),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 12, 31),
            created_by=org_admin,
        )
        mark_licence_batch_paid(batch, paid_by=org_admin, paid_at=date(2026, 4, 1))

        invite_employee(
            organisation,
            email='employee1@test.com',
            first_name='One',
            last_name='Employee',
            invited_by=org_admin,
        )

        with pytest.raises(ValueError, match='No licences are available for this organisation.'):
            invite_employee(
                organisation,
                email='employee2@test.com',
                first_name='Two',
                last_name='Employee',
                invited_by=org_admin,
            )
