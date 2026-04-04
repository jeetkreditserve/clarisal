from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.communications.models import Notice, NoticeAudienceType, NoticeCategory, NoticeStatus
from apps.communications.serializers import NoticeSerializer, NoticeWriteSerializer
from apps.communications.services import (
    create_notice,
    expire_stale_notices,
    get_employee_events,
    get_visible_notices,
    publish_notice,
    publish_scheduled_notices,
    update_notice,
)
from apps.departments.models import Department
from apps.employees.models import Employee, EmployeeProfile, EmployeeStatus
from apps.locations.models import OfficeLocation
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
        name='Notice Org',
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


@pytest.fixture
def ct_user():
    return User.objects.create_user(
        email='ct-notice@test.com',
        role=UserRole.CONTROL_TOWER,
        is_active=True,
    )


@pytest.fixture
def org_admin_user():
    return User.objects.create_user(
        email='org-notice@test.com',
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )


@pytest.fixture
def department(organisation):
    return Department.objects.create(organisation=organisation, name='Engineering')


@pytest.fixture
def location(organisation):
    return OfficeLocation.objects.create(
        organisation=organisation,
        name='HQ',
        address='1 Main St',
        city='Bengaluru',
        state='Karnataka',
        country='India',
        pincode='560001',
        is_remote=False,
        is_active=True,
    )


