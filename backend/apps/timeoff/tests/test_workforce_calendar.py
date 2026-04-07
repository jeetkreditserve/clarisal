from datetime import date
from decimal import Decimal

import pytest

from apps.attendance.models import WFHRequest
from apps.timeoff.models import CompOffAccrual, LeaveWithoutPayEntry
from apps.timeoff.services import get_employee_calendar_month
from apps.timeoff.tests.test_services import _create_employee, _create_organisation


@pytest.mark.django_db
def test_employee_calendar_month_includes_wfh_comp_off_and_lwp_entries():
    organisation = _create_organisation('Workforce Calendar Org')
    employee = _create_employee(organisation, email='calendar-workforce@test.com')
    WFHRequest.objects.create(
        employee=employee,
        start_date=date(2026, 5, 6),
        end_date=date(2026, 5, 6),
        session='FULL_DAY',
        reason='Remote day',
        status='APPROVED',
    )
    CompOffAccrual.objects.create(
        employee=employee,
        accrual_date=date(2026, 5, 7),
        units=Decimal('1.00'),
        expires_on=date(2026, 8, 31),
        status='APPROVED',
        reason='Weekend support',
    )
    LeaveWithoutPayEntry.objects.create(
        employee=employee,
        entry_date=date(2026, 5, 8),
        units=Decimal('1.00'),
        reason='Unpaid day',
        source='MANUAL',
        status='APPROVED',
    )

    calendar = get_employee_calendar_month(employee, calendar_month='2026-05')
    entries_by_date = {item['date']: item['entries'] for item in calendar['days']}

    assert entries_by_date['2026-05-06'][0]['kind'] == 'WFH'
    assert entries_by_date['2026-05-07'][0]['kind'] == 'COMP_OFF'
    assert entries_by_date['2026-05-08'][0]['kind'] == 'LWP'
