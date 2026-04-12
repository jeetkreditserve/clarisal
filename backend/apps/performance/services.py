from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.employees.models import Employee, EmployeeStatus
from apps.notifications.models import NotificationKind
from apps.notifications.services import create_notification

from .models import (
    AppraisalCycle,
    AppraisalReview,
    CalibrationSession,
    CalibrationSessionEntry,
    CycleStatus,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStatus,
    Goal,
    GoalCycle,
    GoalStatus,
    ReviewRelationship,
    ReviewStatus,
    ReviewType,
)

MANAGER_PHASE_REVIEW_TYPES = {ReviewType.MANAGER, ReviewType.REVIEW_360}


def _active_employees_for_org(organisation):
    return list(
        Employee.objects.filter(
            organisation=organisation,
            status=EmployeeStatus.ACTIVE,
        ).select_related('user', 'reporting_to__user', 'department')
    )


def _average_numeric_scores(ratings: dict) -> Decimal | None:
    numeric_scores = [
        Decimal(str(score))
        for score in ratings.values()
        if isinstance(score, int | float | Decimal)
    ]
    if not numeric_scores:
        return None
    return sum(numeric_scores) / Decimal(len(numeric_scores))


def _pick_feedback_reviewers(employee, employees):
    if not employees:
        return []
    candidates = [
        peer
        for peer in employees
        if peer.id != employee.id and peer.id != employee.reporting_to_id
    ]
    if employee.department_id:
        same_department = [peer for peer in candidates if peer.department_id == employee.department_id]
        if same_department:
            candidates = same_department + [peer for peer in candidates if peer.department_id != employee.department_id]
    return candidates[:2]


def _notify_cycle_open(cycle: AppraisalCycle, employees, actor):
    for employee in employees:
        create_notification(
            recipient=employee.user,
            organisation=cycle.organisation,
            kind=NotificationKind.GENERAL,
            title=f"Performance review '{cycle.name}' is now open",
            body='Complete your performance actions before the current phase deadline.',
            related_object=cycle,
            actor=actor,
        )


def create_goal_cycle(
    *,
    organisation,
    name: str,
    start_date: date,
    end_date: date,
    actor,
    auto_create_review_cycle: bool = False,
) -> GoalCycle:
    return GoalCycle.objects.create(
        organisation=organisation,
        name=name,
        start_date=start_date,
        end_date=end_date,
        status=CycleStatus.DRAFT,
        auto_create_review_cycle=auto_create_review_cycle,
        created_by=actor,
        modified_by=actor,
    )


def activate_goal_cycle(cycle: GoalCycle, *, actor) -> GoalCycle:
    if cycle.status != CycleStatus.DRAFT:
        raise ValueError('Only DRAFT cycles can be activated.')
    cycle.status = CycleStatus.ACTIVE
    cycle.modified_by = actor
    cycle.save(update_fields=['status', 'modified_at', 'modified_by'])
    return cycle


def close_goal_cycle(cycle: GoalCycle, *, actor) -> GoalCycle:
    if cycle.status != CycleStatus.ACTIVE:
        raise ValueError('Only ACTIVE cycles can be closed.')
    cycle.status = CycleStatus.CLOSED
    cycle.modified_by = actor
    cycle.save(update_fields=['status', 'modified_at', 'modified_by'])
    return cycle


def update_goal_progress(goal: Goal, *, progress_percent: int, actor) -> Goal:
    clamped = max(0, min(100, progress_percent))
    goal.progress_percent = clamped
    if clamped == 100:
        goal.status = GoalStatus.COMPLETED
    elif clamped > 0 and goal.status == GoalStatus.NOT_STARTED:
        goal.status = GoalStatus.IN_PROGRESS
    goal.modified_by = actor
    goal.save(update_fields=['progress_percent', 'status', 'modified_at', 'modified_by'])
    return goal


