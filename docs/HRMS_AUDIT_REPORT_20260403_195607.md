# HRMS Audit Report

**Version**: v2.0
**Audit Date**: 2026-04-03
**Auditor**: Claude Code (claude-sonnet-4-6)
**Prior Version**: v1.0 (2026-04-03 — `docs/HRMS_AUDIT_REPORT_20260403_000000.md`)
**Stack**: Django 4.2 · DRF 3.15 · PostgreSQL 15 · Celery 5.4 / Redis 7 · React 19 · TypeScript 5.9 · Vite 8 · Tailwind CSS 4 · Radix UI · Playwright 1.58 · Vitest 4 · Docker Compose · AWS S3

---

## Executive Summary

Clarisal has made significant progress since the v1.0 audit. **All seven v1 critical/high bugs have been fixed** — the 87A rebate is implemented, carry-forward and max-balance caps are enforced, payroll calculation is now async via Celery, and the security issues around secrets and validation have been resolved. The frontend has matured with proper dialogs, payslip downloads, real-time leave balance display, and grouped navigation.

The five most important findings in this audit are:

1. **EPF wage ceiling (₹15,000) is not enforced** — PF is deducted on the full basic salary regardless of amount, causing overcollection for higher-paid employees. This is a statutory violation.
2. **ESI half-year contribution period (Apr-Sep / Oct-Mar) is not tracked** — an employee whose salary crosses ₹21,000 mid-period should continue paying ESI for the rest of that period; the engine does not model this.
3. **Professional Tax is hardcoded to Maharashtra only** — organisations in Karnataka, Tamil Nadu, West Bengal, Andhra Pradesh, Telangana, and others receive zero PT deduction. Six PT-applicable states are silently non-compliant.
4. **Frontend test coverage is 7%** — with a payroll engine that handles real money and statutory deductions, this is unacceptably low. The three new payroll test files in v2 cover the happy path but zero boundary conditions.
5. **The communications (Notices) module has no Celery tasks for scheduled publish or auto-expiry** — a notice scheduled for future publication will never automatically go live without a manual publish click; expiry only runs on-demand during `get_visible_notices()`, meaning notices expire lazily rather than precisely.

Three entire feature modules remain absent: Performance Management, Recruitment/ATS, and a statutory filing export layer (Form 24Q, ECR, ESI challan).

---

## Audit Scorecard

| Area | v1 Score | v2 Score | Delta | Notes |
|------|----------|----------|-------|-------|
| Feature Completeness | 6/10 | 7/10 | +1 | On-duty, notices, F&F, old-regime stubs added |
| Architecture | 6/10 | 8/10 | +2 | Async payroll, Form 16 data, CT enhancements |
| Code Quality | 8/10 | 8/10 | = | Still clean; communications untested |
| UI/UX | 6/10 | 7/10 | +1 | Several fixes; aria-labels and bulk ops still open |
| Security | 4/10 | 7/10 | +3 | All critical secrets/validation issues resolved |
| Test Coverage | 3/10 | 4/10 | +1 | 7% frontend coverage; backend improved but compliance gaps remain |
| Indian Compliance | 5/10 | 6/10 | +1 | 87A fixed; EPF ceiling, ESI period, multi-state PT still missing |
| Control Tower | 6/10 | 8/10 | +2 | Full CT config, payroll/attendance/approval summaries, licence batches |

---

## 1. Codebase Overview

### Module Inventory

| Module / App | Backend App | Frontend Pages | Status |
|---|---|---|---|
| Authentication & Workspaces | `accounts/` | LoginPage, CTLoginPage | Complete |
| Employees | `employees/` | EmployeesPage, EmployeeDetailPage | Complete |
| Departments | (shared in `employees/`) | DepartmentsPage | Complete |
| Locations | (shared in `employees/`) | LocationsPage | Complete |
| Attendance | `attendance/` | AttendancePage (employee), OrgAttendancePage | Complete |
| Biometric Devices | `biometrics/` | BiometricDevicesPage | Complete |
| Attendance Imports | `attendance/` | AttendanceImportsPage | Complete |
| Leave Management | `timeoff/` | LeavePage (employee), LeavePlansPage, LeavePlanBuilderPage, LeaveCyclesPage | Complete |
| On-Duty Policies | `timeoff/` | OnDutyPage (employee), OnDutyPoliciesPage, OnDutyPolicyBuilderPage | Complete (new in v2) |
| Holiday Calendars | `timeoff/` | HolidaysPage | Complete |
| Approval Workflows | `approvals/` | ApprovalWorkflowsPage, ApprovalWorkflowBuilderPage | Complete |
| Payroll | `payroll/` | PayrollPage | Complete (async calc new in v2) |
| Payslips (employee) | `payroll/` | PayslipsPage | Complete |
| Documents | `documents/` | DocumentsPage (employee) | Complete |
| Notices / Announcements | `communications/` | NoticesPage, NoticeEditorPage | Backend partial (no Celery) |
| Audit Logs | `audit/` | AuditPage | Complete |
| Reports | `reports/` | ReportsPage | Partial (attendance only) |
| Control Tower | `organisations/` | All CT pages (11 routes) | Complete + expanded in v2 |
| Performance Management | — | — | **ABSENT** |
| Recruitment / ATS | — | — | **ABSENT** |
| Expense Management | — | — | **ABSENT** |
| Asset Lifecycle | — | — | **ABSENT** |
| IT Declarations | Stub in payroll | — | Model only (no UI) |

### Tech Stack (confirmed)
- **Backend**: Django 4.2.16, DRF 3.15, Celery 5.4, Redis 7, PostgreSQL 15
- **File Storage**: AWS S3 (private bucket, 15-min presigned URLs for downloads)
- **Auth**: Django SessionAuthentication + CSRF; `djangorestframework-simplejwt` installed but unused
- **Frontend**: React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4, Radix UI primitives, React Query (TanStack), Sonner toasts, Lucide icons
- **Testing**: Vitest 4 + Testing Library (frontend), Pytest (backend), Playwright 1.58 (E2E)
- **Containerisation**: Docker Compose (dev 8 services, prod 5 services behind nginx)

### Rough Scale
- Backend: ~190 API endpoints across 5 namespaces (`/api/auth/`, `/api/ct/`, `/api/org/`, `/api/me/`, `/api/biometric/`)
- Frontend: 52 authenticated routes + 6 public auth routes
- Backend tests: 229 test functions across 38 test files
- Frontend tests: 13 unit test files (7% statement coverage), 25 E2E spec files

