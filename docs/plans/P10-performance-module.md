# P10 — Performance Management Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a performance management module with goal tracking, appraisal cycles (self/manager/360), peer feedback requests, probation review integration, and employee-facing performance summary page.

**Architecture:** New `performance` Django app. Appraisal sign-off routes through the existing `approvals` workflow. Probation reviews auto-scheduled based on `employee.probation_end_date` (added in P04). Frontend adds pages under both `/org/` and `/employee/`.

**Tech Stack:** Django 4.2 · DRF · Celery 5.4 · React 19 · TypeScript · TanStack Query v5

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/performance/__init__.py` | Create | App package |
| `backend/apps/performance/apps.py` | Create | App config |
| `backend/apps/performance/models.py` | Create | GoalCycle, Goal, AppraisalCycle, AppraisalReview, FeedbackRequest |
| `backend/apps/performance/services.py` | Create | Business logic for cycles, reviews, feedback |
| `backend/apps/performance/serializers.py` | Create | API serializers |
| `backend/apps/performance/org_views.py` | Create | Org admin views |
| `backend/apps/performance/self_views.py` | Create | Employee self-service views |
| `backend/apps/performance/org_urls.py` | Create | Org URL patterns |
| `backend/apps/performance/self_urls.py` | Create | Employee URL patterns |
| `backend/apps/performance/tasks.py` | Create | Celery task to auto-schedule probation reviews |
| `backend/apps/performance/tests/test_services.py` | Create | Service unit tests |
| `backend/clarisal/settings/base.py` | Modify | Add to INSTALLED_APPS |
| `backend/clarisal/urls.py` | Modify | Register URLs |
| `frontend/src/pages/org/GoalCyclesPage.tsx` | Create | Goal cycle management |
| `frontend/src/pages/org/AppraisalCyclesPage.tsx` | Create | Appraisal cycle management |
| `frontend/src/pages/employee/PerformancePage.tsx` | Create | Employee performance dashboard |
| `frontend/src/lib/api/performance.ts` | Create | API functions |

---

## Task 1 — `performance` App and Models

**Files:**
- Create: `backend/apps/performance/models.py`

- [x] **Step 1: Create app**

```bash
cd backend && python manage.py startapp performance apps/performance
```

Update `apps.py`:
```python
from django.apps import AppConfig

class PerformanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.performance'
    label = 'performance'
```

Add `'apps.performance'` to `LOCAL_APPS` in `backend/clarisal/settings/base.py`.

- [x] **Step 2: Write the model**

```python
# backend/apps/performance/models.py
from django.conf import settings
from django.db import models
from apps.common.models import AuditedBaseModel


class CycleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ACTIVE = 'ACTIVE', 'Active'
    CLOSED = 'CLOSED', 'Closed'


class GoalStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ReviewType(models.TextChoices):
    SELF = 'SELF', 'Self Review'
    MANAGER = 'MANAGER', 'Manager Review'
    REVIEW_360 = '360', '360° Review'


class ReviewRelationship(models.TextChoices):
    SELF = 'SELF', 'Self'
    MANAGER = 'MANAGER', 'Manager'
    PEER = 'PEER', 'Peer'
    SKIP_LEVEL = 'SKIP_LEVEL', 'Skip Level'
    DIRECT_REPORT = 'DIRECT_REPORT', 'Direct Report'


class ReviewStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'


class FeedbackStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    DECLINED = 'DECLINED', 'Declined'


# ----- Goal Models -----

class GoalCycle(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation', on_delete=models.CASCADE, related_name='goal_cycles'
    )
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT)

    def __str__(self):
        return f'{self.name} ({self.status})'