def create_appraisal_cycle(
    *,
    organisation,
    name: str,
    review_type: str,
    start_date: date,
    end_date: date,
    actor,
    is_probation_review: bool = False,
    goal_cycle: GoalCycle | None = None,
    self_assessment_deadline: date | None = None,
    peer_review_deadline: date | None = None,
    manager_review_deadline: date | None = None,
    calibration_deadline: date | None = None,
) -> AppraisalCycle:
    return AppraisalCycle.objects.create(
        organisation=organisation,
        goal_cycle=goal_cycle,
        name=name,
        review_type=review_type,
        start_date=start_date,
        end_date=end_date,
        status=CycleStatus.DRAFT,
        is_probation_review=is_probation_review,
        self_assessment_deadline=self_assessment_deadline,
        peer_review_deadline=peer_review_deadline,
        manager_review_deadline=manager_review_deadline,
        calibration_deadline=calibration_deadline,
        created_by=actor,
        modified_by=actor,
    )


def trigger_review_from_goal_cycle(goal_cycle: GoalCycle, *, actor) -> AppraisalCycle | None:
    if not goal_cycle.auto_create_review_cycle:
        return None
    existing = AppraisalCycle.objects.filter(goal_cycle=goal_cycle).first()
    if existing is not None:
        return existing
    base_date = goal_cycle.end_date
    return create_appraisal_cycle(
        organisation=goal_cycle.organisation,
        goal_cycle=goal_cycle,
        name=f'Review - {goal_cycle.name}',
        review_type=ReviewType.REVIEW_360,
        start_date=base_date + timedelta(days=1),
        end_date=base_date + timedelta(days=28),
        self_assessment_deadline=base_date + timedelta(days=7),
        peer_review_deadline=base_date + timedelta(days=14),
        manager_review_deadline=base_date + timedelta(days=21),
        calibration_deadline=base_date + timedelta(days=28),
        actor=actor,
    )


@transaction.atomic
def activate_appraisal_cycle(cycle: AppraisalCycle, *, actor) -> AppraisalCycle:
    if cycle.status != CycleStatus.DRAFT:
        raise ValueError(f'Cannot activate a cycle in status {cycle.status}.')

    employees = _active_employees_for_org(cycle.organisation)
    for employee in employees:
        AppraisalReview.objects.get_or_create(
            cycle=cycle,
            employee=employee,
            reviewer=employee,
            relationship=ReviewRelationship.SELF,
            defaults={'created_by': actor, 'modified_by': actor},
        )
        if cycle.review_type in MANAGER_PHASE_REVIEW_TYPES and employee.reporting_to_id:
            AppraisalReview.objects.get_or_create(
                cycle=cycle,
                employee=employee,
                reviewer=employee.reporting_to,
                relationship=ReviewRelationship.MANAGER,
                defaults={'created_by': actor, 'modified_by': actor},
            )
        if cycle.review_type == ReviewType.REVIEW_360:
            for reviewer in _pick_feedback_reviewers(employee, employees):
                FeedbackRequest.objects.get_or_create(
                    cycle=cycle,
                    employee=employee,
                    requested_from=reviewer,
                    defaults={
                        'status': FeedbackStatus.REQUESTED,
                        'due_date': cycle.peer_review_deadline,
                        'message': f'Share peer feedback for {employee.user.full_name}.',
                        'created_by': actor,
                        'modified_by': actor,
                    },
                )

    cycle.status = CycleStatus.ACTIVE
    cycle.activated_at = timezone.now()
    cycle.modified_by = actor
    cycle.save(update_fields=['status', 'activated_at', 'modified_at', 'modified_by'])
    _notify_cycle_open(cycle, employees, actor)
    return cycle


def _ensure_reviews_submitted(cycle: AppraisalCycle, relationship: str, error_message: str):
    pending = cycle.reviews.filter(relationship=relationship).exclude(status=ReviewStatus.SUBMITTED)
    if pending.exists():
        raise ValueError(error_message)


def _ensure_feedback_submitted(cycle: AppraisalCycle):
    pending = cycle.feedback_requests.exclude(status=FeedbackStatus.SUBMITTED)
    if pending.exists():
        raise ValueError('All requested 360 feedback must be submitted before advancing.')


