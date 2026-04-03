from datetime import date
from decimal import Decimal

import pytest

from apps.locations.models import OfficeLocation
from apps.timeoff.models import (
    DaySession,
    Holiday,
    HolidayCalendar,
    HolidayCalendarStatus,
    LeaveRequest,
    LeaveRequestStatus,
    OnDutyPolicy,
    OnDutyRequest,
    OnDutyRequestStatus,
)
from apps.timeoff.services import (
    create_holiday_calendar,
    get_employee_calendar_month,
    get_employee_holiday_entries,
    publish_holiday_calendar,
    update_holiday_calendar,
)
from apps.timeoff.tests.test_services import _create_employee, _create_leave_type, _create_organisation


def _create_location(organisation, name='HQ'):
    return OfficeLocation.objects.create(organisation=organisation, name=name)


@pytest.mark.django_db
def test_create_update_and_publish_holiday_calendar_manage_relations():
    organisation = _create_organisation('Holiday Calendar Org')
    location_one = _create_location(organisation, 'HQ')
    location_two = _create_location(organisation, 'Remote')
    existing_default = HolidayCalendar.objects.create(
        organisation=organisation,
        name='Existing Default',
        year=2026,
        is_default=True,
        status=HolidayCalendarStatus.DRAFT,
    )

    calendar_obj = create_holiday_calendar(
        organisation,
        name='FY 2026 Calendar',
        year=2026,
        is_default=True,
        holidays=[
            {
                'name': 'Founders Day',
                'holiday_date': date(2026, 5, 1),
                'classification': 'PUBLIC',
                'session': DaySession.FULL_DAY,
            },
            {
                'name': 'Culture Day',
                'holiday_date': date(2026, 5, 15),
                'classification': 'RESTRICTED',
                'session': DaySession.FIRST_HALF,
            },
        ],
        location_ids=[location_one.id],
    )

    existing_default.refresh_from_db()

    assert existing_default.is_default is False
    assert calendar_obj.holidays.count() == 2
    assert calendar_obj.location_assignments.count() == 1

    founders_day = calendar_obj.holidays.get(name='Founders Day')
    update_holiday_calendar(
        calendar_obj,
        name='FY 2026 Calendar Revised',
        holidays=[
            {
                'id': founders_day.id,
                'name': 'Founders Day',
                'holiday_date': date(2026, 5, 1),
                'classification': 'COMPANY',
                'session': DaySession.FULL_DAY,
            },
            {
                'name': 'Wellness Day',
                'holiday_date': date(2026, 6, 1),
                'classification': 'PUBLIC',
                'session': DaySession.SECOND_HALF,
            },
        ],
        location_ids=[location_two.id],
    )
    publish_holiday_calendar(calendar_obj)

    calendar_obj.refresh_from_db()

    assert calendar_obj.name == 'FY 2026 Calendar Revised'
    assert calendar_obj.status == HolidayCalendarStatus.PUBLISHED
    assert calendar_obj.published_at is not None
    assert set(calendar_obj.holidays.values_list('name', flat=True)) == {'Founders Day', 'Wellness Day'}
    assert calendar_obj.holidays.get(name='Founders Day').classification == 'COMPANY'
    assert set(calendar_obj.location_assignments.values_list('office_location_id', flat=True)) == {location_two.id}


@pytest.mark.django_db
def test_get_employee_holiday_entries_filters_by_location_and_month():
    organisation = _create_organisation('Holiday Entries Org')
    matching_location = _create_location(organisation, 'HQ')
    other_location = _create_location(organisation, 'Branch')
    employee = _create_employee(organisation, email='holiday-entries@test.com')
    employee.office_location = matching_location
    employee.save(update_fields=['office_location', 'modified_at'])

    general_calendar = HolidayCalendar.objects.create(
        organisation=organisation,
        name='General Calendar',
        year=2026,
        status=HolidayCalendarStatus.PUBLISHED,
        is_default=True,
    )
    Holiday.objects.create(
        holiday_calendar=general_calendar,
        name='Labour Day',
        holiday_date=date(2026, 5, 1),
        classification='PUBLIC',
        session=DaySession.FULL_DAY,
    )

    matching_calendar = HolidayCalendar.objects.create(
        organisation=organisation,
        name='HQ Calendar',
        year=2026,
        status=HolidayCalendarStatus.PUBLISHED,
    )
    matching_calendar.location_assignments.create(office_location=matching_location)
    Holiday.objects.create(
        holiday_calendar=matching_calendar,
        name='HQ Day',
        holiday_date=date(2026, 5, 15),
        classification='RESTRICTED',
        session=DaySession.FIRST_HALF,
    )

    other_calendar = HolidayCalendar.objects.create(
        organisation=organisation,
        name='Branch Calendar',
        year=2026,
        status=HolidayCalendarStatus.PUBLISHED,
    )
    other_calendar.location_assignments.create(office_location=other_location)
    Holiday.objects.create(
        holiday_calendar=other_calendar,
        name='Branch Day',
        holiday_date=date(2026, 5, 20),
        classification='PUBLIC',
        session=DaySession.FULL_DAY,
    )
    Holiday.objects.create(
        holiday_calendar=general_calendar,
        name='Ignored June Holiday',
        holiday_date=date(2026, 6, 2),
        classification='PUBLIC',
        session=DaySession.FULL_DAY,
    )

    entries = get_employee_holiday_entries(employee, 2026, 5)

    assert {entry['label'] for entry in entries} == {'Labour Day', 'HQ Day'}
    assert next(entry for entry in entries if entry['label'] == 'HQ Day')['color'] == '#f59e0b'


@pytest.mark.django_db
def test_get_employee_calendar_month_combines_holidays_leave_and_on_duty():
    organisation = _create_organisation('Calendar Month Org')
    employee = _create_employee(organisation, email='calendar-month@test.com')
    leave_type = _create_leave_type(organisation, code='CAL')
    policy = OnDutyPolicy.objects.create(
        organisation=organisation,
        name='Travel Policy',
        is_default=True,
        is_active=True,
    )
    calendar_obj = HolidayCalendar.objects.create(
        organisation=organisation,
        name='General Calendar',
        year=2026,
        status=HolidayCalendarStatus.PUBLISHED,
        is_default=True,
    )
    Holiday.objects.create(
        holiday_calendar=calendar_obj,
        name='Founders Day',
        holiday_date=date(2026, 5, 1),
        classification='PUBLIC',
        session=DaySession.FULL_DAY,
    )
    LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=date(2026, 5, 2),
        end_date=date(2026, 5, 3),
        start_session=DaySession.FULL_DAY,
        end_session=DaySession.FULL_DAY,
        total_units=Decimal('2.00'),
        reason='Vacation',
        status=LeaveRequestStatus.APPROVED,
    )
    OnDutyRequest.objects.create(
        employee=employee,
        policy=policy,
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 4),
        duration_type='FULL_DAY',
        total_units=Decimal('1.00'),
        purpose='Client visit',
        status=OnDutyRequestStatus.APPROVED,
    )

    calendar_month = get_employee_calendar_month(employee, calendar_month='2026-05')
    days = {entry['date']: entry['entries'] for entry in calendar_month['days']}

    assert calendar_month['month'] == '2026-05'
    assert [entry['kind'] for entry in days['2026-05-01']] == ['HOLIDAY']
    assert [entry['kind'] for entry in days['2026-05-02']] == ['LEAVE']
    assert [entry['kind'] for entry in days['2026-05-03']] == ['LEAVE']
    assert [entry['kind'] for entry in days['2026-05-04']] == ['ON_DUTY']