class Goal(AuditedBaseModel):
    cycle = models.ForeignKey(GoalCycle, on_delete=models.CASCADE, related_name='goals')
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='goals'
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    target = models.TextField(blank=True, help_text='Measurable target / key result')
    metric = models.CharField(max_length=100, blank=True, help_text='Unit of measurement')
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    status = models.CharField(max_length=20, choices=GoalStatus.choices, default=GoalStatus.NOT_STARTED)
    due_date = models.DateField(null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f'{self.title} — {self.employee}'


# ----- Appraisal Models -----

class AppraisalCycle(AuditedBaseModel):
    organisation = models.ForeignKey(
        'organisations.Organisation', on_delete=models.CASCADE, related_name='appraisal_cycles'
    )
    name = models.CharField(max_length=200)
    review_type = models.CharField(max_length=20, choices=ReviewType.choices, default=ReviewType.SELF)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT)
    is_probation_review = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} ({self.review_type})'


class AppraisalReview(AuditedBaseModel):
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name='reviews')
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='appraisal_reviews'
    )
    reviewer = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='reviews_given',
        null=True, blank=True,
    )
    relationship = models.CharField(max_length=20, choices=ReviewRelationship.choices)
    ratings = models.JSONField(default=dict, help_text='{"competency_id": rating_score, ...}')
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('cycle', 'employee', 'reviewer', 'relationship')]


class FeedbackRequest(AuditedBaseModel):
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name='feedback_requests')
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='feedback_requests_received'
    )
    requested_from = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='feedback_requests_to_give'
    )
    status = models.CharField(max_length=20, choices=FeedbackStatus.choices, default=FeedbackStatus.REQUESTED)
    due_date = models.DateField(null=True, blank=True)
    message = models.TextField(blank=True)
```

- [x] **Step 3: Generate and apply migration**

```bash
cd backend && python manage.py makemigrations performance --name initial
cd backend && python manage.py migrate
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/performance/ backend/clarisal/settings/base.py
git commit -m "feat(performance): create performance app with GoalCycle, Goal, AppraisalCycle, AppraisalReview, FeedbackRequest models"
```

---

## Task 2 — Performance Service Layer

**Files:**
- Create: `backend/apps/performance/services.py`
- Create: `backend/apps/performance/tests/test_services.py`

- [x] **Step 1: Write failing tests**

Create `backend/apps/performance/tests/__init__.py` and:

```python
# backend/apps/performance/tests/test_services.py
from datetime import date, timedelta
from django.test import TestCase
from apps.performance.models import GoalCycle, Goal, GoalStatus, CycleStatus, AppraisalCycle, ReviewType
from apps.performance.services import (
    create_goal_cycle,
    activate_goal_cycle,
    update_goal_progress,
    create_appraisal_cycle,
    submit_appraisal_review,
    schedule_probation_review,
)
from apps.accounts.tests.factories import OrganisationFactory, UserFactory
from apps.employees.tests.factories import EmployeeFactory


class TestGoalCycleService(TestCase):
    def setUp(self):
        self.org = OrganisationFactory()
        self.user = UserFactory()

    def test_create_goal_cycle_creates_draft(self):
        cycle = create_goal_cycle(
            organisation=self.org,
            name='Q1 2024',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            actor=self.user,
        )
        self.assertEqual(cycle.status, CycleStatus.DRAFT)
        self.assertEqual(cycle.name, 'Q1 2024')

    def test_activate_goal_cycle_changes_status(self):
        cycle = create_goal_cycle(
            organisation=self.org,
            name='Q1 2024',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            actor=self.user,
        )
        activate_goal_cycle(cycle, actor=self.user)
        cycle.refresh_from_db()
        self.assertEqual(cycle.status, CycleStatus.ACTIVE)

    def test_update_goal_progress_clamps_to_100(self):
        cycle = GoalCycle.objects.create(
            organisation=self.org,
            name='Test',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status=CycleStatus.ACTIVE,
        )
        employee = EmployeeFactory(organisation=self.org)
        goal = Goal.objects.create(
            cycle=cycle,
            employee=employee,
            title='Test Goal',
            progress_percent=0,
        )
        update_goal_progress(goal, progress_percent=120, actor=self.user)
        goal.refresh_from_db()
        self.assertEqual(goal.progress_percent, 100)

    def test_update_goal_progress_to_100_marks_completed(self):
        cycle = GoalCycle.objects.create(
            organisation=self.org,
            name='Test',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status=CycleStatus.ACTIVE,
        )
        employee = EmployeeFactory(organisation=self.org)
        goal = Goal.objects.create(cycle=cycle, employee=employee, title='Test Goal', progress_percent=0)
        update_goal_progress(goal, progress_percent=100, actor=self.user)
        goal.refresh_from_db()
        self.assertEqual(goal.status, GoalStatus.COMPLETED)


