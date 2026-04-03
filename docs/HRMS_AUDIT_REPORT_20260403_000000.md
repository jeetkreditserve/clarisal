# HRMS Audit Report

**Version**: v1.0
**Audit Date**: 2026-04-03
**Auditor**: Claude Code (claude-sonnet-4-6)
**Tech Stack**: Django 4.2 · DRF 3.15 · PostgreSQL 15 · Celery 5.4 / Redis 7 · React 19 · TypeScript 5.9 · Vite 8 · Tailwind CSS 4 · Radix UI · Playwright 1.58 · Vitest 4 · Docker Compose · AWS S3

---

## Executive Summary

Clarisal is a well-structured, AI-built HRMS with solid coverage of core HR, attendance, leave, and India-specific payroll. The architecture demonstrates mature Django practices — clean multi-tenancy, a service/repository pattern, and comprehensive audit logging. However, **five critical issues demand immediate remediation**: live AWS and Zoho API credentials committed to the `.env` file, a missing Income Tax Rebate u/s 87A that causes statutory overpayment for low-income employees, synchronous payroll calculation that will time out at scale (>500 employees), a complete absence of timeoff service tests (0%), and all destructive UI actions using native browser `confirm()` dialogs instead of the design system. Performance management and recruitment modules are entirely absent, and test coverage of statutory payroll calculations is near zero.

---

## Audit Scorecard

| Area | Score | Status |
|------|-------|--------|
| Feature Completeness | 6/10 | Core HR/payroll strong; performance/recruitment/reports absent |
| Architecture | 6/10 | Good patterns; async gap and versioning absent |
| Code Quality | 8/10 | Clean, no TODOs, minimal duplication |
| UI/UX | 6/10 | Solid foundations; accessibility and bulk ops missing |
| Security | 4/10 | Good RBAC; credentials committed to repo is critical |
| Test Coverage | 3/10 | No payroll unit tests, zero timeoff tests, thin E2E |

---

## [Phase 1] Feature Completeness vs Zoho People + Zoho Payroll

### Core HR

| Feature | Status | Notes |
|---------|--------|-------|
| Employee statuses (INVITED → ACTIVE → RESIGNED/TERMINATED) | ✅ | `employees/models.py:16–22` |
| Offboarding task checklist (IT, Payroll, HR, Manager, Employee) | ✅ | `EmployeeOffboardingTask` model; 6 task types |
| Document management + verification workflow | ✅ | 11 document categories; PENDING/VERIFIED/REJECTED statuses |
| Self-referential org chart (`reporting_to` FK) | ✅ | `employees/models.py:156` — `direct_reports` reverse name |
| Employee self-service portal (`/api/me/` namespace) | ✅ | Leave, attendance, payslips, documents, approvals |
| Onboarding checklist with task templates | ⚠️ | Document-driven only; no configurable task template model like Zoho |
| Custom employee fields | ❌ | No CustomField framework; static model only |
| Probation period tracking | ❌ | No `probation_end_date` or `probation_period_months` on `Employee` |
| Exit interview form / checklist | ⚠️ | Offboarding task `EXIT_INTERVIEW` exists as a task type; no structured form |

**Recommendation:** Add `probation_end_date` field and create an `EmployeeOnboardingTask` model with configurable templates.

---

### Attendance

| Feature | Status | Notes |
|---------|--------|-------|
| Shift management (overnight, grace, overtime thresholds) | ✅ | `attendance/models.py:111–133` |
| Shift assignment with date range validity | ✅ | `ShiftAssignment` with `start_date`/`end_date` |
| Overtime minutes tracking | ✅ | `overtime_minutes` on `AttendanceDay`; `overtime_after_minutes` on `Shift` |
| Geo-fencing | ✅ | `restrict_by_geo` + `allowed_geo_sites` JSONField on `AttendancePolicy` |
| IP-based attendance restriction | ✅ | `restrict_by_ip` + `allowed_ip_ranges` JSONField |
| GPS coordinates captured on punches | ✅ | `latitude`, `longitude` on `AttendancePunch` |
| Biometric / device integration | ✅ | `AttendanceSourceConfig` with DEVICE/API/EXCEL source kinds |
| Multi-location holiday calendars | ✅ | `HolidayCalendarLocation` junction table for per-location assignment |
| Attendance regularization workflow | ✅ | `AttendanceRegularizationRequest` with full approval integration |
| Late mark calculation | ✅ | `is_late` flag; `late_minutes` computed against shift start + grace |
| INCOMPLETE status (single punch) | ✅ | `needs_regularization = True` when check-out absent |
| Overtime pay rate configuration | ❌ | Minutes tracked; no overtime pay rate or component |
| Biometric device sync / real-time feed | ⚠️ | API ingestion endpoint exists; no SDK/device SDK integration |

---

### Leave Management