---

## 2. Feature Completeness Matrix

### Core HR

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Employee statuses (INVITED → ACTIVE → RESIGNED/TERMINATED) | ✅ Complete | — | `employees/models.py:16–22` |
| Offboarding task checklist | ✅ Complete | — | 6 task types including `EXIT_INTERVIEW` |
| Document management + verification | ✅ Complete | — | 11 categories, PENDING/VERIFIED/REJECTED |
| Self-referential org chart | ✅ Complete | — | `reporting_to` FK, `direct_reports` reverse |
| Employee self-service portal | ✅ Complete | — | Full `/api/me/` namespace |
| Onboarding document checklist | ✅ Complete | — | Document-driven with status tracking |
| Probation tracking | ⚠️ Partial | Medium | `employees/models.py` — `probation_end_date` added in v2; probation review workflow absent |
| Custom employee fields | ❌ Missing | High | No `CustomField` framework; static model only |
| Exit interview structured form | ⚠️ Partial | Low | Task type exists; no structured form model |
| Org hierarchy / org chart UI | ⚠️ Partial | Medium | `reporting_to` FK present; no visual org chart component in frontend |

### Attendance & Time

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Shift management (fixed, grace, OT thresholds) | ✅ Complete | — | `attendance/models.py:111–133` |
| Geo-fencing | ✅ Complete | — | `restrict_by_geo` + `allowed_geo_sites` JSONField |
| IP-based restriction | ✅ Complete | — | `restrict_by_ip` + `allowed_ip_ranges` |
| GPS coordinates on punches | ✅ Complete | — | `latitude`, `longitude` on `AttendancePunch` |
| Biometric / device integration | ✅ Complete | — | `AttendanceSourceConfig` with DEVICE/API/EXCEL |
| Multi-location holiday calendars | ✅ Complete | — | Per-location assignment via junction table |
| Attendance regularisation | ✅ Complete | — | Full `AttendanceRegularizationRequest` with approval |
| On-duty requests | ✅ Complete | — | **New in v2** — full policy + request model |
| Overtime pay rate | ❌ Missing | Medium | Minutes tracked; no OT pay component/rate |
| Comp-off / TOIL (Time Off in Lieu) | ❌ Missing | Medium | Not implemented |
| Shift rotation patterns | ⚠️ Partial | Medium | Fixed/flexible shifts; no automated rotation engine |
| Biometric device real-time feed | ⚠️ Partial | Low | API ingestion exists; no real-time WebSocket feed |
| WFH (Work From Home) tracking | ❌ Missing | Medium | No WFH designation on attendance records |

### Leave Management

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Multiple leave types with accrual | ✅ Complete | — | `credit_frequency` (MONTHLY/QUARTERLY/HALF_YEARLY/YEARLY/MANUAL) |
| Carry-forward cap enforcement | ✅ Fixed (was v1 bug) | — | `timeoff/services.py:452–453` |
| Max balance enforcement | ✅ Fixed (was v1 bug) | — | `timeoff/services.py:328–336` |
| Proration on join date | ✅ Complete | — | `prorate_on_join` flag, first-month scaling |
| Half-day leaves | ✅ Complete | — | `allows_half_day` on `LeaveType` |
| Multi-level approval workflows | ✅ Complete | — | `ApprovalStage` with sequence, ALL/ANY mode |
| Leave balance ledger | ✅ Complete | — | Full `LeaveBalanceLedgerEntry` model |
| Leave overdraw prevention | ✅ Complete | — | Checked against pending + approved |
| Leave encashment | ❌ Missing | High | No `LeaveEncashmentRequest`; F&F has manual entry only |
| Comp-off leave type | ❌ Missing | Medium | No comp-off accrual from overtime |
| LWP (Leave Without Pay) auto-deduction | ⚠️ Partial | Medium | Attendance-based proration exists; dedicated LWP type absent |
| Annual leave lapse at year-end | ⚠️ Partial | Medium | `carry_forward_mode = NONE` handles lapse at cycle end; no prescheduled cycle-end job |

### Payroll (Indian Standards)

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Salary structure builder | ✅ Complete | — | `CompensationTemplate` + `CompensationTemplateLine` + `CompensationAssignment` |
| Async payroll calculation (Celery) | ✅ Fixed (was v1 bug) | — | `payroll/tasks.py:12`, 202 response, status-check endpoint |
| PF (12% employee + 12% employer) | ✅ Complete | — | `payroll/services.py:1039` |
| **EPF wage ceiling (₹15,000 basic)** | ❌ **MISSING** | **Critical** | PF deducted on full basic; no ceiling check |
| ESI (0.75% / 3.25%, ≤₹21,000) | ✅ Complete | — | Wage ceiling applied correctly |
| **ESI half-year contribution period** | ❌ **MISSING** | **High** | No period tracking; violates ESI Act rules |
| Professional Tax — Maharashtra | ✅ Complete | — | Hardcoded slabs: 0/150/200 |
| **Professional Tax — Other states** | ❌ **MISSING** | **Critical** | Returns ₹0 for all non-MH states |
| Labour Welfare Fund | ❌ Missing | High | Not implemented for any state |
| Income Tax Rebate u/s 87A | ✅ Fixed (was v1 bug) | — | `INDIA_REBATE_87A_MAX = 25000`, `payroll/services.py:344–356` |
| TDS — New regime (7 slabs) | ✅ Complete | — | Correct slab logic |
| TDS — Old regime | ⚠️ Partial | High | Field `tax_regime` on `CompensationAssignment` added; old regime deductions (80C, 80D, HRA) **not yet calculated** |
| Standard deduction (₹75,000) | ✅ Complete | — | Applied before slab calculation |
| 4% cess | ✅ Complete | — | Applied correctly |
| Investment declarations (80C/80D) | ⚠️ Partial | High | `InvestmentDeclaration` model added; not wired into TDS calculation |
| Payroll run workflow (DRAFT→FINALIZED) | ✅ Complete | — | Full status machine |
| Negative net pay guard | ✅ Fixed (was v1 bug) | — | `ensure_non_negative_net_pay()`, logs warning |
| Payslip generation | ✅ Complete | — | Formatted payslip with earnings/deductions/employer breakdown |
| Form 16 data generation | ✅ Complete | — | JSON data with Part A/Part B; no PDF/XML export |
| Full & Final settlement model | ✅ New in v2 | — | `FullAndFinalSettlement` model with prorated salary, encashment, gratuity fields |
| Gratuity calculation | ⚠️ Partial | High | F&F model field exists; **no automatic 15/26 formula**; manual entry only |
| Arrears / back-pay | ⚠️ Partial | Medium | `Arrears` model added; integration into payroll run not verified |
| ECR (PF) export | ❌ Missing | High | Not implemented |
| ESI challan generation | ❌ Missing | High | Not implemented |
| Form 24Q / TDS returns | ❌ Missing | High | Not implemented |
| Payroll register report | ❌ Missing | High | No dedicated payroll report endpoint |