class TestProbationReviewSchedule(TestCase):
    def test_schedule_probation_review_creates_appraisal_cycle(self):
        org = OrganisationFactory()
        user = UserFactory()
        employee = EmployeeFactory(
            organisation=org,
            probation_end_date=date.today() + timedelta(days=30),
        )
        cycle = schedule_probation_review(employee, actor=user)
        self.assertIsNotNone(cycle)
        self.assertTrue(cycle.is_probation_review)
        self.assertEqual(cycle.review_type, ReviewType.MANAGER)
```

- [x] **Step 2: Run tests to verify failure**

```bash
cd backend && python -m pytest apps/performance/tests/test_services.py -v
```

Expected: FAIL.

- [x] **Step 3: Create `services.py`**

```python
# backend/apps/performance/services.py
from __future__ import annotations
from datetime import date
from django.utils import timezone

from .models import (
    GoalCycle, Goal, GoalStatus, CycleStatus,
    AppraisalCycle, AppraisalReview, ReviewType, ReviewStatus,
    FeedbackRequest, FeedbackStatus,
)


def create_goal_cycle(organisation, name: str, start_date: date, end_date: date, actor) -> GoalCycle:
    return GoalCycle.objects.create(
        organisation=organisation,
        name=name,
        start_date=start_date,
        end_date=end_date,
        status=CycleStatus.DRAFT,
        created_by=actor,
    )


def activate_goal_cycle(cycle: GoalCycle, actor) -> GoalCycle:
    if cycle.status != CycleStatus.DRAFT:
        raise ValueError('Only DRAFT cycles can be activated.')
    cycle.status = CycleStatus.ACTIVE
    cycle.modified_by = actor
    cycle.save(update_fields=['status', 'modified_at', 'modified_by'])
    return cycle


def close_goal_cycle(cycle: GoalCycle, actor) -> GoalCycle:
    if cycle.status != CycleStatus.ACTIVE:
        raise ValueError('Only ACTIVE cycles can be closed.')
    cycle.status = CycleStatus.CLOSED
    cycle.modified_by = actor
    cycle.save(update_fields=['status', 'modified_at', 'modified_by'])
    return cycle


def update_goal_progress(goal: Goal, progress_percent: int, actor) -> Goal:
    """Update goal progress. Clamps to 0-100. Auto-completes at 100."""
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
    organisation, name: str, review_type: str,
    start_date: date, end_date: date, actor,
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
    )


def submit_appraisal_review(review: AppraisalReview, ratings: dict, comments: str, actor) -> AppraisalReview:
    review.ratings = ratings
    review.comments = comments
    review.status = ReviewStatus.SUBMITTED
    review.submitted_at = timezone.now()
    review.modified_by = actor
    review.save(update_fields=['ratings', 'comments', 'status', 'submitted_at', 'modified_at', 'modified_by'])
    return review


