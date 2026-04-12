from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import (
    Organisation,
    OrganisationAccessState,
    OrganisationBillingStatus,
    OrganisationStatus,
)
from apps.performance.models import (
    AppraisalCycle,
    AppraisalReview,
    CycleStatus,
    GoalCycle,
    ReviewRelationship,
    ReviewStatus,
    ReviewType,
)
from apps.performance.tasks import auto_advance_review_cycles, auto_schedule_probation_reviews


def _create_organisation(name='Performance Task Org'):
    return Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


def _create_user(email, *, organisation=None, role=UserRole.EMPLOYEE, is_superuser=False, is_staff=False):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.CONTROL_TOWER if is_superuser else AccountType.WORKFORCE,
        role=UserRole.CONTROL_TOWER if is_superuser else role,
        organisation=organisation,
        is_active=True,
        is_superuser=is_superuser,
        is_staff=is_staff,
    )


@pytest.mark.django_db
def test_auto_schedule_probation_reviews_returns_error_without_superuser():
    result = auto_schedule_probation_reviews()

    assert result == {'status': 'ERROR', 'reason': 'No superuser found for system actor'}


@pytest.mark.django_db
def test_auto_schedule_probation_reviews_creates_missing_cycles():
    organisation = _create_organisation()
    system_user = _create_user('system@test.com', is_superuser=True, is_staff=True)
    manager_user = _create_user('manager-task@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    manager_employee = Employee.objects.create(
        organisation=organisation,
        user=manager_user,
        employee_code='EMP300',
        status=EmployeeStatus.ACTIVE,
    )
    employee_user = _create_user('probation-task@test.com', organisation=organisation)
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP301',
        status=EmployeeStatus.ACTIVE,
        reporting_to=manager_employee,
        probation_end_date=date.today() + timedelta(days=7),
    )

    result = auto_schedule_probation_reviews()

    assert system_user.is_superuser is True
    assert result == {'status': 'OK', 'scheduled': 1}
    cycle = AppraisalCycle.objects.get(organisation=organisation, is_probation_review=True)
    assert cycle.review_type == ReviewType.MANAGER
    review = AppraisalReview.objects.get(cycle=cycle)
    assert review.employee == employee
    assert review.relationship == ReviewRelationship.MANAGER


@pytest.mark.django_db
def test_auto_schedule_probation_reviews_skips_existing_probation_review():
    organisation = _create_organisation()
    system_user = _create_user('system-skip@test.com', is_superuser=True, is_staff=True)
    manager_user = _create_user('manager-skip@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    manager_employee = Employee.objects.create(
        organisation=organisation,
        user=manager_user,
        employee_code='EMP400',
        status=EmployeeStatus.ACTIVE,
    )
    employee_user = _create_user('probation-skip@test.com', organisation=organisation)
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP401',
        status=EmployeeStatus.ACTIVE,
        reporting_to=manager_employee,
        probation_end_date=date.today() + timedelta(days=7),
    )
    cycle = AppraisalCycle.objects.create(
        organisation=organisation,
        name='Existing probation review',
        review_type=ReviewType.MANAGER,
        start_date=date.today() + timedelta(days=7),
        end_date=date.today() + timedelta(days=7),
        is_probation_review=True,
    )
    AppraisalReview.objects.create(
        cycle=cycle,
        employee=employee,
        reviewer=manager_employee,
        relationship=ReviewRelationship.MANAGER,
    )

    result = auto_schedule_probation_reviews()

    assert system_user.is_superuser is True
    assert result == {'status': 'OK', 'scheduled': 0}
    assert AppraisalCycle.objects.filter(organisation=organisation, is_probation_review=True).count() == 1


@pytest.mark.django_db
def test_auto_advance_review_cycles_creates_review_cycle_from_goal_cycle():
    organisation = _create_organisation()
    _create_user('system-advance@test.com', is_superuser=True, is_staff=True)
    actor = _create_user('goal-owner@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    GoalCycle.objects.create(
        organisation=organisation,
        name='H1 Goals',
        start_date=date.today() - timedelta(days=90),
        end_date=date.today() - timedelta(days=1),
        status=CycleStatus.ACTIVE,
        auto_create_review_cycle=True,
        created_by=actor,
        modified_by=actor,
    )

    result = auto_advance_review_cycles()

    assert result['status'] == 'OK'
    assert result['created'] == 1
    assert AppraisalCycle.objects.filter(organisation=organisation, goal_cycle__name='H1 Goals').exists()


@pytest.mark.django_db
def test_auto_advance_review_cycles_advances_due_self_assessment_phase():
    organisation = _create_organisation()
    system_user = _create_user('system-advance-phase@test.com', is_superuser=True, is_staff=True)
    manager_user = _create_user('manager-advance-phase@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
    manager_employee = Employee.objects.create(
        organisation=organisation,
        user=manager_user,
        employee_code='EMP700',
        status=EmployeeStatus.ACTIVE,
    )
    employee_user = _create_user('employee-advance-phase@test.com', organisation=organisation)
    employee = Employee.objects.create(
        organisation=organisation,
        user=employee_user,
        employee_code='EMP701',
        status=EmployeeStatus.ACTIVE,
        reporting_to=manager_employee,
    )
    cycle = AppraisalCycle.objects.create(
        organisation=organisation,
        name='Advance Due Cycle',
        review_type=ReviewType.MANAGER,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=10),
        status=CycleStatus.SELF_ASSESSMENT,
        peer_review_deadline=date.today() - timedelta(days=1),
    )
    AppraisalReview.objects.create(
        cycle=cycle,
        employee=employee,
        reviewer=employee,
        relationship=ReviewRelationship.SELF,
        ratings={'ownership': 4},
        comments='Done',
        status=ReviewStatus.SUBMITTED,
    )

    result = auto_advance_review_cycles()

    cycle.refresh_from_db()
    assert system_user.is_superuser is True
    assert result['status'] == 'OK'
    assert result['advanced'] == 1
    assert cycle.status == CycleStatus.MANAGER_REVIEW