### Self-Service (ESS / MSS)

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Employee self-service (profile, docs, requests) | ✅ Complete | — | 10 pages under `/me/` |
| Payslip download | ✅ Fixed (was v1 bug) | — | `useDownloadMyPayslip` wired in `PayslipsPage.tsx:15` |
| Approval workflows (configurable chains) | ✅ Complete | — | `ApprovalWorkflowBuilderPage` with stage/rule builder |
| Manager approval inbox | ✅ Complete | — | `ApprovalsPage.tsx` for employees; org admin dashboard for managers |
| Approval email notifications | ❌ Missing | High | No Celery tasks triggered on leave/regularisation approval events |
| In-app notifications | ❌ Missing | Medium | No `Notification` model; no bell icon connected to real data |
| SMS notifications | ❌ Missing | Low | Not implemented |
| Delegation of approval authority | ❌ Missing | Medium | No `ApprovalDelegation` model |
| SLA-based escalation | ⚠️ Partial | Medium | Fallback stage exists; no time-based escalation |
| IT declaration forms | ❌ Missing | High | `InvestmentDeclaration` model only; no employee UI |

### Notices Module

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Notice creation with audience targeting | ✅ Complete | — | ALL_EMPLOYEES, DEPARTMENTS, OFFICE_LOCATIONS, SPECIFIC_EMPLOYEES |
| Sticky notices | ✅ Complete | — | `is_sticky` flag |
| Scheduling (`scheduled_for`) | ⚠️ Partial | High | Field exists; **no Celery task to auto-publish at scheduled time** |
| Auto-expiry | ⚠️ Partial | Medium | Expires lazily in `get_visible_notices()`, not via a background task |
| Category tagging | ✅ Complete | — | 6 categories: GENERAL, HR_POLICY, OPERATIONS, CELEBRATION, COMPLIANCE, URGENT |
| CT compose & publish | ✅ Complete | — | Full CT-mode support |
| Employee-visible feed | ✅ Complete | — | `/api/me/communications/` with audience-based filtering |

### Control Tower

| Feature | Status | Severity of Gap | Notes |
|---------|--------|-----------------|-------|
| Multi-tenant data isolation | ✅ Complete | — | Org-scoped middleware; all queries filter by organisation |
| Organisation CRUD + lifecycle | ✅ Complete | — | Create, suspend, restore, activate |
| Module enable/disable per org | ❌ Missing | High | No feature-flag model per org; all modules always on |
| Licence batch / billing tracking | ✅ Complete | — | `OrganisationLicenceBatch` with DRAFT/PAID/EXPIRED lifecycle |
| CT admin org configuration | ✅ Complete | — | CT can manage leave cycles, plans, OD policies, workflows, holidays, notices inline |
| Payroll support visibility | ✅ Complete | — | Sanitised payroll summary; run state visible; employee pay hidden |
| Attendance support visibility | ✅ Complete | — | Today's summary, recent imports, diagnostics |
| Approval support visibility | ✅ Complete | — | Workflow counts, pending/approved/rejected run counts |
| Impersonation / act-as | ❌ Missing | High | CT cannot impersonate org admin; no `ActAsOrgAdmin` session model |
| Onboarding wizard for new orgs | ⚠️ Partial | Medium | `NewOrganisationPage` + `FirstLicenceBatchPage`; no guided seed-data wizard |
| Usage analytics per org | ⚠️ Partial | Medium | Summary counts available; no time-series usage graphs |
| Audit trail of super-admin actions | ✅ Complete | — | `audit/models.py` logs CT actions with actor, org, action, target |
| Feature flags / rollout control | ❌ Missing | High | No `FeatureFlag` model; per-org module toggle absent |

### Performance Management & Recruitment

| Feature | Status |
|---------|--------|
| Goal setting (OKR / KRA) | ❌ Missing |
| Appraisal cycles | ❌ Missing |
| 360° feedback | ❌ Missing |
| Job requisition / ATS | ❌ Missing |
| Offer letter generation | ❌ Missing |
| ATS → onboarding handoff | ❌ Missing |

---

## 3. Screen-by-Screen UX Review

### Employee Portal (`/me/`)

#### `/me/dashboard` — Employee Dashboard
- **Works well**: Announcements feed from Notice module; quick-action links; upcoming holiday cards.
- **Gap**: No attendance summary card showing today's punch status (Darwinbox shows punch-in/out time prominently on dashboard). No pending approval count badge.
- **Loading/empty**: Skeleton loaders present; no empty state for zero announcements.
- **Accessibility**: Missing `aria-label` on icon-only buttons (affects approx. 50+ buttons app-wide).

#### `/me/leave` — Leave Request & Balance
- **Works well**: Real-time "Remaining after this request" balance updated as user selects dates — this was a v1 gap and is now fixed. Color-coded warning when balance insufficient.
- **Gap**: No calendar view showing all approved/pending leaves visually (Zoho People renders a full calendar with color-coded entries by leave type). No ability to withdraw a request directly from the calendar.
- **Mobile**: Single-column layout works on mobile.

#### `/me/attendance` — Attendance & Regularisation
- **Works well**: Live punch status, regularisation request form.
- **Gap**: No visual monthly attendance calendar (Darwinbox shows a color-coded grid: P/A/HD/L/H per day). Users must scroll through a list view rather than seeing the month at a glance.
- **Empty state**: Present for no-punches-found scenario.

#### `/me/payslips` — Payslips
- **Works well**: Payslip breakdown (earnings, deductions, employer contributions) with Indian number formatting. Download button now wired — v1 gap fixed.
- **Gap**: No year filter or search; shows all payslips in a flat list. Large employers with 12+ months will need pagination or search.
- **Missing**: No email-to-self option; no bulk download for entire FY.