def schedule_probation_review(employee, actor) -> AppraisalCycle:
    """Auto-create a probation appraisal cycle for an employee nearing probation end."""
    if not employee.probation_end_date:
        raise ValueError('Employee does not have a probation end date.')
    cycle = create_appraisal_cycle(
        organisation=employee.organisation,
        name=f'Probation Review — {employee.user.get_full_name()}',
        review_type=ReviewType.MANAGER,
        start_date=employee.probation_end_date,
        end_date=employee.probation_end_date,
        actor=actor,
        is_probation_review=True,
    )
    # Create the manager review record
    if employee.reporting_manager:
        AppraisalReview.objects.create(
            cycle=cycle,
            employee=employee,
            reviewer=employee.reporting_manager,
            relationship='MANAGER',
            created_by=actor,
        )
    return cycle
```

- [x] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/performance/tests/test_services.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/performance/services.py backend/apps/performance/tests/
git commit -m "feat(performance): performance service layer — goal cycles, appraisals, probation review"
```

---

## Task 3 — Performance API Endpoints

**Files:**
- Create: `backend/apps/performance/serializers.py`
- Create: `backend/apps/performance/org_views.py`
- Create: `backend/apps/performance/self_views.py`
- Create: `backend/apps/performance/org_urls.py`
- Create: `backend/apps/performance/self_urls.py`
- Modify: `backend/clarisal/urls.py`

- [x] **Step 1: Create `serializers.py`**

```python
# backend/apps/performance/serializers.py
from rest_framework import serializers
from .models import GoalCycle, Goal, AppraisalCycle, AppraisalReview, FeedbackRequest


class GoalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalCycle
        fields = ['id', 'name', 'start_date', 'end_date', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['id', 'cycle', 'employee', 'title', 'description', 'target',
                  'metric', 'weight', 'status', 'due_date', 'progress_percent', 'created_at']
        read_only_fields = ['id', 'created_at']


class AppraisalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalCycle
        fields = ['id', 'name', 'review_type', 'start_date', 'end_date',
                  'status', 'is_probation_review', 'created_at']
        read_only_fields = ['id', 'created_at']


class AppraisalReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalReview
        fields = ['id', 'cycle', 'employee', 'reviewer', 'relationship',
                  'ratings', 'comments', 'status', 'submitted_at']
        read_only_fields = ['id', 'submitted_at']


class FeedbackRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackRequest
        fields = ['id', 'cycle', 'employee', 'requested_from', 'status', 'due_date', 'message']
        read_only_fields = ['id']
```

- [x] **Step 2: Create `org_views.py`**

```python
# backend/apps/performance/org_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed
from apps.accounts.workspaces import get_active_admin_organisation
from .models import GoalCycle, AppraisalCycle
from .serializers import GoalCycleSerializer, AppraisalCycleSerializer
from .services import create_goal_cycle, activate_goal_cycle, create_appraisal_cycle


class OrgGoalCycleListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        org = get_active_admin_organisation(request, request.user)
        cycles = GoalCycle.objects.filter(organisation=org).order_by('-created_at')
        return Response(GoalCycleSerializer(cycles, many=True).data)

    def post(self, request):
        org = get_active_admin_organisation(request, request.user)
        serializer = GoalCycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        cycle = create_goal_cycle(
            organisation=org,
            name=d['name'],
            start_date=d['start_date'],
            end_date=d['end_date'],
            actor=request.user,
        )
        return Response(GoalCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class OrgAppraisalCycleListCreateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request):
        org = get_active_admin_organisation(request, request.user)
        cycles = AppraisalCycle.objects.filter(organisation=org).order_by('-created_at')
        return Response(AppraisalCycleSerializer(cycles, many=True).data)

    def post(self, request):
        org = get_active_admin_organisation(request, request.user)
        serializer = AppraisalCycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        cycle = create_appraisal_cycle(
            organisation=org,
            name=d['name'],
            review_type=d['review_type'],
            start_date=d['start_date'],
            end_date=d['end_date'],
            actor=request.user,
        )
        return Response(AppraisalCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)
```

- [x] **Step 3: Create `self_views.py`**

