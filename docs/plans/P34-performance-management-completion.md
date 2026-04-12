# P34 — Performance Management Module Completion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Wire the Performance Management module from scaffolded models to a fully functional review cycle system. Goal cycles → review triggers → 360 feedback → calibration workflow. The models and UI scaffolding exist; this plan adds the missing service logic, state machines, and frontend interactions to make the module production-usable.

**Architecture:** The `performance` app already used `GoalCycle`, `Goal`, `AppraisalCycle`, and `AppraisalReview` as its core review primitives. This implementation extended those existing models with review-phase status, goal-cycle linkage, feedback-response aggregation, calibration sessions, and self-service APIs instead of introducing a parallel `ReviewCycle` model.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · React 19 · TypeScript · Radix UI · TanStack Query · pytest · Vitest

---

## Audit Findings Addressed

- Performance Management: models + UI scaffolded; review cycles not wired; 360 feedback not aggregated; calibration workflow absent (Gap #29 — Medium)
- Overall module score: 2/10 (target: 7/10 after this plan)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/performance/services.py` | Create/Modify | Review cycle trigger, 360 aggregation, calibration |
| `backend/apps/performance/tasks.py` | Create | Celery task: auto-trigger reviews at cycle end |
| `backend/apps/performance/org_views.py` | Modify | Org-admin review-cycle, feedback-summary, and calibration endpoints |
| `backend/apps/performance/self_views.py` | Modify | Employee self-assessment and feedback-summary endpoints |
| `backend/apps/performance/serializers.py` | Modify | Review summary, 360 aggregation serializers |
| `backend/apps/performance/org_urls.py` | Modify | Register org-admin performance endpoints |
| `backend/apps/performance/self_urls.py` | Modify | Register employee performance endpoints |
| `backend/apps/performance/tests/test_services.py` | Create | Review lifecycle and 360 aggregation tests |
| `backend/apps/performance/tests/test_views.py` | Create | API endpoint tests |
| `frontend/src/pages/org/AppraisalCyclesPage.tsx` | Modify | Org admin review cycle management |
| `frontend/src/pages/employee/PerformancePage.tsx` | Modify | Employee self-assessment and received feedback |
| `frontend/src/pages/org/CalibrationPage.tsx` | Create | HR calibration session dashboard |
| `frontend/src/lib/api/performance.ts` | Modify | Performance API client |

---

## Task 1: Audit Existing Models and Identify Gaps

- [x] Read `backend/apps/performance/models.py` — document all models, their fields, and current state.
- [x] Read `backend/apps/performance/org_views.py` and `backend/apps/performance/self_views.py` — identify which endpoints exist and which are stubs.
- [x] Read `frontend/src/pages/` for any existing performance pages.
- [x] Create a gap map: the implementation reused `AppraisalCycle`/`AppraisalReview` and extended the missing workflow links.

## Task 2: Review Cycle State Machine

> A `ReviewCycle` moves through states: `DRAFT → ACTIVE → SELF_ASSESSMENT → PEER_REVIEW → MANAGER_REVIEW → CALIBRATION → COMPLETED`. The trigger from `GoalCycle` end date is missing.

- [x] Define review-cycle phase choices on the existing `CycleStatus` enum:
  - `DRAFT`, `ACTIVE`, `SELF_ASSESSMENT`, `PEER_REVIEW`, `MANAGER_REVIEW`, `CALIBRATION`, `COMPLETED`

- [x] In `performance/services.py`, add `activate_appraisal_cycle(cycle)` on the existing `AppraisalCycle` model:

```python
def activate_review_cycle(review_cycle: ReviewCycle) -> ReviewCycle:
    """
    Activate a draft review cycle:
    - Set status to ACTIVE
    - Create ReviewRequest records for all active employees in the cycle scope
    - Send notification to employees that review cycle is open
    """
    if review_cycle.status != ReviewCycleStatus.DRAFT:
        raise InvalidStateError(f"Cannot activate a cycle in status {review_cycle.status}")

    employees = Employee.objects.filter(
        organisation=review_cycle.organisation,
        status=EmployeeStatus.ACTIVE,
    )

    review_requests = [
        ReviewRequest(
            review_cycle=review_cycle,
            employee=emp,
            status=ReviewRequestStatus.PENDING,
        )
        for emp in employees
    ]
    ReviewRequest.objects.bulk_create(review_requests, ignore_conflicts=True)

    review_cycle.status = ReviewCycleStatus.ACTIVE
    review_cycle.save(update_fields=['status', 'modified_at'])

    # Notify employees
    for emp in employees:
        send_notification(
            recipient=emp,
            subject=f"Review cycle '{review_cycle.name}' is now open",
            body="Please complete your self-assessment by the due date.",
        )

    return review_cycle
```

- [x] Add `advance_appraisal_cycle_phase(cycle)` that moves through the implemented phases and validates completion at each stage.
- [x] Add a Celery beat task `auto_advance_review_cycles` that runs daily and automatically advances cycles whose phase deadline has passed.

## Task 3: Goal Cycle → Review Cycle Trigger

- [x] When a `GoalCycle` reaches its end date (detected by the daily task), automatically create an `AppraisalCycle` if `auto_create_review_cycle = True` on the goal cycle:

```python
def trigger_review_from_goal_cycle(goal_cycle: GoalCycle) -> Optional[ReviewCycle]:
    if not goal_cycle.auto_create_review_cycle:
        return None
    if ReviewCycle.objects.filter(goal_cycle=goal_cycle).exists():
        return None  # Already created

    review_cycle = ReviewCycle.objects.create(
        organisation=goal_cycle.organisation,
        goal_cycle=goal_cycle,
        name=f"Review — {goal_cycle.name}",
        status=ReviewCycleStatus.DRAFT,
        self_assessment_deadline=goal_cycle.end_date + timedelta(days=7),
        peer_review_deadline=goal_cycle.end_date + timedelta(days=14),
        manager_review_deadline=goal_cycle.end_date + timedelta(days=21),
    )
    return review_cycle
```

## Task 4: 360 Feedback Aggregation

> `FeedbackResponse` records exist per reviewer per employee, but there is no aggregation into a summary visible to the employee or manager.

- [x] Add `aggregate_360_feedback(cycle, employee)` in `performance/services.py`:

```python
def aggregate_360_feedback(
    review_cycle: ReviewCycle,
    employee: Employee,
) -> dict:
    """
    Aggregate all completed FeedbackResponse records for this employee
    in this review cycle into dimension averages and qualitative themes.
    """
    responses = FeedbackResponse.objects.filter(
        feedback_request__review_cycle=review_cycle,
        feedback_request__subject_employee=employee,
        status=FeedbackResponseStatus.COMPLETED,
    )

    if not responses.exists():
        return {'response_count': 0, 'dimensions': {}, 'themes': []}

    # Average numeric dimension scores
    dimensions = responses.values('dimension').annotate(
        avg_score=Avg('score'),
        response_count=Count('id'),
    )

    # Collect qualitative comments (anonymised)
    comments = list(responses.exclude(comments='').values_list('comments', flat=True))

    return {
        'response_count': responses.count(),
        'dimensions': {d['dimension']: {'avg': float(d['avg_score']), 'count': d['response_count']} for d in dimensions},
        'comments': comments,
    }
```

- [x] Add a `FeedbackSummarySerializer` that exposes the aggregated result.
- [x] Add org-admin and employee feedback-summary endpoints on the existing `/api/v1/org|me/performance/...` routes.

## Task 5: Calibration Workflow

> `CalibrationSession` model exists. The workflow: HR creates a calibration session for a review cycle → HR sees a table of all employees with their manager-given ratings → HR can adjust ratings (with reason) → session is locked.

- [x] In `performance/services.py`, add:
  - `create_calibration_session(review_cycle)` — creates the session and snapshot of current ratings
  - `adjust_calibration_rating(session, employee, new_rating, reason)` — HR override with audit
  - `lock_calibration_session(session)` — finalises ratings, marks cycle as COMPLETED

- [x] Add endpoints:
  - `POST /api/v1/org/performance/appraisal-cycles/:id/calibration-sessions/`
  - `PATCH /api/v1/org/performance/calibration-sessions/:id/employees/:emp_id/rating/`
  - `POST /api/v1/org/performance/calibration-sessions/:id/lock/`

## Task 6: Self-Assessment Flow (Employee)

- [x] In `performance/self_views.py`, complete the employee self-assessment flow:
  - `GET /api/v1/me/performance/review-cycles/` — list active review cycles for the employee
  - `GET /api/v1/me/performance/review-cycles/:id/self-assessment/` — get existing self-assessment
  - `PUT /api/v1/me/performance/review-cycles/:id/self-assessment/` — create or update self-assessment
  - `POST /api/v1/me/performance/review-cycles/:id/self-assessment/submit/` — submit (locks editing)

## Task 7: Frontend Pages

### AppraisalCyclesPage (Org Admin)

- [x] Upgrade `frontend/src/pages/org/AppraisalCyclesPage.tsx`:
  - List of review cycles with status badges
  - Create cycle form with linked goal cycle and phase deadlines
  - Activate button (DRAFT → ACTIVE)
  - Advance phase button
  - Per-cycle completion stats (self, manager, and feedback progress)

### PerformancePage (Employee)

- [x] Upgrade `frontend/src/pages/employee/PerformancePage.tsx`:
  - Active review cycle(s) — self-assessment form
  - Received feedback summary (360 aggregation) — visible after manager review phase
  - Goal completion status (linked to goal cycle)
  - Historical reviews (completed cycles)

### CalibrationPage (Org Admin / HR)

- [x] Create `frontend/src/pages/org/CalibrationPage.tsx`:
  - Employee table with current ratings and proposed adjustments
  - Editable rating cells (HR-only)
  - Reason field for each adjustment
  - "Lock Session" button with confirmation dialog

## Task 8: Tests

- [x] Add backend tests in `performance/tests/test_services.py`:
  - `activate_review_cycle` creates `ReviewRequest` for all active employees
  - `activate_review_cycle` on non-DRAFT cycle raises `InvalidStateError`
  - `aggregate_360_feedback` returns correct dimension averages
  - `trigger_review_from_goal_cycle` creates review cycle at goal cycle end
  - `lock_calibration_session` moves cycle to COMPLETED and prevents further edits
- [x] Add backend tests in `performance/tests/test_views.py`:
  - Self-assessment submit locks editing
  - Feedback summary only visible after MANAGER_REVIEW phase
  - Calibration adjustments require HR permission
- [x] Add Vitest smoke tests for the upgraded appraisal/performance pages and `CalibrationPage`.
