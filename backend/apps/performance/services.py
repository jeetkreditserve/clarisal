from __future__ import annotations

from datetime import date

from django.utils import timezone

from .models import (
    AppraisalCycle,
    AppraisalReview,
    CycleStatus,
    Goal,
    GoalCycle,
    GoalStatus,
    ReviewRelationship,
    ReviewStatus,
    ReviewType,
)


def create_goal_cycle(*, organisation, name: str, start_date: date, end_date: date, actor) -> GoalCycle:
    return GoalCycle.objects.create(
        organisation=organisation,
        name=name,
        start_date=start_date,
        end_date=end_date,
        status=CycleStatus.DRAFT,
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
) -> AppraisalCycle:
    return AppraisalCycle.objects.create(
        organisation=organisation,
        name=name,
        review_type=review_type,
        start_date=start_date,
        end_date=end_date,
        status=CycleStatus.DRAFT,
        is_probation_review=is_probation_review,
        created_by=actor,
        modified_by=actor,
    )


def submit_appraisal_review(review: AppraisalReview, *, ratings: dict, comments: str, actor) -> AppraisalReview:
    review.ratings = ratings
    review.comments = comments
    review.status = ReviewStatus.SUBMITTED
    review.submitted_at = timezone.now()
    review.modified_by = actor
    review.save(update_fields=['ratings', 'comments', 'status', 'submitted_at', 'modified_at', 'modified_by'])
    return review


def schedule_probation_review(employee, *, actor) -> AppraisalCycle:
    if not employee.probation_end_date:
        raise ValueError('Employee does not have a probation end date.')

    cycle = create_appraisal_cycle(
        organisation=employee.organisation,
        name=f'Probation Review - {employee.user.full_name}',
        review_type=ReviewType.MANAGER,
        start_date=employee.probation_end_date,
        end_date=employee.probation_end_date,
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