@pytest.fixture
def employee(organisation, department, location):
    user = User.objects.create_user(
        email='employee-notice@test.com',
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    return Employee.objects.create(
        organisation=organisation,
        user=user,
        department=department,
        office_location=location,
        employee_code='EMP-NOTICE',
        status=EmployeeStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestNoticeServices:
    def test_create_and_update_notice_support_org_admin_and_ct_authoring(self, organisation, org_admin_user, ct_user, department):
        draft = create_notice(
            organisation,
            actor=org_admin_user,
            title='Policy refresh',
            body='Review the updated handbook.',
            category=NoticeCategory.HR_POLICY,
            audience_type=NoticeAudienceType.DEPARTMENTS,
            department_ids=[department.id],
        )
        assert draft.created_by == org_admin_user
        assert list(draft.departments.values_list('id', flat=True)) == [department.id]

        updated = update_notice(
            draft,
            actor=ct_user,
            title='Policy refresh v2',
            body='Review the updated handbook today.',
            category=NoticeCategory.COMPLIANCE,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            department_ids=[],
        )
        assert updated.modified_by == ct_user
        assert updated.title == 'Policy refresh v2'
        assert updated.audience_type == NoticeAudienceType.ALL_EMPLOYEES

    def test_publish_notice_sets_timestamp_deterministically(self, organisation, org_admin_user):
        now = aware(datetime(2026, 4, 5, 9, 30))
        draft = create_notice(
            organisation,
            actor=org_admin_user,
            title='Town hall',
            body='Join at 5 PM.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
        )

        with patch('apps.communications.services.timezone.now', return_value=now):
            publish_notice(draft, actor=org_admin_user)

        draft.refresh_from_db()
        assert draft.status == NoticeStatus.PUBLISHED
        assert draft.published_at == now

    def test_get_visible_notices_applies_audience_schedule_expiry_and_sticky_ordering(
        self,
        organisation,
        org_admin_user,
        employee,
        department,
        location,
    ):
        now = aware(datetime(2026, 4, 5, 10, 0))
        sticky = create_notice(
            organisation,
            actor=org_admin_user,
            title='Sticky policy',
            body='Pinned.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            is_sticky=True,
        )
        department_notice = create_notice(
            organisation,
            actor=org_admin_user,
            title='Department update',
            body='Engineering only.',
            audience_type=NoticeAudienceType.DEPARTMENTS,
            status=NoticeStatus.PUBLISHED,
            department_ids=[department.id],
        )
        location_notice = create_notice(
            organisation,
            actor=org_admin_user,
            title='Location update',
            body='HQ only.',
            audience_type=NoticeAudienceType.OFFICE_LOCATIONS,
            status=NoticeStatus.PUBLISHED,
            office_location_ids=[location.id],
        )
        direct_notice = create_notice(
            organisation,
            actor=org_admin_user,
            title='Direct notice',
            body='Specific employee.',
            audience_type=NoticeAudienceType.SPECIFIC_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            employee_ids=[employee.id],
        )
        create_notice(
            organisation,
            actor=org_admin_user,
            title='Scheduled later',
            body='Not visible yet.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.SCHEDULED,
            scheduled_for=now + timedelta(hours=2),
        )
        create_notice(
            organisation,
            actor=org_admin_user,
            title='Expired post',
            body='Should be hidden.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            expires_at=now - timedelta(minutes=1),
        )

        visible = get_visible_notices(employee, now=now)

        assert [notice.id for notice in visible] == [
            sticky.id,
            direct_notice.id,
            location_notice.id,
            department_notice.id,
        ]
        assert Notice.objects.filter(title='Expired post').values_list('status', flat=True).get() == NoticeStatus.PUBLISHED

    def test_publish_and_expire_notice_automation_is_idempotent(self, organisation, org_admin_user):
        now = aware(datetime(2026, 4, 5, 12, 0))
        scheduled = create_notice(
            organisation,
            actor=org_admin_user,
            title='Scheduled launch',
            body='Goes live now.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.SCHEDULED,
            scheduled_for=now - timedelta(minutes=5),
        )
        expiring = create_notice(
            organisation,
            actor=org_admin_user,
            title='Expiring post',
            body='Should expire.',
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            expires_at=now - timedelta(minutes=1),
        )

        assert publish_scheduled_notices(now=now) == 1
        assert publish_scheduled_notices(now=now) == 0
        assert expire_stale_notices(now=now) == 1
        assert expire_stale_notices(now=now) == 0

        scheduled.refresh_from_db()
        expiring.refresh_from_db()
        assert scheduled.status == NoticeStatus.PUBLISHED
        assert expiring.status == NoticeStatus.EXPIRED

    def test_notice_serializer_reports_automation_state_and_blockers(self, organisation, org_admin_user):
        now = aware(datetime(2026, 4, 10, 9, 0))
        scheduled = create_notice(
            organisation,
            actor=org_admin_user,
            title='Scheduled',
            body='Waiting',
            category=NoticeCategory.OPERATIONS,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.SCHEDULED,
            scheduled_for=now + timedelta(hours=2),
        )
        overdue_publish = create_notice(
            organisation,
            actor=org_admin_user,
            title='Publish overdue',
            body='Missed publish',
            category=NoticeCategory.OPERATIONS,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.SCHEDULED,
            scheduled_for=now - timedelta(hours=2),
        )
        live = create_notice(
            organisation,
            actor=org_admin_user,
            title='Live',
            body='Active',
            category=NoticeCategory.GENERAL,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            published_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=3),
        )
        expiry_overdue = create_notice(
            organisation,
            actor=org_admin_user,
            title='Expiry overdue',
            body='Expired but not processed',
            category=NoticeCategory.GENERAL,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.PUBLISHED,
            published_at=now - timedelta(days=1),
            expires_at=now - timedelta(minutes=1),
        )
        expired = create_notice(
            organisation,
            actor=org_admin_user,
            title='Expired',
            body='Done',
            category=NoticeCategory.GENERAL,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.EXPIRED,
            expires_at=now - timedelta(days=1),
        )
        manual = create_notice(
            organisation,
            actor=org_admin_user,
            title='Draft',
            body='Manual',
            category=NoticeCategory.GENERAL,
            audience_type=NoticeAudienceType.ALL_EMPLOYEES,
            status=NoticeStatus.DRAFT,
        )

        with patch('apps.communications.serializers.timezone.now', return_value=now):
            scheduled_data = NoticeSerializer(scheduled).data
            overdue_publish_data = NoticeSerializer(overdue_publish).data
            live_data = NoticeSerializer(live).data
            expiry_overdue_data = NoticeSerializer(expiry_overdue).data
            expired_data = NoticeSerializer(expired).data
            manual_data = NoticeSerializer(manual).data

        assert scheduled_data['automation_state'] == 'WAITING_TO_PUBLISH'
        assert scheduled_data['is_automation_blocked'] is False
        assert overdue_publish_data['automation_state'] == 'PUBLISH_OVERDUE'
        assert overdue_publish_data['is_automation_blocked'] is True
        assert live_data['automation_state'] == 'LIVE'
        assert live_data['is_automation_blocked'] is False
        assert expiry_overdue_data['automation_state'] == 'EXPIRY_OVERDUE'
        assert expiry_overdue_data['is_automation_blocked'] is True
        assert expired_data['automation_state'] == 'EXPIRED'
        assert manual_data['automation_state'] == 'MANUAL'

    def test_notice_write_serializer_validates_targeting_and_schedule_rules(self):
        base_payload = {
            'title': 'Targeted notice',
            'body': 'Details',
            'category': NoticeCategory.GENERAL,
            'audience_type': NoticeAudienceType.ALL_EMPLOYEES,
            'status': NoticeStatus.DRAFT,
            'department_ids': [],
            'office_location_ids': [],
            'employee_ids': [],
        }

        department_serializer = NoticeWriteSerializer(data={**base_payload, 'audience_type': NoticeAudienceType.DEPARTMENTS})
        location_serializer = NoticeWriteSerializer(data={**base_payload, 'audience_type': NoticeAudienceType.OFFICE_LOCATIONS})
        employee_serializer = NoticeWriteSerializer(data={**base_payload, 'audience_type': NoticeAudienceType.SPECIFIC_EMPLOYEES})
        scheduled_serializer = NoticeWriteSerializer(data={**base_payload, 'status': NoticeStatus.SCHEDULED})
        expiry_serializer = NoticeWriteSerializer(
            data={
                **base_payload,
                'status': NoticeStatus.SCHEDULED,
                'scheduled_for': '2026-04-10T09:00:00Z',
                'expires_at': '2026-04-10T08:59:00Z',
            }
        )

        assert not department_serializer.is_valid()
        assert 'department_ids' in department_serializer.errors
        assert not location_serializer.is_valid()
        assert 'office_location_ids' in location_serializer.errors
        assert not employee_serializer.is_valid()
        assert 'employee_ids' in employee_serializer.errors
        assert not scheduled_serializer.is_valid()
        assert 'scheduled_for' in scheduled_serializer.errors
        assert not expiry_serializer.is_valid()
        assert 'expires_at' in expiry_serializer.errors

    def test_get_employee_events_returns_upcoming_birthdays_and_work_anniversaries(self, organisation):
        today = timezone.localdate()
        employee_user = User.objects.create_user(
            email='events@test.com',
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            status=EmployeeStatus.ACTIVE,
            employee_code='EVT001',
            date_of_joining=today + timedelta(days=7),
        )
        EmployeeProfile.objects.create(
            employee=employee,
            date_of_birth=today + timedelta(days=3),
        )

        events = get_employee_events(employee)

        assert events == [
            {
                'kind': 'BIRTHDAY',
                'label': employee.user.full_name,
                'date': (today + timedelta(days=3)).isoformat(),
            },
            {
                'kind': 'WORK_ANNIVERSARY',
                'label': employee.user.full_name,
                'date': (today + timedelta(days=7)).isoformat(),
            },
        ]