#### `/me/od` — On-Duty Requests (new in v2)
- **Works well**: Policy-aware form; correctly shows half-day and time-range modes based on active policy flags. File attachment supported.
- **Gap**: No history view of past OD requests with status. Current page shows only the request form.
- **Accessibility**: Form labels present and correctly linked.

#### `/me/profile`, `/me/education`, `/me/documents` — Profile Suite
- **Works well**: Structured form sections; bank account details; education history CRUD.
- **Gap**: No emergency contact quick-view on dashboard; profile completeness indicator absent (Zoho People shows "80% complete" nudge).

---

### Org Admin Portal (`/org/`)

#### `/org/dashboard` — Org Dashboard
- **Works well**: Key metric cards (headcount, pending approvals, attendance summary).
- **Gap vs Darwinbox**: No drill-down charts; no "attrition this month" card; no upcoming birthdays/anniversaries quick list (data exists in `get_employee_events()` but not surfaced here).

#### `/org/employees` and `/org/employees/:id` — Employee Management
- **Works well**: Search, status filter, department filter. Detail page has comprehensive fields.
- **Gap**: No org chart / hierarchy visualisation. `reporting_to` FK exists in the model but no visual tree component is rendered. Zoho People, Darwinbox, and Keka all have a native org chart view.
- **Bulk operations**: No bulk invite, no bulk status update, no bulk export to CSV — this was a v1 gap and remains unaddressed.

#### `/org/payroll` — Payroll (PayrollPage.tsx)
- **Works well**: Async calculation now shows HTTP 202 + polling status — v1 critical bug fixed. AppDatePicker used consistently. ConfirmDialog replaces `window.confirm()` — v1 bug fixed.
- **Gap**: No payroll register report (summary of all employee pay for the run). No "send payslips" bulk action. Payroll run status badges (`DRAFT`, `CALCULATED`, `FINALIZED`) use inline ternaries rather than the design system `StatusBadge` with a proper tone function (`getPayrollRunStatusTone()` from `status.ts` — v1 gap, still open).
- **Form labels**: Fixed — input fields now have `<label>` elements.

#### `/org/leave-plans` and `/org/leave-plans/:id` — Leave Plan Builder
- **Persistent gap**: `LeavePlanBuilderPage.tsx` is now **1,083 lines** (grew 58 lines since v1) and remains a single-file monolithic form. No step wizard, no "Save as Draft" between leave-type configuration and applicability rules. This is one of the most cognitively demanding screens in the app and lacks any progress scaffolding.
- **Works well**: Leave type CRUD inside the plan, accrual rule configuration, applicability rules by department/location/designation.

#### `/org/notices` and `/org/notices/:id` — Notices
- **Works well**: Audience targeting UI is intuitive; category, scheduling, expiry, sticky toggle all present.
- **Gap**: No preview of how the notice will appear to employees before publishing. Scheduled notices show a future date but the system will not auto-publish them (missing Celery task).

#### `/org/audit` — Audit Log
- **Works well**: Timeline view, filters (module, target type, actor, date range), CSV export, payload inspector dialog.
- **Accessibility**: Native `<input type="date">` used for from/to date filters instead of `AppDatePicker` (inconsistent with the rest of the app).

#### `/org/approval-workflows` and builder — Approval Workflows
- **Works well**: Stage-and-rule builder; ALL/ANY approval mode; fallback approver; CT mode correctly gated.
- **Gap**: No delegation model. If a manager is on leave, approvals queue with no automatic fallback trigger.

---

### Control Tower Portal (`/ct/`)

#### `/ct/organisations/:id` — Organisation Detail
- **Works well**: Comprehensive 12-tab interface with inline dialogs for all configuration. Diagnostic summaries for payroll, attendance, and approvals give CT operators actionable support context without exposing PII.
- **Gap**: "Payroll Support" tab removed and moved to dedicated `/ct/organisations/:id/payroll` page (correct architectural decision). However, the tab strip still has 12 items — consider grouping into sections (Core / Support / Configuration / Notes).
- **Impersonation absent**: CT operators cannot act as an org admin to reproduce issues. This is the most-requested capability in support-facing HRMS platforms.

#### `/ct/organisations/:id/payroll` — CT Org Payroll Page (new in v2)
- **Works well**: Sanitised payroll support view — run state, exception counts, compensation health diagnostics. No employee-level pay data visible, which is correct.
- **Gap**: No trend view (e.g., "exception count over last 6 runs"). Single-point-in-time snapshot only.

#### `/ct/payroll` — Payroll Masters
- **Works well**: Renamed "Payroll Masters" in sidebar (from "Payroll Preview") — correct.
- **Gap**: The global PayrollMastersPage manages India tax slab sets that are cloned into each org. There is no UI indication of which orgs are running which slab version, making it hard to audit slab adoption after a tax rule change.

---

## 4. Architecture Review

### Backend

#### Multi-Tenancy
**Well-implemented.** All views extract the active organisation via `get_active_admin_organisation(request, request.user)` helper and pass it through the service layer. CT views use explicit `organisation` FK lookups. No cross-tenant leakage identified.

#### Async Architecture
**Improved significantly.** Payroll calculation (the heaviest operation) is now a proper Celery task (`payroll/tasks.py:12`) returning HTTP 202 with a polling endpoint. Email delivery, biometric sync, and invitation tasks are all async. Outstanding gap: **no Celery task for notice auto-publish or auto-expiry** (`communications/tasks.py` does not exist).

#### API Design
**No versioning, still.** All routes use `/api/ct/`, `/api/org/`, `/api/me/` with no `/v1/` prefix — v1 finding A2-02 remains unaddressed. The namespace approach provides some stability but any breaking change will hit all clients simultaneously.

**Pagination**: Global `PageNumberPagination` is in `settings/base.py:144`. Not all list endpoints use it — several return unbounded querysets for configuration data (leave types, departments, etc.). Acceptable for small lists; risky for employee lists at large orgs (1,000+ employees).

#### Database
**PayrollRunItem indexes fixed.** The `(pay_run, status)` and `(pay_run, employee)` indexes recommended in v1 are now present (`payroll/models.py` migration `0008_payrollrunitem_indexes`).

**N+1 risk in payroll services** (v1 finding A2-04) is partially addressed — `PayrollRun` queries now `prefetch_related('items__employee__user')`. The inner-loop `get_effective_compensation_assignment()` calls still issue individual queries when the prefetch cache misses; acceptable for current scale but will degrade above 500 employees per run.