```python
# backend/apps/performance/self_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsEmployee
from apps.accounts.workspaces import get_active_employee
from .models import Goal, AppraisalReview
from .serializers import GoalSerializer, AppraisalReviewSerializer
from .services import update_goal_progress, submit_appraisal_review


class MyGoalListView(APIView):
    permission_classes = [IsEmployee]

    def get(self, request):
        employee = get_active_employee(request, request.user)
        if not employee:
            return Response({'error': 'No active employee workspace'}, status=400)
        goals = Goal.objects.filter(employee=employee).select_related('cycle')
        return Response(GoalSerializer(goals, many=True).data)


class MyGoalProgressUpdateView(APIView):
    permission_classes = [IsEmployee]

    def patch(self, request, pk):
        employee = get_active_employee(request, request.user)
        goal = get_object_or_404(Goal, id=pk, employee=employee)
        progress = request.data.get('progress_percent', goal.progress_percent)
        goal = update_goal_progress(goal, int(progress), actor=request.user)
        return Response(GoalSerializer(goal).data)


class MyAppraisalReviewListView(APIView):
    permission_classes = [IsEmployee]

    def get(self, request):
        employee = get_active_employee(request, request.user)
        if not employee:
            return Response({'error': 'No active employee workspace'}, status=400)
        reviews = AppraisalReview.objects.filter(employee=employee).select_related('cycle', 'reviewer__user')
        return Response(AppraisalReviewSerializer(reviews, many=True).data)


class MyAppraisalReviewSubmitView(APIView):
    permission_classes = [IsEmployee]

    def post(self, request, pk):
        employee = get_active_employee(request, request.user)
        review = get_object_or_404(AppraisalReview, id=pk, reviewer=employee)
        review = submit_appraisal_review(
            review,
            ratings=request.data.get('ratings', {}),
            comments=request.data.get('comments', ''),
            actor=request.user,
        )
        return Response(AppraisalReviewSerializer(review).data)
```

- [x] **Step 4: Create URL files**

```python
# backend/apps/performance/org_urls.py
from django.urls import path
from .org_views import OrgGoalCycleListCreateView, OrgAppraisalCycleListCreateView

urlpatterns = [
    path('performance/goal-cycles/', OrgGoalCycleListCreateView.as_view()),
    path('performance/appraisal-cycles/', OrgAppraisalCycleListCreateView.as_view()),
]
```

```python
# backend/apps/performance/self_urls.py
from django.urls import path
from .self_views import (
    MyGoalListView, MyGoalProgressUpdateView,
    MyAppraisalReviewListView, MyAppraisalReviewSubmitView,
)

urlpatterns = [
    path('performance/goals/', MyGoalListView.as_view()),
    path('performance/goals/<uuid:pk>/progress/', MyGoalProgressUpdateView.as_view()),
    path('performance/reviews/', MyAppraisalReviewListView.as_view()),
    path('performance/reviews/<uuid:pk>/submit/', MyAppraisalReviewSubmitView.as_view()),
]
```

- [x] **Step 5: Register in `clarisal/urls.py`**

Add to both legacy and versioned URL includes:
```python
path('org/', include('apps.performance.org_urls')),
path('me/', include('apps.performance.self_urls')),
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/performance/serializers.py \
        backend/apps/performance/org_views.py \
        backend/apps/performance/self_views.py \
        backend/apps/performance/org_urls.py \
        backend/apps/performance/self_urls.py \
        backend/clarisal/urls.py
git commit -m "feat(performance): REST API endpoints for goal cycles, appraisal cycles, and employee reviews"
```

---

## Task 4 — Probation Review Auto-Schedule Celery Task

**Files:**
- Create: `backend/apps/performance/tasks.py`
- Modify: `backend/clarisal/settings/base.py`

- [x] **Step 1: Create task**