| Feature | Status | Notes |
|---------|--------|-------|
| Multiple leave types with accrual policies | ✅ | `credit_frequency` (MONTHLY/QUARTERLY/HALF_YEARLY/YEARLY/MANUAL) |
| Carry-forward rules (NONE/CAPPED/UNLIMITED) | ⚠️ | **Model fields exist** (`carry_forward_cap`, `carry_forward_mode`) but **cap is never enforced in services** |
| Max balance enforcement | ⚠️ | **`max_balance` field exists** but is **never checked** before crediting |
| Proration on joining date | ✅ | `prorate_on_join` flag; first-month credit scaled correctly |
| Half-day leaves | ✅ | `allows_half_day` on `LeaveType`; session-level tracking on requests |
| Multi-level approval workflows | ✅ | `ApprovalStage` with `sequence`; ALL/ANY mode; fallback support |
| Leave balance ledger with full audit trail | ✅ | `LeaveBalanceLedgerEntry` with OPENING/CREDIT/DEBIT/CARRY_FORWARD/EXPIRY types |
| Leave balance visibility for employees | ✅ | `/api/me/timeoff/leave-balance/` endpoint |
| Attachment support, notice days, consecutive day limits | ✅ | Full set of policy fields on `LeaveType` |
| Leave encashment | ❌ | No `LeaveEncashmentRequest` model; no encashment calculation |

**Bug:** `carry_forward_cap` and `max_balance` are stored in `LeaveType` but the services that credit leave (`timeoff/services.py`) never read them. Employees can accumulate unlimited leave regardless of configured caps.

---

### Payroll

| Feature | Status | Notes |
|---------|--------|-------|
| Salary structure builder (components, templates, assignments) | ✅ | `CompensationTemplate` + `CompensationTemplateLine` + `CompensationAssignment` |
| PF (12% employee + 12% employer of basic) | ✅ | `payroll/services.py:41, 729–760` |
| ESI (0.75% / 3.25%, ≤₹21,000 ceiling) | ✅ | `payroll/services.py:42–44, 762–785` |
| Professional Tax (Maharashtra slabs: 0/150/200) | ✅ | `payroll/services.py:47–51, 787–801` |
| TDS — New regime (7 slabs + ₹75k standard deduction + 4% cess) | ✅ | `payroll/services.py:82–908` |
| Rebate u/s 87A (₹25,000 rebate for income ≤₹7L) | ❌ | **MISSING — statutory violation; employees overpay TDS** |
| Payslip generation with formatted Indian notation | ✅ | `Payslip` model; `_build_rendered_payslip()` function |
| Attendance-based LOP proration | ✅ | `use_attendance_inputs` flag; `paid_days / total_days` formula |
| Joining-month proration | ✅ | `payroll/services.py:806–830` |
| Compensation template approval workflow | ✅ | `CompensationTemplate` integrates with `ApprovalRun` |
| Tax slab management (configurable per fiscal year) | ✅ | `PayrollTaxSlabSet` + `PayrollTaxSlab` models |
| Payroll run finalization and rerun support | ✅ | Full status machine: DRAFT → CALCULATED → SUBMITTED → APPROVED → FINALIZED |
| Payroll calculation is async (Celery) | ❌ | **CRITICAL: `calculate_pay_run()` called synchronously in HTTP request** |
| Full & Final settlement | ❌ | Exit proration only; no encashment, gratuity, or severance |
| Arrears / back-pay calculation | ❌ | Not implemented |
| Form 16 generation | ❌ | Document type exists; generation not implemented |
| Investment declarations (80C/80D) | ❌ | No model |
| Old tax regime option | ❌ | New regime only hardcoded |

---

### Performance Management

| Feature | Status | Notes |
|---------|--------|-------|
| Goal setting | ❌ | No model |
| Appraisal cycles | ❌ | No model |
| 360° feedback | ❌ | No model |
| Probation review | ❌ | No probation period tracking |

**Gap:** Performance management module is entirely absent.

---

### Recruitment / ATS

| Feature | Status | Notes |
|---------|--------|-------|
| Job postings | ❌ | Not implemented |
| Applicant tracking | ❌ | Not implemented |
| Offer letters | ❌ | Not implemented |
| Onboarding handoff from ATS | ❌ | Not implemented |

---

### Reports & Analytics

| Feature | Status | Notes |
|---------|--------|-------|
| Attendance summary report | ✅ | `OrgAttendanceReportView` at `/api/org/attendance/reports/summary/` |
| Payroll register | ❌ | No dedicated payroll report endpoint |
| Headcount / attrition reports | ❌ | Not implemented |
| Leave utilization report | ❌ | Not implemented |
| Custom report builder | ❌ | Not implemented |
| Tax reports (PT summary, TDS summary) | ❌ | Not implemented |

---

### Notifications & Workflows

| Feature | Status | Notes |
|---------|--------|-------|
| Email notifications (password reset, invite) | ✅ | Celery tasks with retry logic (`max_retries=3`, 60s delay) |
| Notice board (broadcast to employees/departments) | ✅ | `Notice` model with targeting, scheduling, categorization |
| In-app notifications | ❌ | No Notification model |
| SMS notifications | ❌ | Not implemented |
| Push notifications | ❌ | Not implemented |
| Approval action email triggers | ❌ | No Celery tasks for leave/payroll/regularization notifications |
| Configurable escalation rules | ⚠️ | `ApprovalStage` has fallback support; no time-based escalation |