**Missing indexes elsewhere**: `OnDutyRequest` has indexes on `(employee, status)` and `(employee, start_date, end_date)` — good. `Notice` has indexes on `(organisation, status, published_at)` — good. No new index gaps identified.

#### Caching
Minimal. Session store only. No query-level caching. For a growing HRMS, leave balances and payslip data are candidates for short-TTL cache entries but this is not a blocker at current scale.

#### File Storage
AWS S3 private bucket with 15-minute presigned URLs (`documents/s3.py:23–28`). Correct. File upload limited to `{.pdf,.png,.jpg,.jpeg}`, max 5 MB (`documents/services.py:20–21`). No malware scanning hook.

### Frontend

#### Component Architecture
Well-factored. Shared UI primitives (`AppDialog`, `AppSelect`, `AppDatePicker`, `SectionCard`, `PageHeader`, `StatusBadge`, `EmptyState`) are used consistently. The `!isCtMode` hook pattern for shared pages is implemented correctly across all 9 shared pages (verified in this audit).

**Remaining issue**: `LeavePlanBuilderPage.tsx` at 1,083 lines is the one persistent outlier. It should be decomposed into sub-components: `LeavePlanBasicsForm`, `LeaveTypeCard`, `ApplicabilityRulesSection`.

#### State Management
React Query is used exclusively for server state — appropriate. No Zustand/Redux. Form state is local `useState`. This is correct but creates challenges for multi-step forms (the leave plan builder stores partial state in a single large `form` object with no intermediate persistence).

#### Hook Safety
All 97 hooks in `useOrgAdmin.ts` and 55 hooks in `useCtOrganisations.ts` accept an `enabled` parameter. No CT user will inadvertently fire org-admin endpoints. The CT redirect bug (CT users being logged out when visiting shared org-config pages) has been fully resolved.

#### Bundle Performance
Code-splitting via `React.lazy` / `Suspense` is not visible in the route definitions — all components are eagerly imported in `routes/index.tsx`. For 52+ routes this will produce a large initial bundle. Vite will tree-shake unused code but lazy-loading heavy pages (payroll builder, leave plan builder) would improve initial load time.

### Infrastructure

#### Docker
Dev and prod compose files are correctly separated. Prod uses Gunicorn with 4 workers. No secrets baked into the prod compose file.

#### Nginx
- **Missing**: HTTP→HTTPS redirect (relies on upstream load balancer in production — acceptable if documented, risky if not).
- **Missing**: `gzip on;` directive — static assets and JSON API responses are served uncompressed.
- **Present**: `SECURE_HSTS_SECONDS = 31536000` in Django production settings ensures HSTS header is sent via Django middleware.

#### Secret Management
- `SECRET_KEY` validated in `production.py:14–19` — `ImproperlyConfigured` raised if placeholder value — **v1 bug fixed**.
- `FIELD_ENCRYPTION_KEY` required in production — **v1 bug fixed**.
- Dev compose has hardcoded `POSTGRES_PASSWORD=clarisal_dev_password` — acceptable for dev only.

---

## 5. Code Quality Findings

### What Is Still Clean (v1 clean, confirmed v2)
- Zero `# TODO`, `# FIXME`, `# HACK` comments in `backend/apps/`
- Zero `console.log`, `debugger`, `@ts-ignore` in `frontend/src/`
- No skipped/empty test bodies
- Broad exception handlers are intentional and annotated with `# noqa: BLE001`

### C5-01 — Communications App Has Zero Tests
**Severity**: 🟠 High
**App**: `backend/apps/communications/`

`communications/` has models, services, views, and serializers — but no `tests/` directory. The `create_notice()`, `update_notice()`, `publish_notice()`, and `get_visible_notices()` service functions are entirely untested. The audience-filtering logic in `get_visible_notices()` involves non-trivial M2M joins and an inline expiry side-effect.

**Recommended tests:**
```python
# test_services.py
def test_notice_visible_to_all_employees()
def test_notice_visible_only_to_target_department()
def test_notice_expires_inline_when_past_expiry_date()
def test_draft_notice_not_visible_to_employees()
def test_sticky_notice_returns_before_non_sticky()
```

### C5-02 — Frontend Test Coverage at 7%
**Severity**: 🟠 High
**File**: `frontend/coverage/coverage-summary.json`

Statements: 6.85% (363/5,295), Branches: 7.79% (292/3,745), Functions: 5.83% (143/2,452), Lines: 7% (330/4,708).

All 13 frontend unit tests are smoke tests that verify a component renders without crashing. None test user interactions, form validation, or business logic flows. The 25 E2E specs offer higher coverage but have **6 `test.skip()` calls** (employee onboarding, parts of leave flow) that silently pass in CI.

### C5-03 — `simplejwt` Still Installed But Unused
**Severity**: 🟢 Low
**File**: `backend/requirements.txt`

`djangorestframework-simplejwt 5.3.1` remains in dependencies. DRF uses `SessionAuthentication` only. Dead dependency adds bundle weight and a minor CVE surface. Remove or configure for mobile/API-key auth.

### C5-04 — Aria Labels Still Sparse
**Severity**: 🟠 High
**App-wide**

Grep across `frontend/src/` finds 3 `aria-label` attributes total. The `ThemeToggle` component has one; 2 others exist on specific inputs. The app has an estimated 50–80 icon-only buttons (edit, delete, download, navigate, close) with no accessible name. Screen reader users cannot operate the application.

### C5-05 — Inconsistent Date Input Widgets
**Severity**: 🟡 Medium
**Files**: `frontend/src/pages/org/ReportsPage.tsx:229,233`, `frontend/src/pages/org/AuditPage.tsx:184,199`

`ReportsPage` and `AuditPage` use native `<input type="date">` for their date-range filters while every other page uses the `AppDatePicker` component. Visual and behavioural inconsistency.

---

## 6. Security Findings

### S6-01 — All v1 Critical/High Security Issues Resolved ✅

| v1 Finding | Resolution |
|---|---|
| AWS credentials in `.env` | Rotate instructions followed; `.env` excluded from commits |
| Insecure `SECRET_KEY` default | `ImproperlyConfigured` raised in `production.py:14–19` |
| `FIELD_ENCRYPTION_KEY` defaults to `''` | Required in production; Fernet encryption applied |
| Negative salary in serializers | `validate_monthly_amount >= 0` added (`payroll/serializers.py:96`) |
| Leave date range not validated | `end_date >= start_date` check added (`timeoff/serializers.py:275`) |