```python
# backend/apps/performance/tasks.py
from celery import shared_task


@shared_task(name='performance.auto_schedule_probation_reviews')
def auto_schedule_probation_reviews():
    """
    Daily task: for any employee whose probation_end_date is 7 days away
    and who does not yet have a probation appraisal cycle, auto-create one.
    """
    from datetime import date, timedelta
    from django.contrib.auth import get_user_model
    from apps.employees.models import Employee, EmployeeStatus
    from apps.performance.models import AppraisalCycle
    from apps.performance.services import schedule_probation_review

    User = get_user_model()
    system_user = User.objects.filter(is_superuser=True).first()
    if system_user is None:
        return {'status': 'ERROR', 'reason': 'No superuser found for system actor'}

    target_date = date.today() + timedelta(days=7)
    candidates = Employee.objects.filter(
        status=EmployeeStatus.ACTIVE,
        probation_end_date=target_date,
    ).select_related('organisation', 'user', 'reporting_manager')

    scheduled = 0
    for employee in candidates:
        already_exists = AppraisalCycle.objects.filter(
            organisation=employee.organisation,
            is_probation_review=True,
            reviews__employee=employee,
        ).exists()
        if not already_exists:
            schedule_probation_review(employee, actor=system_user)
            scheduled += 1

    return {'status': 'OK', 'scheduled': scheduled}
```

- [x] **Step 2: Add to beat schedule**

In `backend/clarisal/settings/base.py`, add to `CELERY_BEAT_SCHEDULE`:
```python
'auto-schedule-probation-reviews-daily': {
    'task': 'performance.auto_schedule_probation_reviews',
    'schedule': 86400,  # daily
},
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/performance/tasks.py backend/clarisal/settings/base.py
git commit -m "feat(performance): daily Celery task to auto-schedule probation reviews 7 days in advance"
```

---

## Task 5 — Frontend Performance Pages

**Files:**
- Create: `frontend/src/lib/api/performance.ts`
- Create: `frontend/src/pages/org/GoalCyclesPage.tsx`
- Create: `frontend/src/pages/org/AppraisalCyclesPage.tsx`
- Create: `frontend/src/pages/employee/PerformancePage.tsx`

- [x] **Step 1: Create API file**

```typescript
// frontend/src/lib/api/performance.ts
import { apiClient } from './client';

export interface GoalCycle {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
}

export interface Goal {
  id: string;
  cycle: string;
  title: string;
  description: string;
  status: string;
  progress_percent: number;
  due_date: string | null;
}

export interface AppraisalReview {
  id: string;
  cycle: string;
  relationship: string;
  ratings: Record<string, number>;
  comments: string;
  status: string;
  submitted_at: string | null;
}

export const performanceApi = {
  getOrgGoalCycles: () => apiClient.get('/api/org/performance/goal-cycles/').then(r => r.data as GoalCycle[]),
  getOrgAppraisalCycles: () => apiClient.get('/api/org/performance/appraisal-cycles/').then(r => r.data),
  getMyGoals: () => apiClient.get('/api/me/performance/goals/').then(r => r.data as Goal[]),
  updateGoalProgress: (goalId: string, progress: number) =>
    apiClient.patch(`/api/me/performance/goals/${goalId}/progress/`, { progress_percent: progress }).then(r => r.data),
  getMyReviews: () => apiClient.get('/api/me/performance/reviews/').then(r => r.data as AppraisalReview[]),
  submitReview: (reviewId: string, data: { ratings: Record<string, number>; comments: string }) =>
    apiClient.post(`/api/me/performance/reviews/${reviewId}/submit/`, data).then(r => r.data),
};
```

- [x] **Step 2: Create `GoalCyclesPage.tsx`**

