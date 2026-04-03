import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationStatus
from apps.notifications.models import Notification, NotificationKind
from apps.notifications.services import create_notification, mark_all_read, mark_notification_read


def make_user(email: str, *, organisation=None):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=UserRole.EMPLOYEE,
        organisation=organisation,
        is_active=True,
    )


@pytest.mark.django_db
def test_create_notification_persists():
    user = make_user('notify.user@test.com')

    notification = create_notification(
        recipient=user,
        kind=NotificationKind.GENERAL,
        title='Test notification',
        body='Test body',
    )

    assert notification.id is not None
    assert notification.is_read is False
    assert notification.title == 'Test notification'
    assert notification.body == 'Test body'


@pytest.mark.django_db
def test_create_notification_with_related_object_sets_generic_reference():
    organisation = Organisation.objects.create(
        name='Notification Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )
    user = make_user('notify.related@test.com', organisation=organisation)

    notification = create_notification(
        recipient=user,
        organisation=organisation,
        kind=NotificationKind.PAYROLL_FINALIZED,
        title='Payroll finalized',
        related_object=organisation,
    )

    assert notification.object_id == str(organisation.id)
    assert notification.content_type is not None


@pytest.mark.django_db
def test_mark_notification_read_marks_only_own_notification():
    user = make_user('notify.read@test.com')
    notification = create_notification(recipient=user, kind=NotificationKind.GENERAL, title='Test')

    mark_notification_read(notification, user)
    notification.refresh_from_db()

    assert notification.is_read is True
    assert notification.read_at is not None


@pytest.mark.django_db
def test_mark_notification_read_rejects_other_user():
    recipient = make_user('notify.recipient@test.com')
    other_user = make_user('notify.other@test.com')
    notification = create_notification(recipient=recipient, kind=NotificationKind.GENERAL, title='Test')

    with pytest.raises(PermissionError):
        mark_notification_read(notification, other_user)


@pytest.mark.django_db
def test_mark_all_read_only_updates_recipient_notifications():
    user = make_user('notify.all@test.com')
    other_user = make_user('notify.all.other@test.com')

    create_notification(recipient=user, kind=NotificationKind.GENERAL, title='Notif 1')
    create_notification(recipient=user, kind=NotificationKind.GENERAL, title='Notif 2')
    create_notification(recipient=other_user, kind=NotificationKind.GENERAL, title='Other')

    updated = mark_all_read(user)

    assert updated == 2
    assert Notification.objects.filter(recipient=user, is_read=False).count() == 0
    assert Notification.objects.filter(recipient=other_user, is_read=False).count() == 1