### S6-02 — No File Malware Scanning
**Severity**: 🟡 Medium
**File**: `backend/apps/documents/services.py:20–21`

File uploads are restricted by extension (`{.pdf,.png,.jpg,.jpeg}`) and size (5 MB), but there is no content-level validation (magic bytes check) and no malware scanning hook (e.g., ClamAV or AWS GuardDuty for S3). A renamed executable with a `.pdf` extension would pass the current checks.

**Recommendation:**
```python
import magic
def validate_file_content_type(file):
    detected = magic.from_buffer(file.read(2048), mime=True)
    if detected not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"File content type {detected} is not permitted.")
    file.seek(0)
```

### S6-03 — Decrypt Failure Silently Returns Empty String
**Severity**: 🟡 Medium
**File**: `backend/apps/common/security.py:56`

When Fernet decryption fails (wrong key, corrupted ciphertext), `decrypt_value()` silently returns `''` without logging. An operator would have no visibility into decryption failures, which could indicate key rotation issues or data corruption.

**Recommendation:**
```python
except InvalidToken:
    logger.error(f"Decryption failed for value starting with: {encrypted_value[:20]}")
    return ''
```

### S6-04 — Positive Security Findings Confirmed ✅

| Control | Evidence |
|---------|----------|
| All org API views have explicit `permission_classes` | Verified across `payroll/views.py`, `timeoff/views.py`, `attendance/views.py` |
| Employee payslips filtered to requesting employee (no IDOR) | `payroll/views.py:301–302` |
| S3 presigned URLs (15 min) for all document downloads | `documents/s3.py:23–28` |
| Private S3 bucket | `settings/base.py:226` (`AWS_DEFAULT_ACL = 'private'`) |
| Login rate-limited 5/min, password reset 5/hr | `settings/base.py:135–138` |
| PAN/Aadhaar encrypted at rest with Fernet | `common/security.py` |
| Biometric API key hashed + encrypted | `biometrics/models.py` |
| Multi-tenant isolation verified | All CT and org views use explicit org scoping |
| HSTS, XSS protection, X-Frame-Options in production | `settings/production.py:24–27` |
| CSRF required for all mutation methods | `SessionAuthentication` enforces CSRF by default |

---

## 7. Indian Compliance Audit

### EPF — Employee Provident Fund

| Rule | Status | Details |
|------|--------|---------|
| 12% employee contribution on basic | ✅ Correct | `payroll/services.py:1039` |
| 12% employer contribution (8.33% EPS + 3.67% EPF) | ✅ Correct | Employer split implemented |
| **Wage ceiling ₹15,000/month** | ❌ **MISSING** | PF is calculated on full basic regardless of amount. An employee earning ₹50,000 basic should have PF capped at 12% × ₹15,000 = ₹1,800, not 12% × ₹50,000 = ₹6,000. This is a statutory overcollection. |
| VPF (Voluntary PF beyond 12%) | ❌ Missing | Not implemented |
| PF opt-out for employees earning > ₹15,000 (new joiners) | ❌ Missing | No opt-out flag on `CompensationAssignment` |

**Fix for wage ceiling:**
```python
# payroll/services.py — EPF calculation
EPF_WAGE_CEILING = Decimal('15000.00')
pf_eligible_basic = min(basic_pay, EPF_WAGE_CEILING)
auto_pf = (pf_eligible_basic * PF_RATE).quantize(Decimal('0.01'))
```

### ESI — Employees' State Insurance

| Rule | Status | Details |
|------|--------|---------|
| 0.75% employee, 3.25% employer | ✅ Correct | `payroll/services.py:1072–1089` |
| Wage ceiling ₹21,000/month | ✅ Correct | Applied correctly |
| **Half-year contribution period (Apr-Sep, Oct-Mar)** | ❌ **MISSING** | Under ESI Act, an employee who crosses ₹21,000 gross mid-period must continue contributing ESI for the remainder of that half-year. The engine re-evaluates eligibility every month independently, which is incorrect. |

**Impact**: An employee earning ₹20,000 in April who gets a raise to ₹22,000 in June should continue paying ESI until September. The current code stops ESI deduction the moment gross exceeds ₹21,000.

### Professional Tax

| State | Status | Slabs |
|-------|--------|-------|
| Maharashtra | ✅ Correct | 0/150/200 hardcoded |
| Karnataka | ❌ Missing | Returns ₹0 |
| Tamil Nadu | ❌ Missing | Returns ₹0 |
| West Bengal | ❌ Missing | Returns ₹0 |
| Andhra Pradesh | ❌ Missing | Returns ₹0 |
| Telangana | ❌ Missing | Returns ₹0 |
| Madhya Pradesh | ❌ Missing | Returns ₹0 |

**Root cause**: `_professional_tax_monthly()` at `payroll/services.py:59–73` has `if state_code != 'MH': return ZERO`.

**Recommended fix**: Move PT slabs to a database model (`ProfessionalTaxSlab`) with `(state_code, min_salary, max_salary, monthly_amount)` rows, seeded at setup. This avoids code deployments when states update slabs.

### Labour Welfare Fund (LWF)

| Rule | Status |
|------|--------|
| LWF calculation (any state) | ❌ Not implemented |

Maharashtra LWF: ₹6 employee + ₹12 employer (bi-annual, June/December). Karnataka LWF: ₹20 employee + ₹40 employer (annual). Neither is implemented.

### Gratuity

| Rule | Status | Details |
|------|--------|---------|
| 15/26 formula | ❌ Not automated | `FullAndFinalSettlement.gratuity` is a manual entry field only |
| 5-year eligibility check | ❌ Not implemented | No check against tenure |
| ₹20 lakh ceiling | ❌ Not implemented | No ceiling applied even in manual entry |

**Correct formula** (to be auto-calculated at exit):
```python
def calculate_gratuity(last_basic: Decimal, years_of_service: int) -> Decimal:
    GRATUITY_CEILING = Decimal('2000000')  # ₹20 lakh
    if years_of_service < 5:
        return Decimal('0')
    gratuity = (last_basic / 26) * 15 * years_of_service
    return min(gratuity, GRATUITY_CEILING)
```

### Income Tax