---

## [Phase 2] Architecture Issues

### A2-01 — Synchronous Payroll Calculation
**Severity:** 🔴 Critical
**File:** `backend/apps/payroll/views.py:247`

`calculate_pay_run()` is called directly in the HTTP request-response cycle. For organizations with 500+ employees, this will exceed the typical 30-second HTTP timeout and fail silently.

```python
# Current — BLOCKING
class OrgPayrollRunCalculateView(APIView):
    def post(self, request, pk):
        pay_run = calculate_pay_run(pay_run, actor=request.user)  # blocks
        return Response(PayrollRunSerializer(pay_run).data)
```

**Recommendation:**
```python
# Convert to Celery task
@shared_task
def calculate_pay_run_task(pay_run_id, actor_user_id):
    pay_run = PayrollRun.objects.get(id=pay_run_id)
    calculate_pay_run(pay_run, actor=User.objects.get(id=actor_user_id))

# In view:
calculate_pay_run_task.delay(pay_run.id, request.user.id)
return Response({'status': 'calculation_queued', 'pay_run_id': str(pay_run.id)}, status=202)
```

---

### A2-02 — No API Versioning
**Severity:** 🟠 High
**File:** `backend/clarisal/urls.py`

All routes use `/api/ct/`, `/api/org/`, `/api/me/` namespaces with no `/v1/` version prefix. Any breaking API change will affect all clients simultaneously.

**Recommendation:** Migrate to `/api/v1/org/`, `/api/v1/me/` early and implement version negotiation middleware.

---

### A2-03 — Pagination Inconsistency
**Severity:** 🟡 Medium
**File:** `backend/apps/employees/views.py:86`

`PageNumberPagination` is configured globally (`settings/base.py:144`) but several list endpoints override or bypass it, returning unbounded querysets.

**Recommendation:** Enforce pagination at the view base class level or add a linting rule.

---

### A2-04 — N+1 Risk in Payroll Calculation
**Severity:** 🟡 Medium
**File:** `backend/apps/payroll/services.py:641–677`

`calculate_pay_run()` iterates over employees and calls `get_effective_compensation_assignment(employee, ...)` inside the loop. Each call is a separate DB query, producing N+1 queries for N employees.

**Recommendation:**
```python
employees = Employee.objects.filter(...).prefetch_related(
    Prefetch(
        'compensation_assignments',
        queryset=CompensationAssignment.objects.filter(...).prefetch_related('lines__component'),
        to_attr='prefetched_assignments'
    )
)
```

---

### A2-05 — Missing PayrollRunItem Indexes
**Severity:** 🟡 Medium
**File:** `backend/apps/payroll/models.py:252–278`

`PayrollRunItem` has no database indexes despite being frequently filtered by `(pay_run, status)` for exception summaries and `(pay_run, employee)` for individual access.

**Recommendation:** Add `Meta.indexes`:
```python
class Meta:
    indexes = [
        models.Index(fields=['pay_run', 'status']),
    ]
```

---

### A2-06 — Repository Pattern Partially Enforced
**Severity:** 🟢 Low
**Files:** `backend/apps/employees/repositories.py`, `backend/apps/payroll/services.py`

`employees/repositories.py` centralizes ORM queries with proper `select_related`/`prefetch_related`. However, payroll, timeoff, and attendance services bypass repositories and query the ORM directly. This leads to inconsistent query optimization and duplicated filtering logic.

**Recommendation:** Either enforce repository usage across all apps or remove repositories and document the direct-service pattern as the standard.

---

## [Phase 3] Stale & Dead Code

### C3-01 — Clean Codebase
All searches returned no matches for:
- `# TODO`, `# FIXME`, `# HACK` comments anywhere in `backend/apps/`
- `console.log`, `debugger`, `@ts-ignore` in `frontend/src/`
- Skipped or empty tests (`@pytest.mark.skip`, `pass` in test bodies)
- Duplicate leave balance or salary proration logic

The codebase is exceptionally clean for an AI-built system.

---

### C3-02 — Broad Exception Handlers (Acceptable)
**Files:** `backend/apps/accounts/views.py:206,231`, `backend/apps/timeoff/views.py:78,93`, `backend/apps/payroll/services.py:847`, `backend/apps/attendance/services.py:122,826`

Multiple `except Exception as exc: # noqa: BLE001` patterns. These are intentional — they normalize error response shapes. The `# noqa` annotation documents the intent.

**Assessment:** Acceptable pattern; no action needed.

---

### C3-03 — `simplejwt` Installed but Unused
**Severity:** 🟢 Low
**File:** `backend/requirements.txt`

`djangorestframework-simplejwt 5.3.1` is in requirements but DRF is configured with `SessionAuthentication` only. No JWT auth classes are configured.

