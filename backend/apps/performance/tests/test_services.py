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
    CycleStatus,
    FeedbackRequest,
    Goal,
    GoalCycle,
    GoalStatus,
    ReviewRelationship,
    ReviewStatus,
    ReviewType,
)


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


def _create_employee(
    organisation,
    *,
    email,
    code,
    role=UserRole.EMPLOYEE,
    reporting_to=None,
    designation='Engineer',
):
    user = _create_user(email, organisation=organisation, role=role)
    employee = Employee.objects.create(
        organisation=organisation,
        user=user,
        employee_code=code,
        status=EmployeeStatus.ACTIVE,
        designation=designation,
        reporting_to=reporting_to,
    )
    return user, employee


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


@pytest.mark.django_db
class TestAppraisalWorkflowServices:
    def test_trigger_review_from_goal_cycle_creates_linked_appraisal_cycle(self):
        from apps.performance.services import trigger_review_from_goal_cycle

        organisation = _create_organisation()
        actor = _create_user('performance-trigger@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        cycle = GoalCycle.objects.create(
            organisation=organisation,
            name='FY 2026 Goals',
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            status=CycleStatus.ACTIVE,
            auto_create_review_cycle=True,
            created_by=actor,
            modified_by=actor,
        )

        appraisal_cycle = trigger_review_from_goal_cycle(cycle, actor=actor)

        assert appraisal_cycle.goal_cycle == cycle
        assert appraisal_cycle.status == CycleStatus.DRAFT
        assert appraisal_cycle.name == 'Review - FY 2026 Goals'
        assert appraisal_cycle.self_assessment_deadline == date(2026, 7, 7)
        assert appraisal_cycle.peer_review_deadline == date(2026, 7, 14)
        assert appraisal_cycle.manager_review_deadline == date(2026, 7, 21)

    def test_activate_appraisal_cycle_creates_reviews_and_feedback_requests(self):
        from apps.performance.services import activate_appraisal_cycle

        organisation = _create_organisation()
        actor = _create_user('performance-activator@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        _, manager = _create_employee(
            organisation,
            email='manager-activate@test.com',
            code='EMP300',
            role=UserRole.ORG_ADMIN,
            designation='Engineering Manager',
        )
        _, employee = _create_employee(
            organisation,
            email='employee-activate@test.com',
            code='EMP301',
            reporting_to=manager,
        )
        _, peer = _create_employee(
            organisation,
            email='peer-activate@test.com',
            code='EMP302',
        )
        cycle = AppraisalCycle.objects.create(
            organisation=organisation,
            name='FY 2026 Review',
            review_type=ReviewType.REVIEW_360,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            status=CycleStatus.DRAFT,
            self_assessment_deadline=date(2026, 7, 7),
            peer_review_deadline=date(2026, 7, 14),
            manager_review_deadline=date(2026, 7, 21),
            created_by=actor,
            modified_by=actor,
        )

        activate_appraisal_cycle(cycle, actor=actor)

        cycle.refresh_from_db()
        relationships = set(
            cycle.reviews.filter(employee=employee).values_list('relationship', flat=True)
        )
        feedback_requests = FeedbackRequest.objects.filter(cycle=cycle, employee=employee)

        assert cycle.status == CycleStatus.ACTIVE
        assert ReviewRelationship.SELF in relationships
        assert ReviewRelationship.MANAGER in relationships
        assert feedback_requests.count() == 1
        assert feedback_requests.first().requested_from == peer

    def test_aggregate_360_feedback_returns_dimension_averages(self):
        from apps.performance.models import FeedbackResponse
        from apps.performance.services import aggregate_360_feedback

        organisation = _create_organisation()
        actor = _create_user('performance-feedback@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        _, manager = _create_employee(
            organisation,
            email='manager-feedback@test.com',
            code='EMP400',
            role=UserRole.ORG_ADMIN,
            designation='Manager',
        )
        _, employee = _create_employee(
            organisation,
            email='employee-feedback@test.com',
            code='EMP401',
            reporting_to=manager,
        )
        _, peer_one = _create_employee(organisation, email='peer-one-feedback@test.com', code='EMP402')
        _, peer_two = _create_employee(organisation, email='peer-two-feedback@test.com', code='EMP403')
        cycle = AppraisalCycle.objects.create(
            organisation=organisation,
            name='360 Cycle',
            review_type=ReviewType.REVIEW_360,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            status=CycleStatus.MANAGER_REVIEW,
            created_by=actor,
            modified_by=actor,
        )
        request_one = FeedbackRequest.objects.create(
            cycle=cycle,
            employee=employee,
            requested_from=peer_one,
            due_date=date(2026, 7, 12),
            created_by=actor,
            modified_by=actor,
        )
        request_two = FeedbackRequest.objects.create(
            cycle=cycle,
            employee=employee,
            requested_from=peer_two,
            due_date=date(2026, 7, 12),
            created_by=actor,
            modified_by=actor,
        )
        FeedbackResponse.objects.create(
            request=request_one,
            ratings={'ownership': 4, 'communication': 3},
            comments='Clear communicator',
            created_by=actor,
            modified_by=actor,
        )
        FeedbackResponse.objects.create(
            request=request_two,
            ratings={'ownership': 5, 'communication': 4},
            comments='Trusted partner',
            created_by=actor,
            modified_by=actor,
        )

        summary = aggregate_360_feedback(cycle, employee)

        assert summary['response_count'] == 2
        assert summary['dimensions']['ownership']['avg'] == pytest.approx(4.5)
        assert summary['dimensions']['communication']['avg'] == pytest.approx(3.5)
        assert summary['comments'] == ['Clear communicator', 'Trusted partner']

    def test_lock_calibration_session_completes_cycle_and_prevents_late_changes(self):
        from apps.performance.services import (
            adjust_calibration_rating,
            create_calibration_session,
            lock_calibration_session,
        )

        organisation = _create_organisation()
        actor = _create_user('performance-calibration@test.com', organisation=organisation, role=UserRole.ORG_ADMIN)
        _, manager = _create_employee(
            organisation,
            email='manager-calibration@test.com',
            code='EMP500',
            role=UserRole.ORG_ADMIN,
            designation='Manager',
        )
        _, employee = _create_employee(
            organisation,
            email='employee-calibration@test.com',
            code='EMP501',
            reporting_to=manager,
        )
        cycle = AppraisalCycle.objects.create(
            organisation=organisation,
            name='Calibration Cycle',
            review_type=ReviewType.MANAGER,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            status=CycleStatus.CALIBRATION,
            created_by=actor,
            modified_by=actor,
        )
        review = cycle.reviews.create(
            employee=employee,
            reviewer=manager,
            relationship=ReviewRelationship.MANAGER,
            ratings={'delivery': 3, 'collaboration': 4},
            status=ReviewStatus.SUBMITTED,
            created_by=actor,
            modified_by=actor,
        )

        session = create_calibration_session(cycle, actor=actor)
        entry = adjust_calibration_rating(
            session,
            employee,
            new_rating=4.5,
            reason='Raised after cross-team calibration',
            actor=actor,
        )
        lock_calibration_session(session, actor=actor)

        cycle.refresh_from_db()
        session.refresh_from_db()
        review.refresh_from_db()

        assert entry.original_rating == pytest.approx(3.5)
        assert entry.current_rating == pytest.approx(4.5)
        assert cycle.status == CycleStatus.COMPLETED
        assert session.locked_at is not None

        with pytest.raises(ValueError, match='locked'):
            adjust_calibration_rating(
                session,
                employee,
                new_rating=4.8,
                reason='Late override',
                actor=actor,
            )
