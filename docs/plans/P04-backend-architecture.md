# P04 — Backend Architecture Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the backend architecture — async payroll calculation, API versioning, universal pagination, N+1 query fixes, database indexes, repository layer for timeoff/attendance, and employee probation tracking.

**Architecture:** Nine independent improvements applied in dependency order. Celery infrastructure already exists (apps/communications uses tasks). All changes are additive or non-breaking. Migration files are generated after each model change.

**Tech Stack:** Django 4.2 · DRF · Celery 5.4 · Redis · PostgreSQL 15 · factory-boy · pytest

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/payroll/tasks.py` | Create | Celery task wrapping `calculate_pay_run` |
| `backend/apps/payroll/views.py` | Modify | Return 202 from calculate endpoint; add status polling view |
| `backend/apps/payroll/org_urls.py` | Modify | Add calculation-status URL |
| `backend/apps/payroll/serializers.py` | Modify | Add `PayrollRunCalculationStatusSerializer` |
| `backend/clarisal/urls.py` | Modify | Wrap all patterns in `/v1/` prefix (backwards-compatible with legacy paths) |
| `backend/clarisal/settings/base.py` | Modify | Add `DEFAULT_PAGINATION_CLASS` with explicit `PAGE_SIZE` guard |
| `backend/apps/payroll/services.py` | Modify | Add `prefetch_related` in `calculate_pay_run` to fix N+1 |
| `backend/apps/payroll/migrations/` | Create | Index migration for `PayrollRunItem` |
| `backend/apps/timeoff/repositories.py` | Create | Centralised leave balance query functions |
| `backend/apps/attendance/repositories.py` | Create | Centralised attendance day query functions |
| `backend/apps/employees/models.py` | Modify | Add `probation_end_date` to `Employee` |
| `backend/apps/employees/migrations/` | Create | Migration for probation field |
| `backend/apps/employees/views.py` | Modify | Add `OrgEmployeeProbationCompleteView` |
| `backend/apps/employees/urls.py` | Modify | Register probation endpoint |
| `backend/apps/payroll/tests/test_tasks.py` | Create | Tests for async payroll task |
| `backend/apps/employees/tests/test_probation.py` | Create | Tests for probation field + endpoint |

---

## Task 1 — Async Payroll Calculation (Celery Task)

**Files:**
- Create: `backend/apps/payroll/tasks.py`
- Modify: `backend/apps/payroll/views.py` lines 240-250
- Modify: `backend/apps/payroll/org_urls.py`
- Create: `backend/apps/payroll/tests/test_tasks.py`

### Background

`OrgPayrollRunCalculateView.post()` currently calls `calculate_pay_run()` synchronously inside the HTTP request. For runs with 500+ employees this can time out. The fix: dispatch a Celery task immediately and return HTTP 202.

- [-] **Step 1: Write the failing test for async dispatch**

Create `backend/apps/payroll/tests/test_tasks.py`:

```python
from unittest.mock import patch
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.tests.factories import UserFactory, OrganisationFactory, OrgAdminMembershipFactory
from apps.payroll.tests.factories import PayrollRunFactory
from apps.payroll.models import PayrollRunStatus