| Rule | Status | Details |
|------|--------|---------|
| New regime — 7 slabs | ✅ Correct | `payroll/services.py` |
| Standard deduction ₹75,000 | ✅ Correct | Applied before slab |
| Rebate u/s 87A (≤₹7L, max ₹25,000) | ✅ Fixed in v2 | `payroll/services.py:344–356` |
| 4% cess | ✅ Correct | |
| Old regime (pre-FY2023 slabs) | ⚠️ Partial | Field and slab model exist; deductions (HRA, 80C, 80D) not computed |
| Investment declarations integration | ⚠️ Partial | `InvestmentDeclaration` model exists; not wired into TDS |
| Surcharge slabs (>₹50L, >₹1Cr) | ❌ Missing | No surcharge calculation for high earners |
| Form 16 PDF/XML export | ❌ Missing | JSON data generated; no exportable document |
| Form 24Q (quarterly TDS return) | ❌ Missing | |

### Statutory Filings

| Filing | Status |
|--------|--------|
| ECR (Electronic Challan-cum-Return for PF) | ❌ Missing |
| ESI monthly challan | ❌ Missing |
| PT state-wise returns | ❌ Missing |
| Form 24Q (TDS return) | ❌ Missing |
| Form 16 PDF/XML | ❌ Missing |

---

## 8. Control Tower Benchmark

### Industry Benchmark

| Vendor | CT Capability | Key Differentiator |
|--------|---------------|-------------------|
| **Workday** | Full tenant management console | Feature-flag rollout per tenant; per-tenant configuration override; usage analytics dashboard |
| **SAP SuccessFactors** | Provisioning Manager | Instance-level feature switches; sandbox → production promotion; upgrade orchestration |
| **Zoho People** | Network Organisation admin | Can shadow-login into any sub-org as its admin; per-org module enable/disable from network console |
| **Darwinbox** | Implementation Console | Guided org-setup wizard with checklist; module toggle per org; CT audit trail of all implementation actions |

### Clarisal CT vs Benchmark

| Capability | Clarisal | Gap vs Leaders |
|---|---|---|
| Multi-tenant isolation | ✅ Row-level, explicit scoping | None — correct approach |
| Org CRUD + lifecycle | ✅ Full (create, suspend, restore, activate) | None |
| CT configure org settings | ✅ Full (leave, OD, workflows, holidays, notices inline) | None |
| Billing / licence tracking | ✅ `OrganisationLicenceBatch` model | Missing invoice generation / payment gateway integration |
| Payroll support visibility | ✅ Sanitised (no employee pay visible) | No trend view over time |
| Attendance support visibility | ✅ Today's summary + diagnostics | No historical trend |
| Approval support visibility | ✅ Counts + recent runs | None |
| CT audit trail | ✅ Full — actor, org, action, target logged | None |
| **Impersonation / Act-as** | ❌ **Missing** | Critical gap vs Zoho/Darwinbox — CT operators cannot reproduce org-admin issues |
| **Module feature flags** | ❌ **Missing** | Cannot disable attendance or payroll module per org |
| **Guided onboarding wizard** | ⚠️ Partial | `NewOrganisationPage` exists but no guided seed-data checklist |
| Usage analytics | ⚠️ Point-in-time counts only | No time-series; no MAU / DAU; no feature adoption metrics |
| Impersonation audit trail | ❌ N/A (no impersonation) | Should log impersonation start/end when implemented |

### CT Gap Priority

| Gap | Priority | Recommended Fix |
|-----|----------|-----------------|
| No impersonation / act-as | Critical | `ActAsSession` model with CT-user + org-admin FK; session flag; logged start/end |
| No module feature flags | High | `OrganisationFeatureFlag(org, feature_code, enabled)` table; checked in permission layer |
| No guided new-org wizard | Medium | Checklist model with steps: add admins → configure leave → configure payroll → invite employees |
| No usage analytics | Medium | Daily aggregation Celery task → `OrgUsageStat(date, org, dau, feature_counts)` table |
| No invoice / billing integration | Medium | Webhook receiver for Stripe/Razorpay; mark batch paid automatically |

---

## 9. Prioritised Gap List

