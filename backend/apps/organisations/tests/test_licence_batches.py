from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.models import User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    BootstrapAdminStatus,
    Organisation,
    OrganisationBootstrapAdmin,
    OrganisationMembership,
    OrganisationMembershipStatus,
    OrganisationStatus,
)
from apps.organisations.services import (
    calculate_licence_billing_months,
    create_licence_batch,
    get_batch_lifecycle_state,
    get_licence_batch_defaults,
    get_org_licence_summary,
    mark_licence_batch_paid,
)


@pytest.fixture
def ct_user(db):
    return User.objects.create_superuser(
        email='ct@test.com',
        password='pass123!',
        first_name='Control',
        last_name='Tower',
        role=UserRole.CONTROL_TOWER,
    )


@pytest.fixture
def organisation(ct_user):
    return Organisation.objects.create(name='Acme Corp', created_by=ct_user)


@pytest.mark.django_db
class TestLicenceBatchDefaults:
    def test_defaults_use_env_price_and_one_year_term_when_no_active_batch(self, organisation, settings):
        settings.DEFAULT_LICENCE_PRICE_PER_MONTH = Decimal('125.00')

        defaults = get_licence_batch_defaults(
            organisation,
            quantity=2,
            start_date=date(2026, 4, 1),
            as_of=date(2026, 4, 1),
        )

        assert defaults['start_date'] == date(2026, 4, 1)
        assert defaults['end_date'] == date(2027, 4, 1)
        assert defaults['price_per_licence_per_month'] == Decimal('125.00')
        assert defaults['billing_months'] == 13
        assert defaults['total_amount'] == Decimal('3250.00')

    def test_defaults_use_latest_active_batch_end_date(self, organisation, ct_user, settings):
        settings.DEFAULT_LICENCE_PRICE_PER_MONTH = Decimal('125.00')
        first_batch = create_licence_batch(
            organisation,
            quantity=5,
            price_per_licence_per_month=Decimal('99.00'),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 10, 1),
            created_by=ct_user,
        )
        second_batch = create_licence_batch(
            organisation,
            quantity=7,
            price_per_licence_per_month=Decimal('109.00'),
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 31),
            created_by=ct_user,
        )

        mark_licence_batch_paid(first_batch, paid_by=ct_user, paid_at=date(2026, 1, 1))
        mark_licence_batch_paid(second_batch, paid_by=ct_user, paid_at=date(2026, 2, 1))

        defaults = get_licence_batch_defaults(
            organisation,
            quantity=1,
            start_date=date(2026, 6, 1),
            as_of=date(2026, 6, 1),
        )

        assert defaults['end_date'] == date(2026, 12, 31)