class TestOrgPayrollRunCalculateViewAsync(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.org = OrganisationFactory()
        OrgAdminMembershipFactory(user=self.user, organisation=self.org)
        self.pay_run = PayrollRunFactory(organisation=self.org, status=PayrollRunStatus.DRAFT)
        self.client.force_authenticate(user=self.user)
        # Simulate active org workspace in session
        session = self.client.session
        session['active_org_admin_workspace'] = str(self.org.id)
        session.save()

    @patch('apps.payroll.tasks.calculate_pay_run_task.delay')
    def test_calculate_returns_202_with_task_id(self, mock_delay):
        mock_delay.return_value.id = 'celery-task-uuid-abc'
        response = self.client.post(
            f'/api/org/payroll/runs/{self.pay_run.id}/calculate/'
        )
        self.assertEqual(response.status_code, 202)
        self.assertIn('task_id', response.data)
        mock_delay.assert_called_once_with(str(self.pay_run.id), str(self.user.id))

    @patch('apps.payroll.tasks.calculate_pay_run_task.delay')
    def test_calculate_status_polling_returns_pending(self, mock_delay):
        mock_delay.return_value.id = 'celery-task-uuid-abc'
        self.client.post(f'/api/org/payroll/runs/{self.pay_run.id}/calculate/')
        response = self.client.get(
            f'/api/org/payroll/runs/{self.pay_run.id}/calculation-status/?task_id=celery-task-uuid-abc'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('state', response.data)
```

- [x] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest apps/payroll/tests/test_tasks.py -v
```

Expected: `FAIL` — `calculate_pay_run_task` not found, 404 or AttributeError.

- [x] **Step 3: Create `backend/apps/payroll/tasks.py`**

```python
from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from .services import calculate_pay_run
from .models import PayrollRun

User = get_user_model()


@shared_task(bind=True, name='payroll.calculate_pay_run')
def calculate_pay_run_task(self, pay_run_id: str, actor_user_id: str) -> dict:
    """Asynchronously calculate all payslip items for a payroll run."""
    try:
        pay_run = PayrollRun.objects.get(id=pay_run_id)
        actor = User.objects.get(id=actor_user_id)
        calculate_pay_run(pay_run, actor=actor)
        return {'status': 'SUCCESS', 'pay_run_id': pay_run_id}
    except PayrollRun.DoesNotExist:
        return {'status': 'ERROR', 'error': f'PayrollRun {pay_run_id} not found'}
    except Exception as exc:
        # Celery will retry on unexpected errors
        raise self.retry(exc=exc, countdown=30, max_retries=2)
```

- [x] **Step 4: Modify `OrgPayrollRunCalculateView` in `backend/apps/payroll/views.py`**

Replace the existing `OrgPayrollRunCalculateView` class (lines 240-250):

```python
from celery.result import AsyncResult


class OrgPayrollRunCalculateView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        pay_run = get_object_or_404(PayrollRun, organisation=organisation, id=pk)
        from .tasks import calculate_pay_run_task
        result = calculate_pay_run_task.delay(str(pay_run.id), str(request.user.id))
        return Response(
            {'task_id': result.id, 'pay_run_id': str(pay_run.id)},
            status=status.HTTP_202_ACCEPTED,
        )


class OrgPayrollRunCalculationStatusView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, pk):
        organisation = _get_admin_organisation(request)
        get_object_or_404(PayrollRun, organisation=organisation, id=pk)  # IDOR guard
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id query param required'}, status=status.HTTP_400_BAD_REQUEST)
        result = AsyncResult(task_id)
        data = {
            'task_id': task_id,
            'state': result.state,  # PENDING / STARTED / SUCCESS / FAILURE / RETRY
            'result': result.result if result.successful() else None,
            'error': str(result.result) if result.failed() else None,
        }
        return Response(data)
```

- [x] **Step 5: Register new URL in `backend/apps/payroll/org_urls.py`**

Add import and URL pattern. Open the file, locate the runs detail patterns, add:

```python
from .views import OrgPayrollRunCalculationStatusView

# Inside urlpatterns, after the existing calculate pattern:
path('payroll/runs/<uuid:pk>/calculation-status/', OrgPayrollRunCalculationStatusView.as_view()),
```

- [x] **Step 6: Run tests**

```bash
cd backend && python -m pytest apps/payroll/tests/test_tasks.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/payroll/tasks.py backend/apps/payroll/views.py backend/apps/payroll/org_urls.py backend/apps/payroll/tests/test_tasks.py
git commit -m "feat(payroll): async calculation via Celery task, return 202 + polling endpoint"
```

---

## Task 2 — API Versioning (`/v1/` Prefix)

**Files:**
- Modify: `backend/clarisal/urls.py`

### Background

All current routes use `/api/auth/`, `/api/org/`, `/api/me/`, `/api/ct/`. Adding a `/v1/` layer enables future breaking changes without disrupting existing clients. Strategy: add versioned routes alongside legacy routes (both work) so frontend migration is not required immediately.

- [-] **Step 1: Add versioned URL includes to `backend/clarisal/urls.py`**

Open the file. After the existing `urlpatterns` list, append:

```python
# v1 versioned routes (same views, new prefix — clients should migrate to these)
v1_urlpatterns = [
    path('v1/auth/', include('apps.accounts.urls')),
    path('v1/ct/', include('apps.organisations.urls')),
    path('v1/ct/', include('apps.invitations.urls')),
    path('v1/ct/', include('apps.audit.urls')),
    path('v1/ct/', include('apps.payroll.ct_urls')),
    path('v1/org/', include('apps.organisations.org_urls')),
    path('v1/org/', include('apps.locations.urls')),
    path('v1/org/', include('apps.departments.urls')),
    path('v1/org/', include('apps.employees.urls')),
    path('v1/org/', include('apps.documents.urls')),
    path('v1/org/', include('apps.approvals.urls')),
    path('v1/org/', include('apps.timeoff.org_urls')),
    path('v1/org/', include('apps.attendance.urls')),
    path('v1/org/', include('apps.communications.urls')),
    path('v1/org/', include('apps.payroll.org_urls')),
    path('v1/me/', include('apps.employees.self_urls')),
    path('v1/me/', include('apps.documents.self_urls')),
    path('v1/me/', include('apps.approvals.self_urls')),
    path('v1/me/', include('apps.timeoff.self_urls')),
    path('v1/me/', include('apps.attendance.self_urls')),
    path('v1/me/', include('apps.communications.self_urls')),
    path('v1/me/', include('apps.payroll.self_urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('api/', include(([
        *[path(p.pattern._route, p.callback, name=p.name) if hasattr(p, 'callback') else p
          for p in urlpatterns if hasattr(p.pattern, '_route')],
    ], 'api'))),
]
```

**Simpler approach** (avoids duplication and import errors) — replace the entire `urlpatterns` with:

```python
_app_includes = [
    path('auth/', include('apps.accounts.urls')),
    path('ct/', include('apps.organisations.urls')),
    path('ct/', include('apps.invitations.urls')),
    path('ct/', include('apps.audit.urls')),
    path('ct/', include('apps.payroll.ct_urls')),
    path('org/', include('apps.organisations.org_urls')),
    path('org/', include('apps.locations.urls')),
    path('org/', include('apps.departments.urls')),
    path('org/', include('apps.employees.urls')),
    path('org/', include('apps.documents.urls')),
    path('org/', include('apps.approvals.urls')),
    path('org/', include('apps.timeoff.org_urls')),
    path('org/', include('apps.attendance.urls')),
    path('org/', include('apps.communications.urls')),
    path('org/', include('apps.audit.urls')),
    path('org/', include('apps.payroll.org_urls')),
    path('me/', include('apps.employees.self_urls')),
    path('me/', include('apps.documents.self_urls')),
    path('me/', include('apps.approvals.self_urls')),
    path('me/', include('apps.timeoff.self_urls')),
    path('me/', include('apps.attendance.self_urls')),
    path('me/', include('apps.communications.self_urls')),
    path('me/', include('apps.payroll.self_urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    # Legacy unversioned routes (keep for backwards compatibility)
    path('api/', include(_app_includes)),
    # v1 versioned routes
    path('api/v1/', include(_app_includes)),
]
```

- [x] **Step 2: Verify server starts**

```bash
cd backend && python manage.py check --deploy 2>&1 | head -30
# Expected: no URL errors
```

- [x] **Step 3: Verify a versioned route resolves**

```bash
cd backend && python -c "
from django.test import RequestFactory
from django.urls import resolve
r = resolve('/api/v1/auth/login/')
print('OK:', r.func)
"
# Expected: OK: <function ...login...>
```

- [ ] **Step 4: Commit**

```bash
git add backend/clarisal/urls.py
git commit -m "feat(api): add /v1/ versioned URL prefix alongside legacy routes"
```

---

## Task 3 — Fix N+1 in `calculate_pay_run`

**Files:**
- Modify: `backend/apps/payroll/services.py` — `calculate_pay_run()` function

### Background

`calculate_pay_run()` iterates over employees and for each one loads their `CompensationAssignment` → template → lines → component in a loop. This creates N×4 queries for N employees. Fix: one `prefetch_related` call before the loop.

- [x] **Step 1: Locate the loop in `services.py`**

Search for `calculate_pay_run` function. Find the line that builds the employee/assignment queryset inside the function body.

- [x] **Step 2: Add prefetch before the loop**

Find the queryset that fetches employees or assignments inside `calculate_pay_run`. It will look similar to:

```python
employees = Employee.objects.filter(organisation=pay_run.organisation, status=EmployeeStatus.ACTIVE)
```

Replace with:

```python
employees = (
    Employee.objects
    .filter(organisation=pay_run.organisation, status=EmployeeStatus.ACTIVE)
    .select_related('user')
    .prefetch_related(
        'compensation_assignments__template__lines__component',
        'compensation_assignments__lines__component',
    )
)
```

If the compensation assignments are fetched separately inside the loop (e.g., `CompensationAssignment.objects.filter(employee=emp)`), consolidate by building a dict keyed by employee ID before the loop:

```python
assignments_by_employee = {}
for assignment in CompensationAssignment.objects.filter(
    employee__organisation=pay_run.organisation,
    status=CompensationAssignmentStatus.ACTIVE,
).select_related('employee', 'template').prefetch_related('lines__component', 'template__lines__component'):
    assignments_by_employee[assignment.employee_id] = assignment
```

Then replace per-employee DB hits inside the loop with `assignments_by_employee.get(emp.id)`.

- [x] **Step 3: Run existing payroll tests to confirm no regression**

```bash
cd backend && python -m pytest apps/payroll/ -v --tb=short
```

Expected: All passing tests continue to pass.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/payroll/services.py
git commit -m "perf(payroll): prefetch compensation assignments to eliminate N+1 in calculate_pay_run"
```

---

## Task 4 — `PayrollRunItem` Database Indexes

**Files:**
- Create: `backend/apps/payroll/migrations/000X_payrollrunitem_indexes.py` (auto-generated)

### Background

`PayrollRunItem` is queried in two hot paths: (1) load all items for a run, (2) load all items for an employee across runs. Without composite indexes, these are sequential scans on large tables.

- [x] **Step 1: Add `Meta.indexes` to `PayrollRunItem` model in `backend/apps/payroll/models.py`**

Locate `class PayrollRunItem(AuditedBaseModel)`. Add or extend its `Meta` class:

```python
class Meta:
    indexes = [
        models.Index(fields=['pay_run', 'employee'], name='payrollrunitem_run_emp_idx'),
        models.Index(fields=['employee', 'pay_run'], name='payrollrunitem_emp_run_idx'),
    ]
```

- [x] **Step 2: Generate migration**

```bash
cd backend && python manage.py makemigrations payroll --name payrollrunitem_indexes
```

Expected: New migration file created.

- [x] **Step 3: Apply migration**

```bash
cd backend && python manage.py migrate
```

Expected: `Applying payroll.000X_payrollrunitem_indexes... OK`

- [ ] **Step 4: Commit**

```bash
git add backend/apps/payroll/models.py backend/apps/payroll/migrations/
git commit -m "perf(payroll): add composite DB indexes on PayrollRunItem for run/employee lookups"
```

---

## Task 5 — Timeoff Repository Layer

**Files:**
- Create: `backend/apps/timeoff/repositories.py`
- Modify: `backend/apps/timeoff/services.py` — replace direct ORM calls with repository functions

### Background

`timeoff/services.py` contains raw ORM expressions for leave balance calculation scattered across multiple functions. Centralising them into a repository makes unit testing (mock at repo boundary) and future query optimisation straightforward.

- [x] **Step 1: Create `backend/apps/timeoff/repositories.py`**

```python
from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from .models import LeaveBalance, LeaveLedgerEntry, LeaveLedgerEntryType, LeaveRequest, LeaveRequestStatus


ZERO = Decimal('0.00')


def get_accrued_days(employee_id, leave_type_id) -> Decimal:
    """Sum of all ACCRUAL ledger entries for employee + leave type."""
    result = LeaveLedgerEntry.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        entry_type=LeaveLedgerEntryType.ACCRUAL,
    ).aggregate(total=Sum('days'))['total']
    return result or ZERO


def get_used_days(employee_id, leave_type_id) -> Decimal:
    """Sum of all DEBIT ledger entries (approved leaves consumed)."""
    result = LeaveLedgerEntry.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        entry_type=LeaveLedgerEntryType.DEBIT,
    ).aggregate(total=Sum('days'))['total']
    return result or ZERO