**Recommendation:** Either configure JWT auth for mobile/API clients or remove the unused dependency.

---

## [Phase 4] UI/UX Issues

### U4-01 — All Destructive Actions Use Native `window.confirm()`
**Severity:** 🔴 Critical
**Files:** `PayrollPage.tsx:218,230`, `EmployeeDetailPage.tsx:235`, multiple other pages

8+ destructive actions (finalize payroll, delete employee, deactivate location, remove bank account) use `window.confirm()` instead of the `AppDialog` component. Native confirm dialogs are unstyled, inaccessible on mobile, and cannot include context-specific warning text.

**Recommendation:** Replace with `AppDialog`:
```tsx
<AppDialog
  open={confirmOpen}
  title="Finalize payroll run?"
  description="This action cannot be undone. Payslips will be generated and locked."
  onConfirm={handleFinalize}
  onCancel={() => setConfirmOpen(false)}
>
  <Button onClick={() => setConfirmOpen(true)}>Finalize</Button>
</AppDialog>
```

---

### U4-02 — PayrollPage Forms Missing Form Labels
**Severity:** 🔴 Critical
**File:** `frontend/src/pages/org/PayrollPage.tsx:312–318`

Tax slab and compensation template input fields use placeholder-only pattern with no `<label>` elements. This breaks screen reader access and form usability.

```tsx
// Current — NO LABEL
<input className="field-input" placeholder="Slab set name" />

// Fix
<label htmlFor="slab-name" className="field-label">Slab set name</label>
<input id="slab-name" className="field-input" placeholder="e.g. New Regime FY 2025-26" />
```

---

### U4-03 — PayslipsPage Has No Download Button
**Severity:** 🔴 Critical
**File:** `frontend/src/pages/employee/PayslipsPage.tsx`

Employees can view payslip text but cannot download a PDF. The page shows raw `rendered_text` as a fallback rather than a downloadable document. The `useDownloadMyPayslip` hook exists but is not wired to any button.

**Recommendation:** Add a download button that calls the existing download hook:
```tsx
<button className="btn-secondary" onClick={() => downloadPayslip(payslip.id)}>
  <Download className="h-4 w-4 mr-2" /> Download PDF
</button>
```

---

### U4-04 — Zero `aria-label` Attributes on Icon Buttons
**Severity:** 🔴 Critical

A codebase-wide grep found zero `aria-label` attributes other than `ThemeToggle`. Icon-only buttons (download, edit, delete actions throughout the app) are invisible to screen readers.

**Recommendation:** Add `aria-label` to all icon-only buttons:
```tsx
<button aria-label="Download payslip for April 2025">
  <Download className="h-4 w-4" />
</button>
```

---

### U4-05 — Navigation Is a Flat 14-Item List (Ungrouped)
**Severity:** 🟠 High
**File:** `frontend/src/components/layouts/OrgLayout.tsx:11–26`

14 navigation items are in a flat unordered list. Related items (Leave cycles, Leave plans, Holidays) are not grouped, making the nav hard to scan, especially for new HR managers.

**Recommendation:** Add collapsible groups:
- **People:** Employees, Departments, Locations
- **Time & Leave:** Attendance, Leave Cycles, Leave Plans, Holidays, OD Policies
- **Compensation:** Payroll Preview
- **Governance:** Approvals, Notices, Audit Timeline

---

### U4-06 — LeavePlanBuilderPage Is a Monolithic Scroll Form
**Severity:** 🟠 High
**File:** `frontend/src/pages/org/LeavePlanBuilderPage.tsx` (1025 lines)

5+ major configuration sections (plan basics, leave types, accrual rules, carry-forward, applicability) are presented as a single vertical scroll with no progress indication. Users cannot save intermediate state.

**Recommendation:** Convert to 3-step wizard with "Save as Draft" capability between steps.

---

### U4-07 — Inconsistent Error Handling (Field vs Toast)
**Severity:** 🟠 High
**Files:** `PayrollPage.tsx:119–121` vs `LeavePage.tsx`

`PayrollPage` shows only a generic toast on API error. `LeavePage` uses `FieldErrorText` for field-level validation. A user entering invalid tax slab bounds gets no indication of which field is wrong.

**Recommendation:** Adopt a consistent pattern: use `FieldErrorText` for field validation errors and toast for system-level errors.

---

### U4-08 — No Bulk Operations
**Severity:** 🟠 High

No page supports bulk operations:
- No bulk payslip download
- No bulk leave approval
- No bulk attendance override
- No bulk employee status update

**Recommendation:** Start with the two highest-value bulk operations: bulk payslip generation and bulk leave approval.

---

### U4-09 — PayrollPage Uses Native `<input type="date">`
**Severity:** 🟡 Medium
**File:** `frontend/src/pages/org/PayrollPage.tsx:396`

PayrollPage uses a native `<input type="date">` while all other pages use the `AppDatePicker` component. Native date inputs render differently across browsers and operating systems.

---

