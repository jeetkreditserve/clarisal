from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountType, User, UserRole
from apps.employees.models import Employee, EmployeeStatus
from apps.organisations.models import Organisation, OrganisationAccessState, OrganisationBillingStatus, OrganisationStatus
from apps.performance.models import AppraisalCycle, CycleStatus, Goal, GoalCycle, GoalStatus, ReviewRelationship, ReviewType


def _create_organisation(name='Performance Org'):
    return Organisation.objects.create(
        name=name,
        status=OrganisationStatus.ACTIVE,
        billing_status=OrganisationBillingStatus.PAID,
        access_state=OrganisationAccessState.ACTIVE,
    )


def _create_user(email, *, organisation=None, role=UserRole.EMPLOYEE):
    return User.objects.create_user(
        email=email,
        password='pass123!',
        account_type=AccountType.WORKFORCE,
        role=role,
        organisation=organisation,
        is_active=True,
    )


@pytest.mark.django_db
class TestGoalCycleService:
    def test_create_goal_cycle_creates_draft(self):
        from apps.performance.services import create_goal_cycle

        organisation = _create_organisation()
        user = _create_user('goal-author@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)

        cycle = create_goal_cycle(
            organisation=organisation,
            name='Q1 2026',
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            actor=user,
        )

        assert cycle.status == CycleStatus.DRAFT
        assert cycle.name == 'Q1 2026'
        assert cycle.created_by == user

    def test_activate_goal_cycle_changes_status(self):
        from apps.performance.services import activate_goal_cycle, create_goal_cycle

        organisation = _create_organisation()
        user = _create_user('goal-activator@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        cycle = create_goal_cycle(
            organisation=organisation,
            name='Q1 2026',
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            actor=user,
        )

        activate_goal_cycle(cycle, actor=user)
        cycle.refresh_from_db()

        assert cycle.status == CycleStatus.ACTIVE
        assert cycle.modified_by == user

    def test_update_goal_progress_clamps_to_100(self):
        from apps.performance.services import update_goal_progress

        organisation = _create_organisation()
        user = _create_user('goal-progress@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        employee_user = _create_user('employee-goal@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP100',
            status=EmployeeStatus.ACTIVE,
        )
        cycle = GoalCycle.objects.create(
            organisation=organisation,
            name='Test',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=CycleStatus.ACTIVE,
        )
        goal = Goal.objects.create(
            cycle=cycle,
            employee=employee,
            title='Test Goal',
            progress_percent=0,
        )

        update_goal_progress(goal, progress_percent=120, actor=user)
        goal.refresh_from_db()

        assert goal.progress_percent == 100

    def test_update_goal_progress_to_100_marks_completed(self):
        from apps.performance.services import update_goal_progress

        organisation = _create_organisation()
        user = _create_user('goal-complete@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        employee_user = _create_user('employee-complete@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP101',
            status=EmployeeStatus.ACTIVE,
        )
        cycle = GoalCycle.objects.create(
            organisation=organisation,
            name='Test',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=CycleStatus.ACTIVE,
        )
        goal = Goal.objects.create(
            cycle=cycle,
            employee=employee,
            title='Test Goal',
            progress_percent=0,
        )

        update_goal_progress(goal, progress_percent=100, actor=user)
        goal.refresh_from_db()

        assert goal.progress_percent == 100
        assert goal.status == GoalStatus.COMPLETED


@pytest.mark.django_db
class TestProbationReviewSchedule:
    def test_schedule_probation_review_creates_appraisal_cycle(self):
        from apps.performance.services import schedule_probation_review

        organisation = _create_organisation()
        actor = _create_user('probation-actor@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        manager_user = _create_user('manager@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        manager_employee = Employee.objects.create(
            organisation=organisation,
            user=manager_user,
            employee_code='EMP200',
            status=EmployeeStatus.ACTIVE,
        )
        employee_user = _create_user('probation-employee@test.com', organisation=organisation)
        employee = Employee.objects.create(
            organisation=organisation,
            user=employee_user,
            employee_code='EMP201',
            status=EmployeeStatus.ACTIVE,
            probation_end_date=date.today() + timedelta(days=30),
            reporting_to=manager_employee,
        )

        cycle = schedule_probation_review(employee, actor=actor)

        assert isinstance(cycle, AppraisalCycle)
        assert cycle.is_probation_review is True
        assert cycle.review_type == ReviewType.MANAGER
        review = cycle.reviews.get()
        assert review.employee == employee
        assert review.reviewer == manager_employee
        assert review.relationship == ReviewRelationship.MANAGER