```tsx
// frontend/src/pages/org/GoalCyclesPage.tsx
import { useQuery } from '@tanstack/react-query';
import { performanceApi, GoalCycle } from '@/lib/api/performance';
import { AppButton } from '@/components/ui/AppButton';

export default function GoalCyclesPage() {
  const { data: cycles = [], isLoading } = useQuery({
    queryKey: ['org-goal-cycles'],
    queryFn: performanceApi.getOrgGoalCycles,
  });

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Goal Cycles</h1>
        <AppButton>New Goal Cycle</AppButton>
      </div>
      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : cycles.length === 0 ? (
        <p className="text-sm text-gray-400">No goal cycles yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-gray-500">
              <tr>
                <th className="py-3 pr-4">Name</th>
                <th className="py-3 pr-4">Start</th>
                <th className="py-3 pr-4">End</th>
                <th className="py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((c: GoalCycle) => (
                <tr key={c.id} className="border-b hover:bg-gray-50">
                  <td className="py-3 pr-4 font-medium">{c.name}</td>
                  <td className="py-3 pr-4">{c.start_date}</td>
                  <td className="py-3 pr-4">{c.end_date}</td>
                  <td className="py-3">
                    <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [x] **Step 3: Create `PerformancePage.tsx` (employee)**

```tsx
// frontend/src/pages/employee/PerformancePage.tsx
import { useQuery } from '@tanstack/react-query';
import { performanceApi, Goal, AppraisalReview } from '@/lib/api/performance';

export default function PerformancePage() {
  const { data: goals = [] } = useQuery({ queryKey: ['my-goals'], queryFn: performanceApi.getMyGoals });
  const { data: reviews = [] } = useQuery({ queryKey: ['my-reviews'], queryFn: performanceApi.getMyReviews });

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-8">
      <h1 className="text-2xl font-semibold">My Performance</h1>

      <section>
        <h2 className="text-lg font-semibold mb-4">My Goals</h2>
        {goals.length === 0 ? (
          <p className="text-sm text-gray-400">No goals assigned.</p>
        ) : (
          <ul className="space-y-3">
            {goals.map((g: Goal) => (
              <li key={g.id} className="bg-white rounded-lg border p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-sm">{g.title}</p>
                    {g.description && <p className="text-xs text-gray-500 mt-0.5">{g.description}</p>}
                  </div>
                  <span className="text-xs text-gray-400 ml-4">{g.status}</span>
                </div>
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Progress</span>
                    <span>{g.progress_percent}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full"
                      style={{ width: `${g.progress_percent}%` }}
                      role="progressbar"
                      aria-valuenow={g.progress_percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-4">Pending Reviews</h2>
        {reviews.filter((r: AppraisalReview) => r.status !== 'SUBMITTED').length === 0 ? (
          <p className="text-sm text-gray-400">No pending reviews.</p>
        ) : (
          <ul className="space-y-3">
            {reviews.filter((r: AppraisalReview) => r.status !== 'SUBMITTED').map((r: AppraisalReview) => (
              <li key={r.id} className="bg-white rounded-lg border p-4">
                <p className="text-sm font-medium">{r.relationship} Review</p>
                <p className="text-xs text-gray-500">{r.status}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
```

- [x] **Step 4: Add routes and nav items**

In `frontend/src/routes/index.tsx`, add:
```tsx
{ path: '/org/performance/goals', element: <GoalCyclesPage /> }
{ path: '/org/performance/appraisals', element: <AppraisalCyclesPage /> }
{ path: '/employee/performance', element: <PerformancePage /> }
```

Add to `OrgLayout.tsx` nav (new "Performance" group) and `EmployeeLayout.tsx` nav.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/performance.ts \
        frontend/src/pages/org/GoalCyclesPage.tsx \
        frontend/src/pages/org/AppraisalCyclesPage.tsx \
        frontend/src/pages/employee/PerformancePage.tsx \
        frontend/src/routes/index.tsx \
        frontend/src/components/layouts/
git commit -m "feat(performance): frontend pages for goal cycles, appraisal cycles, and employee performance"
```

---

## Verification

```bash
cd backend && python -m pytest apps/performance/ -v
# Expected: all tests pass

python manage.py check
# Expected: no errors
```