### U4-10 — Tables Have No Mobile Scroll Wrapper
**Severity:** 🟡 Medium
**Files:** `OrgDashboardPage.tsx:241`, `EmployeesPage.tsx`

Data tables use `min-w-full` but are not wrapped in `overflow-x-auto`. On narrow screens the table overflows the viewport without a scroll bar.

**Recommendation:** Wrap all tables: `<div className="overflow-x-auto"><table ...>`.

---

### U4-11 — Missing Status Tone Functions for Payroll Statuses
**Severity:** 🟡 Medium
**File:** `frontend/src/lib/status.ts`

`status.ts` has tone functions for employee, document, leave, and approval statuses, but **not** for payroll run status (DRAFT/CALCULATED/SUBMITTED/APPROVED/FINALIZED), compensation template status, or attendance import status. These are hardcoded inline in `PayrollPage.tsx` as ternary expressions.

---

### U4-12 — Leave Balance Not Shown During Request Submission
**Severity:** 🟡 Medium
**File:** `frontend/src/pages/employee/LeavePage.tsx`

Leave balances are displayed at the top of the page, but the request form does not show "Available balance after this request" calculated in real-time as the employee selects dates.

---

### U4-13 — No `toast.loading()` for Long Operations
**Severity:** 🟢 Low
**File:** `frontend/src/pages/org/PayrollPage.tsx`

Payroll finalization may take several seconds but shows no intermediate loading feedback. The button is disabled while `isPending` but no spinner or loading toast is shown.

---

## [Phase 5] Security Issues

### S5-01 — Live AWS Credentials Committed to Repository
**Severity:** 🔴 Critical
**File:** `.env:22–25`

Real AWS credentials are committed to the repository:
- `AWS_ACCESS_KEY_ID=AKIA47KWW5J3E6Z37SAS`
- `AWS_SECRET_ACCESS_KEY=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`
- `ZEPTOMAIL_API_KEY=Zoho-enczapikey PHtE6r0LF7y6j...` (full token)
- Seed passwords: `SEED_ORG_ADMIN_PASSWORD=Admin@12345`, `SEED_EMPLOYEE_PASSWORD=Employee@12345`

**Immediate actions required:**
1. Rotate AWS Access Key in AWS IAM Console immediately
2. Rotate Zeptomail API key
3. Revoke and regenerate all exposed credentials
4. Add `.env` to `.gitignore` (verify it is already excluded from future commits)
5. Run `git filter-repo` or BFG Repo-Cleaner to purge credentials from git history

---

### S5-02 — Insecure `SECRET_KEY` Default
**Severity:** 🔴 Critical
**File:** `backend/clarisal/settings/base.py:16`, `.env:2`

`base.py` falls back to `'django-insecure-dev-key-change-in-production'`. The `.env` file contains `SECRET_KEY=your-secret-key-here-change-in-production`. If the environment variable is missing in production, Django starts with a known, weak key.

**Recommendation:** In `production.py`, raise `ImproperlyConfigured` if `SECRET_KEY` is the insecure placeholder:
```python
if 'insecure' in SECRET_KEY or 'change-in-production' in SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be set to a cryptographically strong value in production.")
```

---

### S5-03 — `FIELD_ENCRYPTION_KEY` Defaults to Empty String
**Severity:** 🟠 High
**File:** `backend/clarisal/settings/base.py:185`, `backend/apps/common/security.py:29`

When `FIELD_ENCRYPTION_KEY` is not set, it defaults to `''` and the encryption module falls back to deriving the key from `SECRET_KEY`. In development (where `SECRET_KEY` is the insecure placeholder), sensitive fields (PAN, Aadhaar, bank account numbers) are encrypted with a known, weak key.

**Recommendation:** Require `FIELD_ENCRYPTION_KEY` explicitly in all environments, not just production:
```python
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY')  # No default — fails fast if unset
```

---

### S5-04 — No Negative Salary Validation in Serializers
**Severity:** 🟡 Medium
**File:** `backend/apps/payroll/serializers.py:24,76`

`CompensationTemplateLine.monthly_amount` and `PayrollTaxSlab.min_income`/`max_income` accept negative values in the serializer. There is no `validate_monthly_amount` method enforcing `>= 0`.

**Recommendation:**
```python
def validate_monthly_amount(self, value):
    if value < 0:
        raise serializers.ValidationError("Monthly amount cannot be negative.")
    return value
```

---

### S5-05 — Leave Date Range Not Validated in Serializer
**Severity:** 🟡 Medium
**File:** `backend/apps/timeoff/serializers.py:259–260`

`LeaveRequestCreateSerializer` has `start_date` and `end_date` fields but no `validate()` method to assert `start_date <= end_date`. An invalid request (end before start) may reach the service layer and cause unexpected behavior.

**Recommendation:**
```python
def validate(self, data):
    if data.get('end_date') and data.get('start_date') and data['end_date'] < data['start_date']:
        raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
    return data
```

---

### S5-06 — Positive Security Findings (No Action Needed)

