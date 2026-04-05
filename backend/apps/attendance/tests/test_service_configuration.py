from datetime import date, time

import pytest

from apps.attendance.models import AttendanceSourceConfigKind
from apps.attendance.services import (
    _get_effective_shift,
    assign_shift,
    create_shift,
    create_source_config,
    get_default_attendance_policy,
    get_source_api_key_preview,
    update_shift,
    update_source_config,
    upsert_attendance_policy,
)
from apps.timeoff.tests.test_services import _create_employee, _create_organisation


@pytest.mark.django_db
def test_get_default_attendance_policy_creates_and_reuses_default():
    organisation = _create_organisation('Attendance Policy Org')

    created_policy = get_default_attendance_policy(organisation)
    reused_policy = get_default_attendance_policy(organisation)

    assert created_policy == reused_policy
    assert created_policy.is_default is True
    assert created_policy.week_off_days == [6]


@pytest.mark.django_db
def test_upsert_attendance_policy_switches_default_without_constraint_error():
    organisation = _create_organisation('Attendance Policy Switch Org')
    first_policy = upsert_attendance_policy(
        organisation,
        name='General Policy',
        is_default=True,
        is_active=True,
        week_off_days=[6],
    )

    second_policy = upsert_attendance_policy(
        organisation,
        name='HQ Policy',
        is_default=True,
        is_active=True,
        week_off_days=[5],
    )

    first_policy.refresh_from_db()
    second_policy.refresh_from_db()

    assert first_policy.is_default is False
    assert second_policy.is_default is True
    assert second_policy.week_off_days == [5]


@pytest.mark.django_db
def test_create_and_update_source_config_manage_api_keys_and_configuration():
    organisation = _create_organisation('Attendance Source Org')
    source, raw_api_key = create_source_config(
        organisation,
        name='Webhook',
        kind=AttendanceSourceConfigKind.API,
        configuration={'endpoint': 'https://example.com/hook'},
    )

    assert raw_api_key
    assert source.configuration['endpoint'] == 'https://example.com/hook'
    assert source.configuration['api_key_hash']
    assert source.configuration['api_key_encrypted']
    assert get_source_api_key_preview(source).endswith(raw_api_key[-4:])
    assert get_source_api_key_preview(source) != raw_api_key

    updated_source, rotated_key = update_source_config(
        source,
        name='Webhook v2',
        configuration={'timeout_seconds': 30},
        rotate_api_key=True,
    )

    assert updated_source.name == 'Webhook v2'
    assert updated_source.configuration['endpoint'] == 'https://example.com/hook'
    assert updated_source.configuration['timeout_seconds'] == 30
    assert rotated_key
    assert rotated_key != raw_api_key


@pytest.mark.django_db
def test_create_update_shift_and_assignment_drive_effective_shift_resolution():
    organisation = _create_organisation('Attendance Shift Org')
    employee = _create_employee(organisation, email='attendance-shift@test.com')
    day_shift = create_shift(
        organisation,
        name='Day Shift',
        start_time=time(9, 0),
        end_time=time(18, 0),
        grace_minutes=20,
    )
    night_shift = create_shift(
        organisation,
        name='Night Shift',
        start_time=time(22, 0),
        end_time=time(6, 0),
        is_overnight=True,
    )

    updated_day_shift = update_shift(day_shift, name='General Shift', end_time=time(18, 30))
    assign_shift(employee, updated_day_shift, start_date=date(2026, 4, 1), end_date=date(2026, 4, 30))
    assign_shift(employee, night_shift, start_date=date(2026, 5, 1))

    april_assignment = _get_effective_shift(employee, date(2026, 4, 15))
    may_assignment = _get_effective_shift(employee, date(2026, 5, 2))

    assert updated_day_shift.name == 'General Shift'
    assert updated_day_shift.end_time == time(18, 30)
    assert april_assignment.shift == updated_day_shift
    assert may_assignment.shift == night_shift
