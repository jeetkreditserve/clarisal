from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType, User, UserRole
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import create_licence_batch, mark_licence_batch_paid


@pytest.fixture
def org_admin_client(db):
    organisation = Organisation.objects.create(
        name='Branch Code Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    batch = create_licence_batch(
        organisation,
        quantity=10,
        price_per_licence_per_month='99.00',
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    mark_licence_batch_paid(batch, paid_at=date(2026, 4, 1))
    user = User.objects.create_user(
        email='org-admin@test.com',
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.ORG_ADMIN,
        organisation=organisation,
        is_active=True,
    )
    OrganisationMembership.objects.create(
        user=user,
        organisation=organisation,
        is_org_admin=True,
        status=OrganisationMembershipStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    session = client.session
    session['active_workspace_kind'] = 'ADMIN'
    session['active_admin_org_id'] = str(organisation.id)
    session.save()
    return client, organisation


@pytest.mark.django_db
class TestOrgProfileEsiBranchCode:
    def test_org_profile_reads_and_updates_esi_branch_code(self, org_admin_client):
        client, organisation = org_admin_client

        read_response = client.get('/api/org/profile/')
        assert read_response.status_code == 200
        assert read_response.data['esi_branch_code'] == ''

        write_response = client.patch(
            '/api/org/profile/',
            {'esi_branch_code': 'ESI-BLR-001'},
            format='json',
        )

        assert write_response.status_code == 200
        assert write_response.data['esi_branch_code'] == 'ESI-BLR-001'
        organisation.refresh_from_db()
        assert organisation.esi_branch_code == 'ESI-BLR-001'