def get_carry_forward_days(employee_id, leave_type_id) -> Decimal:
    """Sum of all CARRY_FORWARD ledger entries."""
    result = LeaveLedgerEntry.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        entry_type=LeaveLedgerEntryType.CARRY_FORWARD,
    ).aggregate(total=Sum('days'))['total']
    return result or ZERO


def get_pending_leave_days(employee_id, leave_type_id) -> Decimal:
    """Sum of days for PENDING leave requests (not yet approved — still count against balance)."""
    result = LeaveRequest.objects.filter(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        status=LeaveRequestStatus.PENDING,
    ).aggregate(total=Sum('total_days'))['total']
    return result or ZERO


def get_available_balance(employee_id, leave_type_id) -> Decimal:
    """Available = accrued + carry_forward - used - pending."""
    accrued = get_accrued_days(employee_id, leave_type_id)
    carry = get_carry_forward_days(employee_id, leave_type_id)
    used = get_used_days(employee_id, leave_type_id)
    pending = get_pending_leave_days(employee_id, leave_type_id)
    return max(ZERO, accrued + carry - used - pending)


def get_leave_balance_snapshot(employee_id, leave_type_id) -> dict:
    """Return a full balance breakdown dict for display or API responses."""
    accrued = get_accrued_days(employee_id, leave_type_id)
    carry = get_carry_forward_days(employee_id, leave_type_id)
    used = get_used_days(employee_id, leave_type_id)
    pending = get_pending_leave_days(employee_id, leave_type_id)
    available = max(ZERO, accrued + carry - used - pending)
    return {
        'accrued': accrued,
        'carry_forward': carry,
        'used': used,
        'pending': pending,
        'available': available,
    }