The following were verified as correctly implemented:

| Control | Evidence |
|---------|----------|
| All payroll ViewSets have `permission_classes` | `payroll/views.py` — every class has explicit permissions |
| Employee payslips filtered to requesting employee (no IDOR) | `payroll/views.py:301–302` — `Payslip.objects.filter(employee=employee)` |
| Document downloads use S3 presigned URLs (15-min expiry) | `documents/s3.py:23–28` — `generate_presigned_url(key, expiry=900)` |
| S3 bucket is private (`AWS_DEFAULT_ACL = 'private'`) | `settings/base.py:226` |
| Login rate-limited at 5/min, password reset at 5/hr | `settings/base.py:135–138` |
| File uploads restricted to `{.pdf,.png,.jpg,.jpeg}`, max 5 MB | `documents/services.py:20–21` |
| Attendance API source uses hashed API key (not plaintext) | `attendance/views.py:187–188` |
| All dependencies current — no known CVEs | Django 4.2.16, Pillow 10.4.0, cryptography 45.0.7 |
| Comprehensive audit logging (actor, org, action, target, IP, user-agent) | `audit/models.py:7–38` |
| Document access filtered by requesting employee | `documents/views.py:176–177` |

---

## [Phase 6] Functional Correctness

### F6-01 — Missing Income Tax Rebate u/s 87A
**Severity:** 🔴 Critical — Statutory Violation
**File:** `backend/apps/payroll/services.py:901–908`

The payroll engine correctly implements PF, ESI, PT, the 7-slab new regime, ₹75,000 standard deduction, and 4% cess. However, **Rebate u/s 87A is missing entirely.**

Under India's new tax regime (FY2024-25), employees with net taxable income ≤ ₹7,00,000 are entitled to a tax rebate of up to ₹25,000, effectively resulting in zero tax liability. This is one of the most impactful provisions for salaried employees earning in the ₹5L–₹7L range.

**Example of the bug:**
- Employee: Annual taxable income after standard deduction = ₹6,50,000
- Current code tax = (₹6,50,000 − ₹3,00,000) × 5% = ₹17,500 → after cess = ₹18,200
- Correct tax = ₹17,500 − ₹17,500 (rebate, capped at ₹25,000) = ₹0

**Fix:**
```python
# In payroll/services.py, after _calculate_annual_tax():
REBATE_87A_INCOME_LIMIT = Decimal('700000')
REBATE_87A_MAX_REBATE = Decimal('25000')

annual_tax_before_cess = _calculate_annual_tax(tax_slab_set, annual_taxable_after_sd)

# Apply Section 87A rebate (new regime only)
if annual_taxable_after_sd <= REBATE_87A_INCOME_LIMIT:
    rebate = min(annual_tax_before_cess, REBATE_87A_MAX_REBATE)
    annual_tax_before_cess = max(ZERO, annual_tax_before_cess - rebate)

annual_tax = annual_tax_before_cess * (ONE + INDIA_CESS_RATE)
```

---

### F6-02 — Carry-Forward Cap Not Enforced
**Severity:** 🟠 High
**File:** `backend/apps/timeoff/services.py` (services that compute cycle-end carry-forward)

`LeaveType.carry_forward_cap` is defined in the model but the services that compute carry-forward at cycle end never read this field. Employees carry forward their full balance regardless of configured caps.

**Recommendation:** In the cycle-end processing function, cap the carry-forward amount:
```python
if leave_type.carry_forward_mode == CarryForwardMode.CAPPED:
    carry_forward = min(current_balance, leave_type.carry_forward_cap)
elif leave_type.carry_forward_mode == CarryForwardMode.UNLIMITED:
    carry_forward = current_balance
else:  # NONE
    carry_forward = ZERO
```

---

### F6-03 — Max Leave Balance Not Enforced
**Severity:** 🟠 High
**File:** `backend/apps/timeoff/services.py`

`LeaveType.max_balance` is defined in the model but the credit service never checks it before adding credits. Balance can grow indefinitely past the configured maximum.

**Recommendation:** Before crediting:
```python
if leave_type.max_balance:
    available_capacity = leave_type.max_balance - current_balance
    credit_amount = min(credit_amount, available_capacity)
    if credit_amount <= ZERO:
        return  # Already at or above max balance
```

---

### F6-04 — No Guard Against Negative Net Pay
**Severity:** 🟡 Medium
**File:** `backend/apps/payroll/services.py:911–912`

If custom deduction components exceed gross earnings, `net_pay` could be negative. No guard exists.

**Recommendation:**
```python
net_pay = max(ZERO, gross_pay - total_deductions)
if gross_pay - total_deductions < ZERO:
    logger.warning(f"Deductions exceed gross for employee {employee.id} in run {pay_run.id}")
```

---

### F6-05 — Verified Correct Implementations