@pytest.mark.django_db
class TestLicenceBatchLifecycle:
    def test_calculates_billing_months_from_days_rounded_up(self):
        assert calculate_licence_billing_months(date(2026, 4, 1), date(2026, 5, 15)) == 2

    def test_lifecycle_moves_from_draft_to_paid_pending_start_to_active_to_expired(self, organisation, ct_user):
        batch = create_licence_batch(
            organisation,
            quantity=3,
            price_per_licence_per_month=Decimal('150.00'),
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 15),
            created_by=ct_user,
        )

        assert batch.payment_status == 'DRAFT'
        assert get_batch_lifecycle_state(batch, as_of=date(2026, 4, 15)) == 'DRAFT'

        mark_licence_batch_paid(batch, paid_by=ct_user, paid_at=date(2026, 4, 20))

        assert batch.payment_status == 'PAID'
        assert get_batch_lifecycle_state(batch, as_of=date(2026, 4, 20)) == 'PAID_PENDING_START'
        assert get_batch_lifecycle_state(batch, as_of=date(2026, 5, 10)) == 'ACTIVE'
        assert get_batch_lifecycle_state(batch, as_of=date(2026, 6, 16)) == 'EXPIRED'

    def test_first_paid_batch_marks_pending_org_paid(self, organisation, ct_user):
        batch = create_licence_batch(
            organisation,
            quantity=2,
            price_per_licence_per_month=Decimal('150.00'),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            created_by=ct_user,
        )

        mark_licence_batch_paid(batch, paid_by=ct_user, paid_at=date(2026, 4, 1))
        organisation.refresh_from_db()

        assert organisation.status == OrganisationStatus.PAID

    @patch('django.db.transaction.on_commit')
    @patch('apps.invitations.tasks.send_invite_email.delay')
    def test_first_paid_batch_sends_bootstrap_admin_invite(self, mock_send_invite, mock_on_commit, organisation, ct_user):
        mock_on_commit.side_effect = lambda callback: callback()
        OrganisationBootstrapAdmin.objects.create(
            organisation=organisation,
            first_name='Aditi',
            last_name='Rao',
            email='admin@acme.com',
            phone='+919876543210',
        )
        batch = create_licence_batch(
            organisation,
            quantity=2,
            price_per_licence_per_month=Decimal('150.00'),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 5, 1),
            created_by=ct_user,
        )

        mark_licence_batch_paid(batch, paid_by=ct_user, paid_at=date(2026, 4, 1))
        organisation.refresh_from_db()

        assert organisation.status == OrganisationStatus.PAID
        assert organisation.bootstrap_admin.status == BootstrapAdminStatus.INVITE_PENDING
        mock_send_invite.assert_called_once()

    def test_org_summary_counts_only_paid_active_batches(self, organisation, ct_user):
        active_batch = create_licence_batch(
            organisation,
            quantity=4,
            price_per_licence_per_month=Decimal('100.00'),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 8, 1),
            created_by=ct_user,
        )
        future_batch = create_licence_batch(
            organisation,
            quantity=9,
            price_per_licence_per_month=Decimal('110.00'),
            start_date=date(2026, 9, 1),
            end_date=date(2027, 9, 1),
            created_by=ct_user,
        )
        expired_batch = create_licence_batch(
            organisation,
            quantity=11,
            price_per_licence_per_month=Decimal('90.00'),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            created_by=ct_user,
        )
        draft_batch = create_licence_batch(
            organisation,
            quantity=13,
            price_per_licence_per_month=Decimal('75.00'),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 12, 31),
            created_by=ct_user,
        )

        mark_licence_batch_paid(active_batch, paid_by=ct_user, paid_at=date(2026, 4, 1))
        mark_licence_batch_paid(future_batch, paid_by=ct_user, paid_at=date(2026, 4, 1))
        mark_licence_batch_paid(expired_batch, paid_by=ct_user, paid_at=date(2025, 1, 1))

        summary = get_org_licence_summary(organisation, as_of=date(2026, 6, 1))

        assert draft_batch.payment_status == 'DRAFT'
        assert summary['active_paid_quantity'] == 4
        assert summary['allocated'] == 0
        assert summary['available'] == 4
        assert summary['overage'] == 0
        assert summary['has_overage'] is False

    def test_org_admin_memberships_do_not_consume_licences(self, organisation, ct_user):
        batch = create_licence_batch(
            organisation,
            quantity=2,
            price_per_licence_per_month=Decimal('100.00'),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 12, 31),
            created_by=ct_user,
        )
        mark_licence_batch_paid(batch, paid_by=ct_user, paid_at=date(2026, 4, 1))

        hybrid_user = User.objects.create_user(
            email='hybrid@acme.com',
            password='pass123!',
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        OrganisationMembership.objects.create(
            organisation=organisation,
            user=hybrid_user,
            is_org_admin=True,
            status=OrganisationMembershipStatus.ACTIVE,
        )
        Employee.objects.create(
            organisation=organisation,
            user=hybrid_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EMP001',
        )

        summary = get_org_licence_summary(organisation, as_of=date(2026, 6, 1))

        assert summary['allocated'] == 1
        assert summary['available'] == 1