```

- [x] **Step 2: Update `timeoff/services.py` to use repository functions**

Find all direct `LeaveLedgerEntry.objects.filter(...).aggregate(Sum(...))` calls in `services.py`. Replace each with the matching repository function. Example replacement:

```python
# Before:
available = LeaveLedgerEntry.objects.filter(
    employee=employee,
    leave_type=leave_type,
).aggregate(net=Sum('days'))['net'] or ZERO

# After:
from .repositories import get_available_balance
available = get_available_balance(employee.id, leave_type.id)
```

- [x] **Step 3: Run timeoff tests**

```bash
cd backend && python -m pytest apps/timeoff/ -v --tb=short
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/timeoff/repositories.py backend/apps/timeoff/services.py
git commit -m "refactor(timeoff): extract leave balance queries into repository layer"
```

---

## Task 6 — Attendance Repository Layer

**Files:**
- Create: `backend/apps/attendance/repositories.py`

- [x] **Step 1: Create `backend/apps/attendance/repositories.py`**

```python
from __future__ import annotations

from datetime import date

from django.db.models import Count, Q

from .models import AttendanceDay, AttendanceDayStatus, AttendancePunch


def get_attendance_day(employee_id, work_date: date):
    """Return the AttendanceDay record for a specific date, or None."""
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        work_date=work_date,
    ).first()