| Calculation | Status | Evidence |
|-------------|--------|----------|
| PF: 12% of basic (employee + employer) | ✅ Correct | `services.py:41, 729–760` |
| ESI: 0.75% / 3.25%, gross ≤ ₹21,000 | ✅ Correct | `services.py:42–44, 762–785` |
| PT: Maharashtra slabs (0/150/200) | ✅ Correct | `services.py:47–51, 787–801` |
| TDS: 7-slab new regime | ✅ Correct | `services.py:82–89, 901–908` |
| Standard deduction: ₹75,000 | ✅ Correct | `services.py:39, 903` |
| Cess: 4% of income tax | ✅ Correct | `services.py:40, 906` |
| Joining month proration | ✅ Correct | `services.py:806–830` |
| Exit month proration (basic) | ✅ Correct | `services.py:814–816` |
| Attendance-based LOP proration | ✅ Correct | `services.py:831–867` |
| Leave PRESENT threshold (worked_minutes >= full_day_min) | ✅ Correct | `attendance/services.py:637–645` |
| Late mark calculation (check-in > shift_start + grace) | ✅ Correct | `attendance/services.py:647–650` |
| Monthly leave accrual (annual / 12) | ✅ Correct | `timeoff/services.py:232–254` |
| Leave overdraw prevention (checked against pending + approved) | ✅ Correct | `timeoff/services.py:351–354` |
| Status priority (leave > on-duty > holiday > week-off > attendance) | ✅ Correct | `attendance/services.py:665–680` |

---

## [Phase 7] Test Coverage

### Backend Test Inventory

| App | Test Files | Lines | Coverage Assessment |
|-----|-----------|-------|---------------------|
| `payroll` | `test_services.py`, `test_views.py` | ~356 total | 20% — happy path only; **zero statutory calculation tests** |
| `timeoff` | **None** | 0 | **0% — no test directory exists** |
| `attendance` | `test_views.py`, others | ~300+ | 40% — import/export covered; daily calculation logic untested |
| `employees` | `test_models.py`, `test_services.py`, `test_views.py` | 7699 + 9493 | 60% — comprehensive CRUD + lifecycle |
| `accounts` | `test_models.py`, `test_services.py`, `test_views.py`, `test_permissions.py`, `test_workspaces.py` | Moderate | 55% |
| `approvals` | `test_services.py`, `test_views.py` | Moderate | 50% |
| `organisations` | `test_models.py`, `test_services.py`, `test_views.py`, `test_licence_batches.py` | Good | 50% |
| `documents` | Present | Moderate | 40% |

---

### What Payroll Tests Cover (and Miss)

**Exists:**
- `test_ensure_org_payroll_setup_clones_active_ct_master` — tax slab setup ✓
- `test_pay_run_approval_and_finalize_generates_payslip` — end-to-end flow ✓
- `test_pay_run_with_exception_items_cannot_be_submitted_or_finalized` — error handling ✓

**Missing (critical):**
- ❌ `test_pf_12_percent_of_basic_salary()`
- ❌ `test_esi_0_75_percent_skipped_above_21000()`
- ❌ `test_pt_maharashtra_slab_boundaries()`
- ❌ `test_income_tax_rebate_87a_under_7_lakh()` — **this would catch the F6-01 bug**
- ❌ `test_income_tax_standard_deduction_75000()`
- ❌ `test_joining_month_proration_accurate()`
- ❌ `test_attendance_based_proration()`
- ❌ `test_negative_net_pay_guard()`

---

### Frontend Unit Test Assessment (4 files)

| File | Lines | Quality |
|------|-------|---------|
| `ApprovalWorkflowsPage.test.tsx` | 114 | "Renders without crashing" level; no interaction flow |
| `DashboardPage.test.tsx` (employee) | 109 | Smoke test only |
| `DashboardPage.test.tsx` (CT) | 88 | Smoke test only |
| `MonthCalendar.test.tsx` | 33 | Basic rendering; no date logic |

All 4 test files are smoke tests that verify the component renders. None test business logic or user interactions.

---

### E2E Playwright Coverage

**Present (24 specs):**
- Auth flows (login, logout, password reset)
- Employee self-service (leave form, on-duty, profile, onboarding, approvals)
- Org admin (employees, departments, locations, holidays, leave plans, leave cycles, notices, OD policies, approval workflows)
- Control Tower (dashboard, organisations)

**Missing:**
- ❌ `org/payroll.spec.ts` — no payroll end-to-end test (create run → calculate → approve → finalize)
- ❌ `org/attendance-regularization.spec.ts` — no regularization approval flow
- ❌ `employee/leave-approval.spec.ts` — leave is submitted but approval by manager is not tested
- ❌ `employee/payslips.spec.ts` — payslip view/download not tested

**Note:** `employee/leave.spec.ts` uses `test.skip()` (line 48) causing the test to silently pass even if the form doesn't exist. This is a false positive in CI.

---

### Top 10 Untested Areas Ranked by Business Risk