def advance_appraisal_cycle_phase(cycle: AppraisalCycle, *, actor) -> AppraisalCycle:
    next_status = None
    now = timezone.now()

    if cycle.status == CycleStatus.ACTIVE:
        next_status = CycleStatus.SELF_ASSESSMENT
    elif cycle.status == CycleStatus.SELF_ASSESSMENT:
        _ensure_reviews_submitted(cycle, ReviewRelationship.SELF, 'All self-assessments must be submitted before advancing.')
        if cycle.review_type == ReviewType.REVIEW_360:
            next_status = CycleStatus.PEER_REVIEW
        elif cycle.review_type == ReviewType.MANAGER:
            next_status = CycleStatus.MANAGER_REVIEW
        else:
            next_status = CycleStatus.COMPLETED
    elif cycle.status == CycleStatus.PEER_REVIEW:
        _ensure_feedback_submitted(cycle)
        next_status = CycleStatus.MANAGER_REVIEW
    elif cycle.status == CycleStatus.MANAGER_REVIEW:
        if cycle.review_type in MANAGER_PHASE_REVIEW_TYPES:
            _ensure_reviews_submitted(cycle, ReviewRelationship.MANAGER, 'All manager reviews must be submitted before advancing.')
        next_status = CycleStatus.CALIBRATION
    else:
        raise ValueError(f'Cannot advance a cycle in status {cycle.status}.')

    cycle.status = next_status
    if next_status == CycleStatus.COMPLETED:
        cycle.completed_at = now
    cycle.modified_by = actor
    update_fields = ['status', 'modified_at', 'modified_by']
    if next_status == CycleStatus.COMPLETED:
        update_fields.append('completed_at')
    cycle.save(update_fields=update_fields)
    return cycle


def save_appraisal_review_draft(review: AppraisalReview, *, ratings: dict, comments: str, actor) -> AppraisalReview:
    if review.status == ReviewStatus.SUBMITTED:
        raise ValueError('Submitted reviews cannot be edited.')
    review.ratings = ratings
    review.comments = comments
    review.status = ReviewStatus.IN_PROGRESS
    review.modified_by = actor
    review.save(update_fields=['ratings', 'comments', 'status', 'modified_at', 'modified_by'])
    return review


def submit_appraisal_review(review: AppraisalReview, *, ratings: dict, comments: str, actor) -> AppraisalReview:
    if review.status == ReviewStatus.SUBMITTED:
        raise ValueError('Submitted reviews cannot be edited.')
    review.ratings = ratings
    review.comments = comments
    review.status = ReviewStatus.SUBMITTED
    review.submitted_at = timezone.now()
    review.modified_by = actor
    review.save(update_fields=['ratings', 'comments', 'status', 'submitted_at', 'modified_at', 'modified_by'])
    return review


def get_or_create_self_assessment(cycle: AppraisalCycle, *, employee, actor) -> AppraisalReview:
    review, created = AppraisalReview.objects.get_or_create(
        cycle=cycle,
        employee=employee,
        reviewer=employee,
        relationship=ReviewRelationship.SELF,
        defaults={'created_by': actor, 'modified_by': actor},
    )
    if created and cycle.status == CycleStatus.DRAFT:
        cycle.status = CycleStatus.ACTIVE
        cycle.modified_by = actor
        cycle.save(update_fields=['status', 'modified_at', 'modified_by'])
    return review


def aggregate_360_feedback(cycle: AppraisalCycle, employee) -> dict:
    responses = list(
        FeedbackResponse.objects.filter(
            request__cycle=cycle,
            request__employee=employee,
        ).exclude(submitted_at__isnull=True).order_by('created_at')
    )
    if not responses:
        return {'response_count': 0, 'dimensions': {}, 'comments': []}

    totals = defaultdict(lambda: {'total': Decimal('0'), 'count': 0})
    comments = []
    for response in responses:
        for dimension, score in response.ratings.items():
            if isinstance(score, int | float | Decimal):
                totals[dimension]['total'] += Decimal(str(score))
                totals[dimension]['count'] += 1
        if response.comments:
            comments.append(response.comments)

    dimensions = {
        dimension: {
            'avg': float(values['total'] / values['count']),
            'count': values['count'],
        }
        for dimension, values in totals.items()
        if values['count']
    }
    return {
        'response_count': len(responses),
        'dimensions': dimensions,
        'comments': comments,
    }