def get_attendance_days_in_range(employee_id, start_date: date, end_date: date):
    """Return queryset of AttendanceDays for an employee within a date range."""
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        work_date__gte=start_date,
        work_date__lte=end_date,
    ).order_by('work_date')


def count_present_days(employee_id, start_date: date, end_date: date) -> int:
    """Count days with status PRESENT or HALF_DAY in the range."""
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        work_date__gte=start_date,
        work_date__lte=end_date,
        status__in=[AttendanceDayStatus.PRESENT, AttendanceDayStatus.HALF_DAY],
    ).count()


def count_absent_days(employee_id, start_date: date, end_date: date) -> int:
    """Count days with status ABSENT in the range."""
    return AttendanceDay.objects.filter(
        employee_id=employee_id,
        work_date__gte=start_date,
        work_date__lte=end_date,
        status=AttendanceDayStatus.ABSENT,
    ).count()


def get_punches_for_day(employee_id, work_date: date):
    """Return all punch records for an employee on a given day, ordered by time."""
    return AttendancePunch.objects.filter(
        employee_id=employee_id,
        punch_time__date=work_date,
    ).order_by('punch_time')
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/attendance/repositories.py
git commit -m "refactor(attendance): create repository layer for attendance day queries"
```

---

## Task 7 — Employee Probation Tracking

**Files:**
- Modify: `backend/apps/employees/models.py` — add `probation_end_date` to `Employee`
- Create: migration
- Modify: `backend/apps/employees/views.py` — add `OrgEmployeeProbationCompleteView`
- Modify: `backend/apps/employees/urls.py` — register endpoint
- Create: `backend/apps/employees/tests/test_probation.py`

- [x] **Step 1: Write failing test**

Create `backend/apps/employees/tests/test_probation.py`:

```python
from datetime import date, timedelta
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.tests.factories import UserFactory, OrganisationFactory, OrgAdminMembershipFactory
from apps.employees.tests.factories import EmployeeFactory
from apps.employees.models import Employee, EmployeeStatus