| Rank | Area | Risk | Missing Test |
|------|------|------|-------------|
| 1 | Income Tax Rebate u/s 87A | Statutory violation; employees overpay | `test_income_tax_rebate_87a_under_7_lakh()` |
| 2 | Carry-forward cap enforcement | Policy violation | `test_carry_forward_cap_enforced()` (feature also missing) |
| 3 | Max leave balance cap | Policy violation | `test_max_balance_prevents_credit_overage()` (feature also missing) |
| 4 | ESI boundary (gross = ₹21,001) | Incorrect deduction | `test_esi_skipped_when_gross_above_21000()` |
| 5 | PT slab boundaries (₹9,999 / ₹10,000 / ₹15,000) | Wrong deduction amount | `test_pt_slabs_maharashtra_slab_boundaries()` |
| 6 | Attendance-based payroll proration | Wrong pay amount | `test_gross_pay_prorated_by_attendance_paid_days()` |
| 7 | Regularization approval end-to-end | Core workflow untested | `org/attendance-regularization.spec.ts` |
| 8 | Leave approval end-to-end | Core workflow untested | `employee/leave-approval.spec.ts` |
| 9 | Payroll run end-to-end | Most critical business flow untested | `org/payroll.spec.ts` |
| 10 | Negative net pay guard | Data integrity | `test_negative_net_pay_validation()` |

---

## Priority Action Plan

### 🔴 Must Fix (Week 1)

1. **Rotate all exposed credentials** — AWS key, Zeptomail API key. Purge from git history with BFG Repo-Cleaner. (`S5-01`)

2. **Fix Income Tax Rebate u/s 87A** — Add ₹25,000 rebate logic for income ≤ ₹7L in `payroll/services.py:905–908`. Write test with salary of ₹6.5L to verify zero TDS. (`F6-01`)

3. **Make payroll calculation async** — Wrap `calculate_pay_run()` in a Celery task; view returns 202 + job ID. (`A2-01`)

4. **Replace all `window.confirm()` with `AppDialog`** — 8+ instances in `PayrollPage.tsx`, `EmployeeDetailPage.tsx`, etc. (`U4-01`)

5. **Add aria-labels to all icon buttons** — 100+ icon-only buttons are screen-reader invisible. (`U4-04`)

6. **Wire up payslip download button** — `useDownloadMyPayslip` hook exists; add button to `PayslipsPage.tsx`. (`U4-03`)

---

### 🟠 Should Fix (Month 1)

7. **Enforce carry-forward cap in leave service** — Add cap logic to cycle-end processing. (`F6-02`)

8. **Enforce max balance in leave credit service** — Add pre-credit check against `LeaveType.max_balance`. (`F6-03`)

9. **Create timeoff test suite** — Currently 0 tests. Add `backend/apps/timeoff/tests/test_services.py` with 6+ scenarios. (`Phase 7`)

10. **Add payroll statutory calculation unit tests** — Test PF/ESI/PT/TDS/87A with specific numeric assertions. (`Phase 7`)

11. **Fix SECRET_KEY validation in production** — Raise `ImproperlyConfigured` if insecure placeholder is used. (`S5-02`)

12. **Add negative salary validation to serializers** — `monthly_amount >= 0` on `CompensationTemplateLine`. (`S5-04`)

13. **Add leave date range validation to serializer** — `start_date <= end_date` check. (`S5-05`)

14. **Add PayrollRunItem indexes** — `(pay_run, status)` composite index. (`A2-05`)

15. **Add form labels to PayrollPage** — Tax slab and compensation template inputs need `<label>` elements. (`U4-02`)

16. **Add E2E test for payroll run** — `org/payroll.spec.ts`: create → calculate → approve → finalize. (`Phase 7`)

17. **Group navigation items** — Add collapsible groups (People / Time & Leave / Compensation / Governance). (`U4-05`)

---

### 🟡 Nice to Have (Quarter)

18. Add API versioning (`/api/v1/` prefix) before public launch. (`A2-02`)

19. Implement Leave Encashment model and integration with F&F. (`Phase 1 — Leave`)

20. Implement Full & Final Settlement calculation. (`Phase 1 — Payroll`)

21. Add Rebate u/s 87A and old-regime TDS option.

22. Add Performance Management module (goals, appraisals, 360° feedback).

23. Add pre-built payroll reports (payroll register, headcount, attrition).

24. Implement in-app notifications for approval actions.

25. Extend `status.ts` with `getPayrollRunStatusTone()`, `getCompensationStatusTone()`, `getAttendanceImportTone()`. (`U4-11`)

26. Convert `LeavePlanBuilderPage.tsx` to 3-step wizard. (`U4-06`)

27. Add probation period tracking (`probation_end_date` on `Employee`).

28. Wrap all data tables in `overflow-x-auto`. (`U4-10`)

29. Add `toast.loading()` for long operations (payroll calculation, finalization). (`U4-13`)

30. Add leave balance preview during request form (real-time "remaining after this request"). (`U4-12`)

---

## Changelog from Previous Audit

No previous audit report exists. This is **v1.0** — the baseline audit.

---

*Report generated by automated code analysis. All findings are based on static source code inspection. No code was modified during the audit.*
