# P26 — Architecture & Performance Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the architectural and performance gaps identified in the v3 audit that don't belong to any feature module: API versioning (`/api/v1/`), missing DB indexes on high-traffic query paths, cost centre model for payroll allocation, and Celery idempotency keys to prevent double payroll calculation on broker redelivery.

**Architecture:** URL versioning is a one-shot structural change that must be coordinated with the frontend API client. DB indexes are additive migrations. Cost centre is a new model in `payroll` with a thin API. Celery idempotency uses task IDs stored in Redis.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · Redis · React 19 · TypeScript

---

## Audit Findings Addressed

- No API versioning — `/api/v1/` prefix absent (Gap #18)
- Missing DB indexes on `Employee(organisation, status, date_of_joining)` and `CompensationAssignment(employee, status, effective_from)` (§4.1)
- No cost centre model — payroll allocations cannot be split (Gap #17)
- No idempotency keys on Celery payroll calculation tasks (§4.1)
- `PayrollRun.items` returned inline in summary response — risk of large payload for 500+ employee orgs (§4.2)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/clarisal/urls.py` | Modify | Add `/api/v1/` prefix wrapper |
| `backend/apps/*/urls.py` (all app URL files) | Modify | Register under `/api/v1/` |
| `frontend/src/lib/api/*.ts` | Modify | Update base URL constant to `/api/v1/` |
| `backend/apps/payroll/models.py` | Modify | Add `CostCentre` model; add `cost_centre` FK to `CompensationTemplateLine` |
| `backend/apps/payroll/serializers.py` | Modify | Expose cost centre in template and assignment serializers |
| `backend/apps/payroll/views.py` | Modify | Cost centre CRUD endpoints |
| `backend/apps/payroll/org_urls.py` | Modify | Register cost centre routes |
| `backend/apps/payroll/migrations/0016_*.py` | Create | CostCentre model; missing indexes |
| `backend/apps/employees/migrations/0XXX_*.py` | Create | Employee covering index |
| `backend/apps/payroll/tasks.py` | Modify | Idempotency key guard on payroll calculation task |
| `backend/apps/payroll/tests/test_views.py` | Modify | Cost centre CRUD tests |
| `backend/apps/payroll/tests/test_services.py` | Modify | Idempotency test; payroll run items pagination test |

---

## Task 1: Add API Versioning (`/api/v1/`)

> **Audit finding (Gap #18, §4.1):** All API URLs lack a `/api/v1/` prefix. Adding a `/api/v2/` later will require changing URLs across all frontend clients and breaking any external integrations.

- [x] In `backend/clarisal/urls.py`, wrap all app `include()` calls under a `path('api/v1/', ...)` prefix. Keep the old unversioned paths alive as deprecated aliases returning a `410 Gone` or `301 Redirect` for a transition period — do NOT break existing frontend behaviour.
- [x] Update the frontend's API base URL constant in `frontend/src/lib/api/client.ts` (or wherever `axios`/`fetch` base URL is defined) from `/api/` to `/api/v1/`.
- [x] Update `CSRF_TRUSTED_ORIGINS` and any hardcoded API paths in frontend test mocks to use the new prefix.
- [x] Run the full backend test suite and frontend Vitest suite after the change to catch any missed URL references.
- [x] Add a `API_VERSION = "v1"` constant to `settings/base.py` so future version bumps are a one-line change.
- [x] Document the versioning policy in `CONTRIBUTING.md`: breaking changes require a new version prefix; additive changes are allowed within a version.

## Task 2: Add Missing DB Indexes

> **Audit finding (§4.1):** Two high-traffic query paths lack covering indexes:
> - `PayrollRun` scans all `ACTIVE` employees per org — needs `Employee(organisation, status, date_of_joining)`.
> - `get_effective_compensation_assignment` resolves via ordering — needs `CompensationAssignment(employee, status, effective_from)`.

- [x] Add the following indexes in a new migration:

```python
# In Employee model Meta or via AddIndex migration:
indexes = [
    models.Index(
        fields=["organisation", "status", "date_of_joining"],
        name="employee_org_status_doj_idx",
    ),
]

# In CompensationAssignment model Meta:
indexes = [
    models.Index(
        fields=["employee", "status", "effective_from"],
        name="comp_assign_emp_status_eff_idx",
    ),
]
```

- [x] Verify with `EXPLAIN ANALYZE` on a dev DB with 10,000+ employee rows that the payroll run query uses the new index. Regression coverage now lives in `backend/apps/payroll/tests/test_query_plans.py` and asserts `employee_org_status_doj_idx` and `comp_assign_emp_status_eff_idx` appear in the PostgreSQL execution plans.
- [x] Check `PayrollRunItem` — confirm the existing `(pay_run, employee)` composite index is already present (audit said it is); if not, add it.

## Task 3: Add Cost Centre Model

> **Audit finding (Gap #17, §2):** No cost centre entity exists. Payroll allocations cannot be split across departments, projects, or GL codes. SAP SuccessFactors has full cost centre split. This is needed for enterprises with multi-department payroll allocation reporting.

- [x] Add `CostCentre` model to `backend/apps/payroll/models.py`:

```python
class CostCentre(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="cost_centres")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    gl_code = models.CharField(max_length=50, blank=True)  # General Ledger integration reference
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("organisation", "code")]
```

- [x] Add `cost_centre = models.ForeignKey(CostCentre, null=True, blank=True, on_delete=models.SET_NULL)` to `CompensationTemplateLine` and `CompensationAssignmentLine`.
- [x] Add CRUD endpoints for `CostCentre` (org-admin only): list, create, update, deactivate. No delete — deactivate only to preserve historical references.
- [x] Expose `cost_centre` in payslip and run-item serializers so cost centre appears in the payroll run detail page and future GL export reports.
- [x] Add UI: a `CostCentresPage` (or section within the payroll Setup tab) for managing cost centres, and an optional cost centre selector on compensation template lines.
- [x] Cover CRUD, deactivation, and FK enforcement with tests.

## Task 4: Add Celery Idempotency Keys for Payroll Calculation

> **Audit finding (§4.1):** No idempotency keys on Celery tasks. Duplicate delivery from the broker could trigger double payroll calculation for the same pay run, resulting in duplicate `PayrollRunItem` records or double-applied TDS.

- [x] In `backend/apps/payroll/tasks.py`, add an idempotency guard at the start of the `calculate_payroll_run` task:

```python
@app.task(bind=True, max_retries=3)
def calculate_payroll_run(self, pay_run_id: str):
    lock_key = f"payroll:calc:lock:{pay_run_id}"
    # Acquire a Redis lock with 30-minute TTL
    if not cache.add(lock_key, self.request.id, timeout=1800):
        # Already running — idempotent: do nothing
        logger.info("Payroll calc already in progress", pay_run_id=pay_run_id)
        return
    try:
        # ... existing calculation logic ...
    finally:
        cache.delete(lock_key)
```

- [x] Set `CELERY_TASK_ACKS_LATE = True` in `settings/base.py` so tasks are only acknowledged after successful completion, enabling safe broker redelivery on worker crash.
- [x] Add a test verifying that calling `calculate_payroll_run.delay(run_id)` twice in rapid succession executes the calculation logic exactly once (use `mock.patch` on the lock acquire).
- [x] Verify existing payroll calculation tests still pass with the lock in place.

## Task 5: Paginate PayrollRun Items in Summary Response

> **Audit finding (§4.2):** `PayrollRun.items` is fetched inline in the payroll summary response. A run with 500 employees returns 500 items in a single response, causing slow loads and large payloads.

- [x] Audit the payroll summary serializer/view to confirm that `PayrollRunItem` records are being serialized inline.
- [x] Remove inline `items` from the payroll summary serializer. The `PayrollRunDetailPage` (P25) will fetch items via the dedicated paginated endpoint.
- [x] Update `PayrollPage.tsx` to stop expecting inline `items` in the summary response — it should show only aggregate counts (employee count, total gross, total net) which are cheap to compute and return.
- [x] Add `total_gross`, `total_net`, `total_deductions`, `employee_count`, and `exception_count` as computed annotations on the `PayrollRun` queryset using `Sum` and `Count` aggregations — serve these from the summary endpoint.
- [x] Cover the aggregated summary fields and the removal of inline items with API tests.