class TestProbationEndDateField(TestCase):
    def test_employee_has_probation_end_date_field(self):
        emp = EmployeeFactory()
        emp.probation_end_date = date.today() + timedelta(days=90)
        emp.save()
        emp.refresh_from_db()
        self.assertEqual(emp.probation_end_date, date.today() + timedelta(days=90))

    def test_probation_end_date_nullable(self):
        emp = EmployeeFactory()
        self.assertIsNone(emp.probation_end_date)


class TestOrgEmployeeProbationCompleteView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.org = OrganisationFactory()
        OrgAdminMembershipFactory(user=self.user, organisation=self.org)
        self.emp = EmployeeFactory(organisation=self.org, probation_end_date=date.today() - timedelta(days=1))
        self.client.force_authenticate(user=self.user)
        session = self.client.session
        session['active_org_admin_workspace'] = str(self.org.id)
        session.save()

    def test_probation_complete_clears_probation_end_date(self):
        response = self.client.post(
            f'/api/org/employees/{self.emp.id}/probation-complete/'
        )
        self.assertEqual(response.status_code, 200)
        self.emp.refresh_from_db()
        self.assertIsNone(self.emp.probation_end_date)

    def test_probation_complete_returns_404_for_other_org(self):
        other_org = OrganisationFactory()
        other_emp = EmployeeFactory(organisation=other_org)
        response = self.client.post(
            f'/api/org/employees/{other_emp.id}/probation-complete/'
        )
        self.assertEqual(response.status_code, 404)
```

- [x] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest apps/employees/tests/test_probation.py -v
```

Expected: `FAIL` — `Employee` has no `probation_end_date`, URL not found.

- [x] **Step 3: Add field to `Employee` model**

In `backend/apps/employees/models.py`, locate the `Employee` model class. Add the field after `date_of_joining`:

```python
probation_end_date = models.DateField(
    null=True,
    blank=True,
    help_text='Date on which the employee completes their probation period.',
)
```

- [x] **Step 4: Generate and apply migration**

```bash
cd backend && python manage.py makemigrations employees --name add_probation_end_date
cd backend && python manage.py migrate
```

- [x] **Step 5: Add `OrgEmployeeProbationCompleteView` to `views.py`**

In `backend/apps/employees/views.py`, add:

```python
class OrgEmployeeProbationCompleteView(APIView):
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg, OrgAdminMutationAllowed]

    def post(self, request, pk):
        organisation = _get_admin_organisation(request)
        employee = get_object_or_404(Employee, organisation=organisation, id=pk)
        employee.probation_end_date = None
        employee.save(update_fields=['probation_end_date', 'modified_at', 'modified_by'])
        log_audit_event(
            actor=request.user,
            verb='probation_completed',
            target=employee,
            organisation=organisation,
        )
        from apps.employees.serializers import EmployeeSerializer
        return Response(EmployeeSerializer(employee).data)
```

- [x] **Step 6: Register URL**

In `backend/apps/employees/urls.py`, add:

```python
from .views import OrgEmployeeProbationCompleteView

# Inside urlpatterns:
path('employees/<uuid:pk>/probation-complete/', OrgEmployeeProbationCompleteView.as_view()),
```

- [x] **Step 7: Run tests**

```bash
cd backend && python -m pytest apps/employees/tests/test_probation.py -v
```

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/apps/employees/models.py \
        backend/apps/employees/migrations/ \
        backend/apps/employees/views.py \
        backend/apps/employees/urls.py \
        backend/apps/employees/tests/test_probation.py
git commit -m "feat(employees): add probation_end_date field and probation-complete endpoint"
```

---

## Verification

```bash
cd backend && python -m pytest apps/payroll/tests/test_tasks.py apps/employees/tests/test_probation.py apps/timeoff/ -v
# Expected: all pass

python manage.py check
# Expected: System check identified no issues
```