def create_calibration_session(cycle: AppraisalCycle, *, actor) -> CalibrationSession:
    if cycle.status != CycleStatus.CALIBRATION:
        raise ValueError('Calibration can only start once the cycle reaches the calibration phase.')

    session, _ = CalibrationSession.objects.get_or_create(
        cycle=cycle,
        defaults={'created_by': actor, 'modified_by': actor},
    )
    manager_reviews = cycle.reviews.filter(
        relationship=ReviewRelationship.MANAGER,
        status=ReviewStatus.SUBMITTED,
    ).select_related('employee')
    for review in manager_reviews:
        original_rating = _average_numeric_scores(review.ratings)
        entry, created = CalibrationSessionEntry.objects.get_or_create(
            session=session,
            employee=review.employee,
            defaults={
                'original_rating': original_rating,
                'current_rating': original_rating,
                'created_by': actor,
                'modified_by': actor,
            },
        )
        if not created and entry.original_rating is None and original_rating is not None:
            entry.original_rating = original_rating
            entry.current_rating = entry.current_rating or original_rating
            entry.modified_by = actor
            entry.save(update_fields=['original_rating', 'current_rating', 'modified_at', 'modified_by'])
    return session


def adjust_calibration_rating(session: CalibrationSession, employee, *, new_rating, reason: str, actor) -> CalibrationSessionEntry:
    if session.locked_at is not None:
        raise ValueError('This calibration session is locked.')

    entry = session.entries.get(employee=employee)
    entry.current_rating = Decimal(str(new_rating))
    entry.reason = reason
    entry.modified_by = actor
    entry.save(update_fields=['current_rating', 'reason', 'modified_at', 'modified_by'])
    return entry


def lock_calibration_session(session: CalibrationSession, *, actor) -> CalibrationSession:
    if session.locked_at is not None:
        raise ValueError('This calibration session is locked.')

    now = timezone.now()
    session.locked_at = now
    session.modified_by = actor
    session.save(update_fields=['locked_at', 'modified_at', 'modified_by'])

    cycle = session.cycle
    cycle.status = CycleStatus.COMPLETED
    cycle.completed_at = now
    cycle.modified_by = actor
    cycle.save(update_fields=['status', 'completed_at', 'modified_at', 'modified_by'])
    return session


def schedule_probation_review(employee, *, actor) -> AppraisalCycle:
    if not employee.probation_end_date:
        raise ValueError('Employee does not have a probation end date.')

    cycle = create_appraisal_cycle(
        organisation=employee.organisation,
        name=f'Probation Review - {employee.user.full_name}',
        review_type=ReviewType.MANAGER,
        start_date=employee.probation_end_date,
        end_date=employee.probation_end_date,
        self_assessment_deadline=employee.probation_end_date,
        manager_review_deadline=employee.probation_end_date + timedelta(days=3),
        calibration_deadline=employee.probation_end_date + timedelta(days=5),
        actor=actor,
        is_probation_review=True,
    )

    if employee.reporting_to_id:
        AppraisalReview.objects.create(
            cycle=cycle,
            employee=employee,
            reviewer=employee.reporting_to,
            relationship=ReviewRelationship.MANAGER,
            created_by=actor,
            modified_by=actor,
        )

    return cycle


def auto_advance_review_cycles(*, today: date | None = None, actor=None) -> dict:
    current_date = today or timezone.localdate()
    created = 0
    advanced = 0

    for goal_cycle in GoalCycle.objects.filter(
        auto_create_review_cycle=True,
        end_date__lte=current_date,
    ):
        appraisal_cycle = trigger_review_from_goal_cycle(goal_cycle, actor=actor)
        if appraisal_cycle and appraisal_cycle.created_at.date() == timezone.localdate():
            created += 1

    deadline_map = {
        CycleStatus.ACTIVE: 'self_assessment_deadline',
        CycleStatus.SELF_ASSESSMENT: 'peer_review_deadline',
        CycleStatus.PEER_REVIEW: 'manager_review_deadline',
        CycleStatus.MANAGER_REVIEW: 'calibration_deadline',
    }
    for cycle in AppraisalCycle.objects.exclude(status__in=[CycleStatus.DRAFT, CycleStatus.CALIBRATION, CycleStatus.COMPLETED, CycleStatus.CLOSED]):
        deadline_field = deadline_map.get(cycle.status)
        deadline = getattr(cycle, deadline_field, None) if deadline_field else None
        if deadline and deadline <= current_date:
            try:
                advance_appraisal_cycle_phase(cycle, actor=actor)
            except ValueError:
                continue
            advanced += 1

    return {'status': 'OK', 'created': created, 'advanced': advanced}