| # | Area | Gap | Severity | Effort | Recommended Fix | Reference |
|---|------|-----|----------|--------|-----------------|-----------|
| 1 | Compliance — EPF | Wage ceiling ₹15,000 not enforced; overcollection on high earners | 🔴 Critical | S | Cap `pf_eligible_basic = min(basic_pay, 15000)` in `payroll/services.py:1039` | EPF Act 1952, S. 6 |
| 2 | Compliance — PT | Professional Tax returns ₹0 for all non-Maharashtra states | 🔴 Critical | M | Move PT slabs to DB; seed KA, TN, WB, AP, TS, MP slabs | State PT Acts |
| 3 | Compliance — ESI | Half-year contribution period not tracked | 🟠 High | M | Track `esi_period_start` on payslip; continue ESI if mid-period even after crossing ₹21K | ESI Act 1948, Regulation 27 |
| 4 | Compliance — LWF | Labour Welfare Fund not implemented | 🟠 High | M | `LabourWelfareFundSlab` model; monthly/bi-annual/annual deduction by state | State LWF Acts |
| 5 | Compliance — Gratuity | Manual entry only; no 15/26 formula | 🟠 High | S | Auto-calculate at exit in `FullAndFinalSettlement` service | Payment of Gratuity Act 1972 |
| 6 | Compliance — Old regime | `tax_regime` field exists; 80C/80D/HRA deductions not computed | 🟠 High | L | Implement old-regime deduction calculation using `InvestmentDeclaration` model | Income Tax Act, S. 10 |
| 7 | Test Coverage | Communications app has zero tests | 🟠 High | S | Add `communications/tests/test_services.py` with 6 scenarios | — |
| 8 | Test Coverage | Frontend at 7% statement coverage | 🟠 High | L | Write interaction tests for leave form, payroll run, approval flow | — |
| 9 | Feature — CT | No impersonation / act-as org admin | 🟠 High | M | `ActAsSession` model; session middleware; audit log on start/end | Zoho People Network Admin |
| 10 | Feature — CT | No per-org module feature flags | 🟠 High | M | `OrganisationFeatureFlag` table; check in permission middleware | Darwinbox Implementation Console |
| 11 | Notices | No Celery task for scheduled publish | 🟠 High | S | `@shared_task` beat schedule every 5 min; query `status=SCHEDULED, scheduled_for <= now()` | — |
| 12 | Notices | Auto-expiry runs lazily on-demand only | 🟡 Medium | S | Separate beat task to mark `status=EXPIRED` for past `expires_at` | — |
| 13 | Feature | No leave encashment module | 🟡 Medium | M | `LeaveEncashmentRequest` model; integrate with F&F | Zoho Payroll |
| 14 | Feature | No comp-off / TOIL tracking | 🟡 Medium | M | `CompOffAccrual` model; link to overtime records | Darwinbox |
| 15 | Feature | No org chart visualisation | 🟡 Medium | M | React tree component using `reporting_to` FK data from existing API | Zoho People |
| 16 | Feature | No approval email notifications | 🟡 Medium | M | Celery task triggered on `ApprovalRun` status change | All competitors |
| 17 | Compliance | EPF opt-out for new joiners earning > ₹15K | 🟡 Medium | S | `is_pf_opted_out` flag on `CompensationAssignment` | EPF Act |
| 18 | Compliance | VPF (Voluntary PF) contribution | 🟡 Medium | S | `vpf_percentage` on `CompensationAssignment`; add to PF total | EPF Act |
| 19 | Compliance | Surcharge on income > ₹50L (new regime) | 🟡 Medium | S | Add surcharge tiers (10%/15%/25%) in `payroll/services.py` | Finance Act 2023 |
| 20 | Compliance | Investment declarations not wired to TDS | 🟡 Medium | M | Wire `InvestmentDeclaration` into old-regime TDS calculation | Income Tax Act S. 80C |
| 21 | UX | Zero aria-labels on icon buttons | 🟠 High | S | Add `aria-label` to all icon-only buttons app-wide (~50 instances) | WCAG 2.1 AA |
| 22 | UX | LeavePlanBuilderPage is 1,083-line monolith | 🟡 Medium | M | Split into `LeavePlanBasicsForm`, `LeaveTypeCard`, `ApplicabilityRulesSection` | — |
| 23 | UX | No bulk operations (invite, approve, export) | 🟡 Medium | L | Start with bulk payslip send and bulk leave approval | Keka, Darwinbox |
| 24 | UX | No visual attendance calendar (employee) | 🟡 Medium | M | Monthly grid with P/A/HD/L/H colour coding using existing attendance data | Darwinbox ESS |
| 25 | UX | AuditPage uses native date input | 🟢 Low | S | Replace with `AppDatePicker` (same fix for ReportsPage) | — |
| 26 | Infra | Nginx missing gzip compression | 🟢 Low | S | Add `gzip on; gzip_types text/plain application/json ...` to nginx.conf | — |
| 27 | Architecture | No API versioning (`/api/v1/`) | 🟢 Low | L | Add version prefix; set up version negotiation middleware | REST best practice |
| 28 | Architecture | `simplejwt` installed but unused | 🟢 Low | S | Remove from requirements.txt or configure for mobile clients | — |
| 29 | Compliance | Form 24Q / ECR / ESI challan export | 🟠 High | XL | Statutory filing export layer (structured text/CSV per format spec) | IT Act, EPF Act, ESI Act |
| 30 | Feature | Performance management module absent | 🟡 Medium | XL | Goal model + appraisal cycle + 360 feedback — full new module | Zoho People, Darwinbox |
| 31 | Feature | Recruitment / ATS absent | 🟡 Medium | XL | Job requisition → pipeline → offer → onboarding handoff | Zoho Recruit integration |
| 32 | Security | File upload lacks magic-byte content validation | 🟡 Medium | S | Add `python-magic` MIME type check in `documents/services.py` | OWASP |
| 33 | Security | Decrypt failure silently returns `''` | 🟢 Low | S | Add `logger.error()` in `common/security.py:56` on `InvalidToken` | — |

---

## 10. Recommended Roadmap

### Phase 1 — Statutory Compliance (Weeks 1-2) 🔴

These are revenue / legal risks. Ship before any new features.

1. **EPF wage ceiling** — 1 hour. One-line change + test with ₹50K basic employee.
2. **PT multi-state** — 2 days. Create `ProfessionalTaxSlab` model, seed MH/KA/TN/WB/AP/TS/MP slabs, update service to query DB.
3. **ESI half-year period** — 1 day. Add `esi_contribution_period_start` to `Payslip`; continue ESI deduction through period end even after crossing ₹21K.
4. **Gratuity auto-calculation** — 2 hours. Wire 15/26 formula into `FullAndFinalSettlement` service using exit date and last basic salary.
5. **Income Tax Rebate u/s 87A test** — Write `test_income_tax_rebate_87a_under_7_lakh()` to guard the now-fixed calculation from regression.

### Phase 2 — Critical UX & Test Coverage (Weeks 3-4) 🟠

6. **aria-label on all icon buttons** — 1 day. Global sweep; add labels with descriptive text.
7. **Communications test suite** — 1 day. 6 tests covering notice visibility, expiry, audience targeting.
8. **Notices Celery tasks** — 4 hours. Beat schedule: `auto_publish_scheduled_notices` every 5 min, `auto_expire_stale_notices` every hour.
9. **Payroll statutory unit tests** — 2 days. Test EPF ceiling, ESI period, all PT state boundaries, 87A boundary, joining-month proration with attendance inputs.
10. **LWF implementation** — 2 days. MH + KA as first states; DB-driven slab model.

### Phase 3 — Feature Completeness (Month 2) 🟠

11. **CT impersonation** — `ActAsSession` model, middleware, audit log.
12. **Per-org feature flags** — `OrganisationFeatureFlag` table, permission-layer enforcement.
13. **Old-regime TDS + investment declarations** — Wire `InvestmentDeclaration` into calculation.
14. **Leave encashment** — `LeaveEncashmentRequest` model + F&F integration.
15. **Approval email notifications** — Celery tasks on `ApprovalRun` status transitions.
16. **Bulk operations** — Start with bulk payslip send and bulk leave approval.

### Phase 4 — Compliance Filings & Advanced Features (Quarter 2) 🟡

17. ECR export for PF monthly filing.
18. ESI challan generation.
19. Form 24Q TDS return data export.
20. Org chart UI component.
21. Visual attendance calendar (employee ESS).
22. Surcharge slabs for high earners (>₹50L income).
23. Comp-off / TOIL tracking.

### Phase 5 — New Modules (H2) 🟡

24. Performance Management — goal setting, appraisal cycles, 360° feedback.
25. Recruitment / ATS — job postings, pipeline, offer letters.
26. Expense Management.
27. IT Declaration forms (employee UI for Section 80C/80D).

---

*End of HRMS Audit Report v2.0*
