from datetime import date
from decimal import Decimal

import pytest

from apps.departments.models import Department
from apps.employees.models import EmploymentType
from apps.locations.models import OfficeLocation
from apps.timeoff.models import LeaveCycle, LeaveCycleType, LeavePlanEmployeeAssignment
from apps.timeoff.services import (
    create_leave_plan,
    get_cycle_window,
    get_default_leave_cycle,
    resolve_employee_leave_plan,
    update_leave_plan,
    upsert_leave_cycle,
)
from apps.timeoff.tests.test_services import _create_employee, _create_organisation


def _create_department(organisation, name='Engineering'):
    return Department.objects.create(organisation=organisation, name=name)


def _create_location(organisation, name='HQ'):
    return OfficeLocation.objects.create(organisation=organisation, name=name)


@pytest.mark.django_db
def test_upsert_leave_cycle_switches_default_cycle():
    organisation = _create_organisation('Timeoff Cycle Org')
    first_cycle = upsert_leave_cycle(
        organisation,
        name='Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        start_month=1,
        start_day=1,
        is_default=True,
        is_active=True,
    )

    second_cycle = upsert_leave_cycle(
        organisation,
        name='Financial Year',
        cycle_type=LeaveCycleType.FINANCIAL_YEAR,
        start_month=4,
        start_day=1,
        is_default=True,
        is_active=True,
    )

    first_cycle.refresh_from_db()

    assert first_cycle.is_default is False
    assert get_default_leave_cycle(organisation) == second_cycle


@pytest.mark.django_db
def test_create_and_update_leave_plan_manage_relations_and_default_status():
    organisation = _create_organisation('Timeoff Plan Org')
    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
    )
    existing_default = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Legacy Plan',
        is_default=True,
        is_active=True,
        priority=100,
    )

    leave_plan = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Operations Plan',
        is_default=True,
        is_active=True,
        priority=50,
        leave_types=[
            {
                'code': 'AL',
                'name': 'Annual Leave',
                'annual_entitlement': Decimal('12'),
                'credit_frequency': 'YEARLY',
            },
            {
                'code': 'CL',
                'name': 'Casual Leave',
                'annual_entitlement': Decimal('6'),
                'credit_frequency': 'MONTHLY',
            },
        ],
        rules=[
            {
                'name': 'Engineering Rule',
                'priority': 10,
                'designation': 'Engineer',
            }
        ],
    )

    existing_default.refresh_from_db()

    assert existing_default.is_default is False
    assert leave_plan.leave_types.count() == 2
    assert leave_plan.rules.count() == 1

    annual_leave = leave_plan.leave_types.get(code='AL')
    engineering_rule = leave_plan.rules.get(name='Engineering Rule')

    update_leave_plan(
        leave_plan,
        name='Operations Plan v2',
        is_default=True,
        leave_types=[
            {
                'id': annual_leave.id,
                'code': 'AL',
                'name': 'Annual Leave Plus',
                'annual_entitlement': Decimal('15'),
                'credit_frequency': 'YEARLY',
            },
            {
                'code': 'SL',
                'name': 'Sick Leave',
                'annual_entitlement': Decimal('5'),
                'credit_frequency': 'MONTHLY',
            },
        ],
        rules=[
            {
                'id': engineering_rule.id,
                'name': 'Leadership Rule',
                'priority': 5,
                'designation': 'Lead Engineer',
            }
        ],
    )

    leave_plan.refresh_from_db()

    assert leave_plan.name == 'Operations Plan v2'
    assert leave_plan.leave_types.count() == 2
    assert set(leave_plan.leave_types.values_list('code', flat=True)) == {'AL', 'SL'}
    assert leave_plan.leave_types.get(code='AL').name == 'Annual Leave Plus'
    assert leave_plan.rules.count() == 1
    assert leave_plan.rules.get().designation == 'Lead Engineer'


@pytest.mark.django_db
def test_resolve_employee_leave_plan_prefers_explicit_assignment():
    organisation = _create_organisation('Assigned Plan Org')
    employee = _create_employee(organisation, email='assigned-plan@test.com')
    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
    )
    default_plan = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Default Plan',
        is_default=True,
        is_active=True,
        priority=100,
    )
    assigned_plan = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Assigned Plan',
        is_default=False,
        is_active=True,
        priority=10,
    )
    LeavePlanEmployeeAssignment.objects.create(employee=employee, leave_plan=assigned_plan)

    assert resolve_employee_leave_plan(employee) == assigned_plan
    assert resolve_employee_leave_plan(employee) != default_plan


@pytest.mark.django_db
def test_resolve_employee_leave_plan_uses_best_matching_rule_before_default():
    organisation = _create_organisation('Rule Match Org')
    department = _create_department(organisation)
    location = _create_location(organisation)
    employee = _create_employee(organisation, email='rule-match@test.com')
    employee.department = department
    employee.office_location = location
    employee.designation = 'Lead Engineer'
    employee.employment_type = EmploymentType.FULL_TIME
    employee.save(update_fields=['department', 'office_location', 'designation', 'employment_type', 'modified_at'])

    cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Calendar Year',
        cycle_type=LeaveCycleType.CALENDAR_YEAR,
        is_default=True,
    )
    default_plan = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Default Plan',
        is_default=True,
        is_active=True,
        priority=200,
    )
    higher_priority_plan = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Engineering Plan',
        is_default=False,
        is_active=True,
        priority=50,
        rules=[
            {
                'name': 'Department Rule',
                'priority': 20,
                'department': department,
            }
        ],
    )
    best_match_plan = create_leave_plan(
        organisation,
        leave_cycle=cycle,
        name='Lead Engineer Plan',
        is_default=False,
        is_active=True,
        priority=100,
        rules=[
            {
                'name': 'Lead Rule',
                'priority': 10,
                'department': department,
                'office_location': location,
                'employment_type': EmploymentType.FULL_TIME,
                'designation': 'lead engineer',
            }
        ],
    )

    assert resolve_employee_leave_plan(employee) == best_match_plan
    assert resolve_employee_leave_plan(employee) != higher_priority_plan
    assert resolve_employee_leave_plan(employee) != default_plan


@pytest.mark.django_db
def test_get_cycle_window_supports_financial_and_joining_date_cycles():
    organisation = _create_organisation('Cycle Window Org')
    employee = _create_employee(organisation, email='cycle-window@test.com')
    employee.date_of_joining = date(2024, 8, 20)
    employee.save(update_fields=['date_of_joining', 'modified_at'])

    financial_cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Financial Year',
        cycle_type=LeaveCycleType.FINANCIAL_YEAR,
        is_default=True,
    )
    joining_cycle = LeaveCycle.objects.create(
        organisation=organisation,
        name='Anniversary',
        cycle_type=LeaveCycleType.EMPLOYEE_JOINING_DATE,
        is_default=False,
    )

    financial_start, financial_end = get_cycle_window(financial_cycle, employee, as_of=date(2026, 5, 15))
    joining_start, joining_end = get_cycle_window(joining_cycle, employee, as_of=date(2026, 5, 15))

    assert financial_start == date(2026, 4, 1)
    assert financial_end == date(2027, 3, 31)
    assert joining_start == date(2025, 8, 20)
    assert joining_end == date(2026, 8, 19)
