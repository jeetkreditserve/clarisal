from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.communications.models import NoticeAudienceType, NoticeStatus
from apps.communications.services import create_notice
from apps.communications.tasks import expire_stale_notices_task, publish_scheduled_notices_task
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)


def aware(value: datetime):
    return timezone.make_aware(value)


@pytest.fixture
def organisation(db):
    return Organisation.objects.create(
        name='Task Notice Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def actor():
    return User.objects.create_user(
        email='notice-task-admin@test.com',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.mark.django_db
class TestCommunicationTasks:
    def test_publish_scheduled_notices_task_runs_under_lock(self, organisation, actor):
        now = aware(datetime(2026, 4, 5, 9, 0))
        notice = create_notice(
            organisation,
            actor=actor,
            title='Locked publish',
            body='Scheduled.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.SCHEDULED,
            scheduled_for=now - timedelta(minutes=5),
        )

        with (
            patch('apps.communications.tasks.cache.add', return_value=True),
            patch('apps.communications.tasks.cache.delete'),
            patch('apps.communications.services.timezone.now', return_value=now),
        ):
            changed = publish_scheduled_notices_task()

        notice.refresh_from_db()
        assert changed == 1
        assert notice.status == NoticeStatus.PUBLISHED

    def test_expire_stale_notices_task_skips_when_lock_not_acquired(self, organisation, actor):
        now = aware(datetime(2026, 4, 5, 11, 0))
        notice = create_notice(
            organisation,
            actor=actor,
            title='Locked expiry',
            body='Published.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            expires_at=now - timedelta(minutes=1),
        )

        with (
            patch('apps.communications.tasks.cache.add', return_value=False),
            patch('apps.communications.services.timezone.now', return_value=now),
        ):
            changed = expire_stale_notices_task()

        notice.refresh_from_db()
        assert changed == 0
        assert notice.status == NoticeStatus.PUBLISHED
