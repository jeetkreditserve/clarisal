# HRMS Audit Report

**Version**: v3.0
**Audit Date**: 2026-04-06 16:47:45 IST
**Auditor**: Claude Code (claude-sonnet-4-6)
**Prior Version**: v2.0 (2026-04-03 — `docs/HRMS_AUDIT_REPORT_20260403_195607.md`)
**Stack**: Django 4.2 · DRF 3.15 · PostgreSQL 15 · Celery 5.4 / Redis 7 · React 19 · TypeScript 5.9 · Vite 8 · Tailwind CSS 4 · Radix UI · Playwright 1.58 · Vitest 4 · Docker Compose · AWS S3

---

## Executive Summary

Clarisal v3 shows significant maturation across all dimensions audited in v2. The three headline statutory violations from v2 have been resolved: the EPF wage ceiling is now enforced with `cap_wages=True`, the ESI half-year contribution period is tracked via `ESIEligibilityMode`, and Professional Tax now covers 7 states (MH, KA, TN, WB, AP, TG, MP). The Control Tower now has impersonation, per-org feature flags, and audit trail. Backend test coverage for the payroll module has grown substantially (167 test functions).

The five most important findings in this v3 audit are:

1. **87A rebate threshold is hardcoded to ₹7 lakh for all fiscal years** — `INDIA_REBATE_87A_THRESHOLD = Decimal('700000.00')` in `statutory.py` applies to both FY24-25 and FY25-26. Under the Finance Act 2025, the new regime 87A rebate for FY25-26 rises to ₹60,000 on income up to ₹12 lakh. The single constant is wrong for FY25-26 new regime calculations.
2. **TDS monthly allocation divides annual tax by exactly 12** (`income_tax = annual_tax_total / 12`) without accounting for mid-year joiners or partial-period months. An employee joining in October with a prorated salary in that month will pay 1/12 of their full-year TDS even though they have earned far less than a full year's income.
3. **FNF leave encashment is hardcoded to zero days** — `_calculate_fnf_totals` calls `calculate_leave_encashment_amount(leave_days=ZERO, ...)` (line 413 of `services.py`). The payable leave balance is never fetched from the timeoff module. Every FnF settlement will under-pay by the employee's encashable leave balance.
4. **Frontend test coverage is 0 for all ct/ pages and virtually 0 for browser-level interactions** — The Vitest suite covers render/smoke tests for most org/ and employee/ pages but zero tests exist for the ct/ pages (PayrollMastersPage, CtOrgPayrollPage, OrganisationsPage, etc.). No test validates the critical payroll calculation trigger-to-result flow end-to-end.
5. **The new-regime 37% surcharge tier is still seeded in `OLD_REGIME_SURCHARGE_TIERS` at the ₹5 crore level but the new regime cap was reduced to 25% by Finance Act 2023** — `NEW_REGIME_SURCHARGE_TIERS` in `statutory.py` correctly caps at 25%, but the surcharge tiers are not differentiated per fiscal year. Any org processing senior executives earning above ₹5 crore may silently miscalculate surcharge.

Three entire modules remain incomplete or absent: Performance Management (models exist, UI scaffolded, but no evaluation cycles logic), Recruitment (ATS pipeline models exist, UI exists, but no onboarding-handoff integration), and a guided CT onboarding wizard (Task 3 from P17 is explicitly checked-off as incomplete).

---

## Audit Scorecard

| Area | v1 Score | v2 Score | v3 Score | Delta v2→v3 | Notes |
|------|----------|----------|----------|------------|-------|
| Core HR | 4/10 | 5/10 | 6/10 | +1 | Employee lifecycle complete; custom fields still missing |
| Attendance & Time | 3/10 | 5/10 | 5/10 | 0 | Biometric hooks added; geo-fencing absent |
| Payroll Engine | 4/10 | 7/10 | 8/10 | +1 | Ceiling, ESI period, multi-state PT fixed; TDS/FnF edge cases remain |
| Statutory Compliance | 3/10 | 6/10 | 7/10 | +1 | 7-state PT + LWF + ECR + Form16 + Form24Q live; 87A FY26 wrong |
| ESS / MSS | 4/10 | 6/10 | 6/10 | 0 | Investment declarations; no Form 12BB UX; no payslip PDF brand |
| Performance Mgmt | 0/10 | 1/10 | 2/10 | +1 | Goal cycles UI live; review/360 UI scaffolded but not wired |
| Recruitment / ATS | 0/10 | 1/10 | 2/10 | +1 | Job postings + applications + interviews; no onboarding handoff |
| Control Tower | 2/10 | 5/10 | 8/10 | +3 | Impersonation, feature flags, audit trail, billing lifecycle all shipped |
| Architecture | 6/10 | 7/10 | 7/10 | 0 | Row-level tenancy solid; no API versioning; no caching layer |
| Security | 4/10 | 7/10 | 8/10 | +1 | Secrets clean; PII encrypted; HTTPS enforced in prod; RBAC correct |
| Test Coverage | 2/10 | 3/10 | 5/10 | +2 | 167 backend payroll tests; 0 frontend unit tests for CT pages |
| UX vs Zoho/Keka | 3/10 | 4/10 | 4/10 | 0 | Functional but dense single-page forms; no wizard-style flows |

---

## 1. Codebase Overview

### Tech Stack
- **Backend**: Django 4.2, Django REST Framework 3.15, PostgreSQL 15, Celery 5.4, Redis 7, `django-environ`, `cryptography` (Fernet), `django-storages` (S3), `django-celery-beat`
- **Frontend**: React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4, Radix UI, React Router 6, TanStack Query, Vitest 4, Playwright
- **Infrastructure**: Docker Compose (dev), nginx reverse proxy, AWS S3 (production media), ZeptoMail transactional email
- **Auth**: JWT (SimpleJWT) + Django session, dual-mode (Control Tower / Workforce), impersonation via server-side sessions

### Module Inventory

| Backend App | Description | Status |
|---|---|---|
| `accounts` | User model, JWT auth, workspaces, CT impersonation | Complete |
| `organisations` | Multi-tenant core, feature flags, billing lifecycle, act-as sessions | Complete |
| `employees` | Employee master, lifecycle, bank accounts, government IDs (PAN/Aadhaar encrypted) | Solid |
| `departments` | Department / designation management | Complete |
| `locations` | Office locations with org address + state code | Complete |
| `timeoff` | Leave types, plans, accrual, carry-forward, LWP, approvals | Complete |
| `attendance` | Shift assignments, punch-in/out, biometric ingest, LOP calculation | Solid |
| `payroll` | Salary structure, EPF/ESI/PT/LWF/TDS, run workflow, payslips, FnF, filings | Mostly complete |
| `approvals` | Multi-stage approval workflows with delegation, escalation, SLA | Complete |
| `audit` | Structured audit log with PII redaction | Complete |
| `documents` | Document upload to S3, expiry tracking | Solid |
| `biometrics` | ESSL/ZKTeco integration, push/pull modes, encrypted API keys | Solid |
| `notifications` | In-app + email notifications, Celery tasks | Complete |
| `communications` | Notices/announcements with scheduled publish, auto-expiry | Complete |
| `reports` | Report generation stubs | Partial |
| `performance` | Goal cycles, reviews, 360 feedback models + UI scaffolding | Partial |
| `recruitment` | Job postings, applications, interviews, offers | Partial |

### Frontend Pages

| Area | Pages | Test Coverage |
|---|---|---|
| CT | DashboardPage, OrganisationsPage, OrganisationDetailPage, NewOrganisationPage, FirstLicenceBatchPage, PayrollMastersPage, CtOrgPayrollPage | DashboardPage only |
| Org Admin | DashboardPage, EmployeesPage, EmployeeDetailPage, DepartmentsPage, LocationsPage, LeaveCyclesPage, LeavePlanBuilderPage, HolidaysPage, PayrollPage, BiometricDevicesPage, ApprovalWorkflowsPage, AuditPage, ReportsPage, ProfilePage, NoticesPage, NoticeEditorPage, GoalCyclesPage, JobPostingsPage, CandidateDetailPage, AttendanceImportsPage, OnDutyPoliciesPage, SetupPage | Most pages have smoke tests |
| Employee | DashboardPage, LeavePage, AttendancePage, ApprovalsPage, PayslipsPage, DocumentsPage, OnboardingPage, PerformancePage, ProfilePage, EducationPage, OnDutyPage | Most pages have smoke tests |

### Approximate LOC
- Backend Python: ~52,500 lines (apps only, excluding migrations)
- Frontend TS/TSX: ~34,100 lines
- Total: ~86,600 lines

---

## 2. Feature Completeness Matrix

| Feature | Status | Severity of Gap | Notes |
|---|---|---|---|
| Employee master — core fields | Complete | — | Name, DOB, joining date, designation, department, location, employment type |
| Employee master — custom fields | Missing | High | No org-configurable custom fields. Zoho/Darwinbox allow 50+ |
| Org chart / reporting hierarchy | Partial | Medium | `reporting_to` FK exists; no graphical org chart in UI |
| Department / designation management | Complete | — | CRUD with employee count |
| Cost centre | Missing | Medium | No cost centre entity; payroll allocations cannot be split |
| Onboarding workflow | Complete | — | Multi-step wizard: basic details → documents → bank → govt IDs |
| Employee confirmation | Partial | Medium | Probation end date field exists; no automated confirmation workflow |
| Transfers / promotions | Missing | High | No transfer or promotion event model; only ad-hoc field edits |
| Employee exit / offboarding | Complete | — | Exit tasks, FnF, offboarding process |
| Document management | Solid | Low | Upload, S3 storage, expiry tracking; no e-sign |
| Shift management | Partial | Medium | Shift assignments exist; no rotational/flexible shift builder |
| Attendance capture — biometric | Solid | Low | ZKTeco/ESSL push + pull; geo-fencing absent |
| Attendance capture — mobile | Missing | Medium | No mobile punch-in, no location tracking |
| Leave policy engine | Complete | — | Accrual, carry-forward cap, max-balance, LWP, comp-off |
| Leave types — PL/CL/SL/ML | Complete | — | Configurable leave types; maternity/paternity can be created |
| Holiday calendar — state-wise | Partial | Medium | Holiday lists exist; no auto-population by state |
| Overtime rules | Missing | Medium | OT minutes tracked in attendance; no OT pay calculation |
| Attendance regularisation | Complete | — | On-duty policy, WFH via attendance regularisation workflow |
| Salary structure builder | Complete | — | Multi-component templates with EARNING/DEDUCTION/EMPLOYER types |
| CTC-to-in-hand computation | Complete | — | Gross, PF, ESI, PT, LWF, TDS, net all auto-computed |
| EPF with wage ceiling | Complete | — | ₹15,000 cap enforced via `cap_wages=True` (fixed from v2) |
| ESI with contribution period | Complete | — | Half-year period tracking via `ESIEligibilityMode` (fixed from v2) |
| Professional Tax — multi-state | Complete | — | 7 states: MH, KA, TN, WB, AP, TG, MP with correct slabs (fixed from v2) |
| Labour Welfare Fund | Complete | — | MH (half-yearly) and KA (annual) seeded |
| Income Tax — new regime FY25-26 | Mostly correct | High | Slabs correct per Finance Act 2025; 87A threshold wrong (see §7) |
| Income Tax — old regime | Complete | — | Correct slabs for all three age categories |
| Surcharge | Mostly correct | Medium | Marginal relief implemented; FY-specific tiers not separated |
| Standard Deduction ₹75,000 | Complete | — | Applied to both regimes |
| 87A Rebate | Partial | High | ₹25,000 rebate correct; threshold wrong for FY25-26 new regime |
| Section 80C/80D deductions | Complete | — | Capped deductions in old regime |
| Payroll run workflow | Complete | — | Draft → Calculated → Approval Pending → Approved → Finalized |
| Async payroll calculation | Complete | — | Celery task with polling |
| Payslip generation | Complete | — | Text-based; no PDF with org branding |
| FnF settlement | Partial | Critical | Gratuity and prorated salary correct; leave encashment hardcoded to 0 |
| Statutory filings — ECR | Complete | — | CSV with UAN, EPS/EPF split, EDLI, admin charges |
| Statutory filings — ESI | Complete | — | Monthly challan CSV |
| Statutory filings — Form 24Q | Complete | — | Quarterly TDS, challan linkage |
| Statutory filings — PT | Complete | — | State-wise PT export |
| Form 16 | Complete | — | XML + PDF skeleton per payslip |
| Approval workflows | Complete | — | Multi-stage, delegation, SLA, escalation |
| Notification engine | Complete | — | In-app + email (ZeptoMail or SMTP) |
| ESS — investment declarations | Complete | — | Employee can declare 80C/80D/HRA/LTA |
| ESS — Form 12BB | Missing | Medium | No Form 12BB generation from declarations |
| Performance — goal cycles | Partial | Medium | Model + UI exist; no KRA weighting, no calibration |
| Performance — 360 reviews | Partial | Medium | Model + basic UI; not wired to cycle workflow |
| Recruitment — ATS | Partial | Medium | Job postings, pipeline stages, offer; no onboarding handoff |
| CT impersonation | Complete | — | Act-as session with audit, read-only enforcement |
| CT feature flags per org | Complete | — | Per-module enable/disable |
| CT guided onboarding | Partial | Medium | P17 Task 3 explicitly incomplete |
| CT audit trail | Complete | — | Full AuditLog with PII redaction |
| CT usage analytics | Partial | Low | Placeholder; no aggregation queries |
| Billing / subscription | Partial | Medium | Licence ledger, batch lifecycle; no payment gateway |

---

## 3. Screen-by-Screen UX Review

### 3.1 CT Dashboard (`/ct/dashboard`)
**Purpose**: Control Tower landing page with org KPIs.
**What works**: Organisation list, status badges, billing status visible at a glance.
**UX gaps vs Zoho/Darwinbox**: No usage heat map, no per-org activity timeline, no quick-action shortcuts (e.g., "suspend org", "bulk licence top-up"). Darwinbox's implementation console shows per-tenant health metrics inline.
**Accessibility**: No ARIA landmark roles verified in snapshot; status badges rely solely on colour.
**Mobile**: Unknown — CT is likely desktop-only use, acceptable.
**Loading/empty states**: Skeleton loaders present (verified in DashboardPage.test.tsx mock pattern).

### 3.2 CT Organisations Page (`/ct/organisations`)
**Purpose**: List all tenants, navigate to org detail.
**What works**: Pagination, status badges, navigate to detail.
**UX gaps**: No bulk actions, no search/filter by state or billing status. Zoho People's Network Organisations panel has one-click suspend, quick feature-toggle, and inline licence count.
**Edge cases**: No empty state documented for zero organisations — unlikely in prod but should be handled.

### 3.3 CT Organisation Detail (`/ct/organisations/:id`)
**Purpose**: View and configure a specific tenant.
**What works**: Feature flags panel, act-as session, lifecycle events, licence batches.
**UX gaps**: Feature flag UI is a flat list of toggles; no description of what each flag does. No "reason required" prompt before disabling a module that has active data. Darwinbox's implementation console warns admins when disabling a module with outstanding records.
**Accessibility**: Toggle switches need associated labels for screen readers.

### 3.4 CT Payroll Masters (`/ct/payroll-masters`)
**Purpose**: Manage system-level income tax slab sets, view PT and LWF master data.
**What works**: Full CRUD for tax slab sets with per-category (Individual/Senior/Super Senior) and per-regime tabs. PT and LWF view with slab detail modal.
**UX gaps**: The fiscal year field is a free-text input — entering `2025-26` instead of `2025-2026` will silently create a disconnected slab set that never matches the payroll engine's derived fiscal year string. No format hint or picker. Zoho Payroll enforces fiscal year as a dropdown.
**Edge cases**: No warning when deleting a slab set that is referenced by active payroll runs. The `delete_tax_slab_set` service deletes with CASCADE risks on `PayrollTaxSlabSet → PayrollTaxSlab`.

### 3.5 Org Admin Payroll Page (`/org/payroll`)
**Purpose**: Full payroll management: setup, compensation templates, assignments, runs, filings.
**What works**: Tab navigation (Setup / Compensation / Runs / Filings), create/submit template, create/submit assignment, create/calculate/submit/approve/finalize runs, generate/download statutory filings. TDS challan entry. Arrears entry.
**UX gaps (critical)**:
- The entire payroll module is a single 1090-line component. It has no dedicated pages for payslip review, run details, employee-by-employee exception drill-down, or payslip preview before finalization. Keka's payroll run screen shows a per-employee expandable row with computed gross/deductions/net for each employee. Clarisal shows only aggregate counts.
- Template creation hardcodes just two lines (BASIC + PF_EMPLOYEE). Real salary structures need HRA, Special Allowance, LTA, etc. The form would need line-adding capability. Zoho allows adding up to 30+ components inline.
- No "salary comparison" view between current and revised assignments.
- Payslip is text-only — no branded PDF. Keka, Zoho, and Darwinbox all generate pixel-perfect PDFs.
**Loading states**: `toast.loading` used for async operations — correct.
**Empty states**: Empty `pay_runs` array shows a message but no CTA.

### 3.6 Employee Payslips Page (`/employee/payslips`)
**Purpose**: Employee views their own payslips.
**What works**: List view with month/year, download link.
**UX gaps**: Payslip is a raw text render (`rendered_text` field). No structured HTML/PDF view, no component-by-component breakdown in a visually friendly format. Zoho and Keka produce payslips with company logo, highlighted net pay, and a tax summary widget.
**Accessibility**: Download link must have descriptive `aria-label`.

### 3.7 Employee Leave Page (`/employee/leave`)
**Purpose**: Employee applies for and tracks leave.
**What works**: Leave balance display (real-time from API), apply leave form, approval status, leave history, calendar view.
**UX gaps**: No half-day leave option visible in the UI; no "planned absence" calendar overlay. Zoho People allows overlapping with holidays to auto-calculate net working days deducted.
**Edge cases**: Leave application with start > end date — backend validates but frontend error message placement is unclear.

### 3.8 Org Admin Employee List (`/org/employees`)
**Purpose**: View and manage all employees.
**What works**: Paginated list, status filter, invite modal, bulk operations.
**UX gaps**: No column sort, no advanced filter (department + location + status combined). Darwinbox's People Directory has a faceted search with 15+ filters. Designation is shown but not filterable.
**Data density**: Adequate — avatar, name, employee code, department, designation, status, join date.

### 3.9 Org Admin Employee Detail (`/org/employees/:id`)
**Purpose**: Full employee profile management.
**What works**: Personal info, employment, bank accounts, government IDs, leave balances, compensation history, onboarding status, offboarding tasks.
**UX gaps**: No org chart preview showing the employee's reporting chain. No document expiry alert banner. BambooHR surfaces "documents expiring soon" prominently on the profile.
**Edge cases**: Editing bank account number — the masked field shows `XXXX1234`; editing replaces the whole number. If the admin accidentally saves with the masked value, the backend will store the masked string as the actual account number. Should be a separate "Update account number" confirmation modal.

### 3.10 Org Admin Attendance Imports Page (`/org/attendance-imports`)
**Purpose**: Bulk-import attendance records from biometric exports.
**What works**: File upload, validation feedback.
**UX gaps**: No progress indicator for large file processing. No preview of records before confirming import. Keka shows a "100 records found, 3 errors — click to review" pre-import summary.

### 3.11 Org Admin Leave Cycles / Plans
**Purpose**: Configure leave policies.
**What works**: Leave cycle creation, plan builder with accrual/carry-forward/max-balance/encashment fields.
**UX gaps**: The plan builder is a long-scroll form with no section grouping. Zoho People's leave policy UI uses a step-based wizard with clear section headers. No policy cloning for similar leave types.

---

## 4. Architecture Review

### 4.1 Backend

**Project structure**: Clean Django apps-based layout under `backend/apps/`. Each app has `models.py`, `services.py`, `views.py`, `serializers.py`, `tests/`. Business logic is correctly isolated in `services.py`. Views are thin. This follows the layered pattern used by Keka and Zoho's engineering teams.

**Multi-tenancy**: Row-level tenancy via `organisation` FK on every model. Queries are consistently scoped to the request org via `get_active_admin_organisation`. CT users bypass org scoping intentionally (verified in `BelongsToActiveOrg` permission). No evidence of cross-org data leakage in the patterns examined.

**Models and normalisation**:
- `CompensationAssignmentLine` denormalises `component_name` and `component_type` — this is correct and intentional for payslip historical accuracy (so renaming a component doesn't break old payslips).
- `PayrollRunItem.snapshot` stores a full JSON snapshot of per-employee calculations — correct approach for auditability.
- `StatutoryFilingBatch.artifact_binary` stores binary content in PostgreSQL. For large filings (e.g., full-year Form 24Q) this will bloat the DB. Should use S3 storage with a reference key.
- `Employee.designation` is a `CharField` (max 255) — no foreign key to a designations table. This means designation values diverge over time (e.g., "Sr. Engineer", "Senior Engineer", "Senior Software Engineer"). Darwinbox uses a locked designation master.

**Indexes**:
- `PayrollRunItem` has composite indexes on `(pay_run, employee)` and `(employee, pay_run)` — correct.
- `InvestmentDeclaration` has index on `(employee, fiscal_year)` — correct.
- `AuditLog` has index on `(organisation, created_at)` and `(actor, created_at)` — correct.
- Missing: `Employee(organisation, status, date_of_joining)` — payroll run scans all ACTIVE employees per org; a covering index would help for large orgs.
- Missing: `CompensationAssignment(employee, status, effective_from)` — the `get_effective_compensation_assignment` query filters on all three; current ordering-based resolution will scan all assignments per employee.

**API design**:
- All REST, no versioning. A `/api/v1/` prefix is absent — adding `/api/v2/` later will require URL changes across all frontend clients.
- Pagination is `PageNumberPagination` (PAGE_SIZE=20) — fine for most resources but `PayrollRun.items` is fetched inline in the payroll summary response, meaning a run with 500 employees returns 500 items in a single response.
- No cursor-based pagination or GraphQL for deeply nested payroll data.

**Background jobs**:
- Celery Beat schedules are defined in `settings/base.py` (publish-scheduled-notices, expire-stale-notices, approval-reminders, biometric-sync, probation-reviews) — correct.
- Payroll calculation is async via Celery with polling (`PayrollRunCalculationStatusSerializer`) — correct.
- No idempotency keys on Celery tasks. Duplicate delivery from broker could trigger double payroll calculation.
- `send_payroll_ready_email` is dispatched via `transaction.on_commit` with a lambda capturing `user_id` and `label` — correct pattern.

**Caching**: No explicit caching layer for payroll tax slab sets, PT rules, or LWF rules — these are queried on every payroll run item. For an org with 1000 employees, each payroll run queries the PT rule table 1000+ times. A request-scoped cache or `select_related` preload would reduce DB load significantly.

**File storage**:
- Development: local filesystem (`MEDIA_ROOT`).
- Production: `S3Boto3Storage` with `AWS_DEFAULT_ACL = 'private'` — correct.
- `StatutoryFilingBatch.artifact_binary` stores binary in PostgreSQL even in production — should be migrated to S3.

**Configuration management**:
- All secrets via `environ.Env` reading `.env` — correct.
- `SECRET_KEY` has an insecure placeholder default that production settings block at startup — correct.
- `FIELD_ENCRYPTION_KEY` validation enforced in production — correct.
- `DEFAULT_LICENCE_PRICE_PER_MONTH` is a settings value (₹50/month default) — good but should be a DB-configurable value to support plan tiers.

### 4.2 Frontend

**Component architecture**: Pages are largely monolithic (e.g., `PayrollPage.tsx` at 1090 lines, `PayrollMastersPage.tsx` at 793 lines). Core UI primitives (AppDialog, AppSelect, AppDatePicker, SectionCard, StatusBadge, etc.) are well-abstracted in `components/ui/`. The payroll page should be broken into sub-components: `CompensationTemplateSection`, `PayrollRunSection`, `FilingsSection`.

**Routing**: React Router 6 with role-based route separation (`/ct/`, `/org/`, `/employee/`). Clean and intuitive.

**Form handling**: Standard `useState` form management. No form library (React Hook Form, Zod). Validation is entirely backend-side — frontend only shows the error returned from the API. Complex forms (leave plan builder, payroll template) lack inline field-level validation, leading to round-trips for obvious errors (e.g., empty required field).

**State management**: TanStack Query for server state — correct. No Zustand/Redux needed at this scale.

**API error handling**: `getErrorMessage` utility normalises API errors to human-readable strings — good. `toast.error` used consistently. Loading states handled via `isLoading` from TanStack Query.

**Performance**:
- Payroll summary endpoint returns all payroll runs with all items inline — risk of large payload.
- No lazy loading of sections within PayrollPage (all four sections rendered simultaneously).
- No code splitting at the route level observed in a quick grep — Vite should be configured for route-level splitting.

### 4.3 Infrastructure

**Environment separation**: `settings/development.py`, `settings/base.py`, `settings/production.py` — clean separation.
**Secret management**: `.env` file, not committed. Production validates key strength at startup.
**Logging**: Production logs to console at WARNING level — no structured JSON logging (e.g., structlog) for log aggregation in CloudWatch/Datadog.
**Monitoring hooks**: No Sentry/Datadog integration observed. No health check endpoint beyond Django's default.
**Docker Compose**: Dev compose with postgres, redis, celery, celery-beat, nginx — complete.

---

## 5. Code Quality Findings

### 5.1 Dead / Stale Code
- `calculate_professional_tax_monthly` in `statutory.py` (lines 187–194) is a legacy function that accepts a `slabs_by_state` dict. The actual call path now uses the DB-driven `_resolve_professional_tax_amount` in services. This function is not called anywhere in production code. It should be removed to avoid confusion.
- `DEFAULT_TAX_SLABS` in `services.py` (lines 106–114) is a hardcoded FY2024-25 new regime fallback used only when no CT master exists via `_ensure_global_default_tax_master`. Since `seed_statutory_masters` must be run on any deployment, these constants are unreachable in a correctly seeded system. Document or remove.

### 5.2 Broad Exception Handling
| File | Line | Pattern | Risk |
|---|---|---|---|
| `payroll/services.py` | 161 | `except Exception: return str(val)` | `_fmt_inr` silently returns the raw value on any error — acceptable |
| `payroll/services.py` | 532 | `except Exception: return TaxCategory.INDIVIDUAL` | `tax_category_for_fiscal_year` falls back silently — acceptable for default |
| `payroll/services.py` | 1419 | `except Exception: # noqa: BLE001` | Attendance summary fetch failure is silently swallowed and attendance inputs are skipped — **medium risk**: payroll run continues without attendance data with no visible warning to the admin |
| `recruitment/views.py` | 187 | `except Exception as exc` | Generic catch in recruitment view — low risk given module is partial |
| `timeoff/views.py` | 89, 104 | `except Exception as exc: # noqa: BLE001` | Leave request creation fallback — should be narrowed |

### 5.3 Duplication
- `_fiscal_year_for_period` appears in `services.py` and a similar pattern is in `filings/__init__.py` as `fiscal_year_bounds`. Should be unified.
- `_normalize_decimal` in `services.py` and `normalize_decimal` in `statutory.py` are functionally identical (both call `.quantize(Decimal('0.01'))`).

### 5.4 Test Coverage

**Backend payroll module** (167 test functions across 12 test files):
- `test_statutory_calculations.py` — Comprehensive EPF, ESI, PT, LWF, gratuity, income tax, surcharge, 87A rebate unit tests.
- `test_service_run_calculation.py` — Payroll run calculation integration tests.
- `test_filings.py` — ECR, ESI, Form 24Q, Form 16, PT filing generation.
- `test_service_run_finalization.py`, `test_full_and_final.py`, `test_investment_declarations.py` — Good coverage.
- **Gap**: No test for the TDS monthly allocation under joining-month proration scenario (employee joins mid-year, verifying their monthly TDS is correct).
- **Gap**: No test for FnF leave encashment calculation (expected to fail — the hardcoded `ZERO` will produce wrong results).
- **Gap**: No test for the 87A rebate under FY25-26 new regime at ₹12 lakh income.

**Frontend** (22 test files, all smoke tests):
- All tests verify that the page renders without crashing and that key UI text appears.
- Zero tests for user interaction flows (fill form → submit → verify API called with correct args).
- Zero tests for CT pages except `ct/DashboardPage.test.tsx`.
- `PayrollPage.test.tsx` (236 lines) tests only that the page renders and sections switch on tab click — no payroll calculation flow tested.

### 5.5 Error Handling — FnF Leave Encashment Bug

```python
# backend/apps/payroll/services.py lines 410-414
leave_encashment = ZERO
if monthly_basic_salary > ZERO:
    leave_encashment = calculate_leave_encashment_amount(
        leave_days=ZERO,   # <-- BUG: hardcoded zero, should query leave balance
        monthly_basic_salary=monthly_basic_salary,
    )
```

**Fix required**: Query the employee's encashable leave balance from `timeoff.services.get_employee_leave_balances` and pass the balance for encashable leave types.

---

## 6. Security Findings

| Finding | Severity | File | Details |
|---|---|---|---|
| Insecure default SECRET_KEY | Low (blocked at startup) | `settings/base.py:17` | `'django-insecure-dev-key-change-in-production'` — production settings raise `ImproperlyConfigured` if this is present. Correctly handled. |
| PAN/Aadhaar encryption | Good | `employees/models.py:366` | `identifier_encrypted` uses Fernet; `masked_identifier` stored separately. Correct. |
| Bank account/IFSC encryption | Good | `employees/models.py:395-398` | `account_number_encrypted`, `ifsc_encrypted` with masked variants. Correct. |
| Audit log PII redaction | Good | `audit/services.py` | `SENSITIVE_AUDIT_KEYS` set redacts salary, account, PAN, Aadhaar fields from payloads. |
| RBAC — CT vs Org Admin | Correct | `accounts/permissions.py` | `IsControlTowerUser`, `IsOrgAdmin`, `BelongsToActiveOrg` with feature flag enforcement. |
| CT impersonation — read-only | Correct | `accounts/permissions.py:110` | `OrgAdminMutationAllowed` returns `False` while CT is impersonating. |
| Horizontal privilege escalation | Acceptable risk | Multiple views | Views consistently scope queries to `organisation = get_active_admin_organisation(request)`. No cross-org escalation pattern found. |
| Biometric device API key | Good | `biometrics/models.py` | Stored encrypted, preview is masked, `compare_digest` used for validation. |
| Rate limiting | Complete | `settings/base.py:134-151` | Scoped throttles on login (5/min), password reset (5/hour), document upload (30/hour), approval actions (60/hour). |
| CORS | Correct | `settings/base.py:171-192` | Explicit allowed origins; no wildcard. `CORS_ALLOW_CREDENTIALS = True`. |
| HTTPS enforcement | Complete | `settings/production.py:32-37` | `SECURE_SSL_REDIRECT`, HSTS 1 year, preload, `SECURE_REFERRER_POLICY`. |
| CSRF | Correct | `settings/base.py:181-191` | `SESSION_COOKIE_SAMESITE = 'Lax'`, `CSRF_COOKIE_SAMESITE = 'Lax'`. `CSRF_COOKIE_HTTPONLY = False` (required by frontend AJAX — acceptable). |
| StatutoryFilingBatch binary in DB | Medium | `payroll/models.py:699-701` | `artifact_binary = models.BinaryField` stores filing artifacts in PostgreSQL. Large Form 24Q XMLs will bloat the DB. Should move to S3 with `artifact_s3_key`. |
| Form 12BB — no storage | Low | N/A | Investment proof files (`proof_file_key` on `InvestmentDeclaration`) reference S3 keys. No ACL verification that employees can only access their own proofs. |
| Missing `Content-Security-Policy` header | Medium | nginx config | CSP header not set in nginx config. XSS risk without CSP. |

---

## 7. Indian Compliance Audit

### 7.1 EPF (Employees' Provident Fund)

**Statutory rule**: Employee: 12% of basic wages. Employer: 12% (8.33% to EPS capped at ₹1,250/month + 3.67% to EPF). Wage ceiling: ₹15,000/month for mandatory contributions.

**Status**: **Compliant** (fixed from v2).

- `calculate_epf_contributions` with `cap_wages=True` and `wage_ceiling=PF_WAGE_CEILING` (₹15,000) — correct (statutory.py:143-157).
- ECR export correctly splits employer contribution into `eps_employer_share = min(eps_wages * 0.0833, 1250)` and `epf_employer_share = pf_employer_total - eps_employer_share` (ecr.py:48-50).
- EDLI admin charges at 0.5% of EPF wages — present in ECR (ecr.py:51-52).
- EPF admin charges at 0.5% — present in ECR.
- VPF: `vpf_rate_percent` on `CompensationAssignment` allows rates above 12% — correct.
- PF opt-out: Only when `basic_pay > PF_WAGE_CEILING AND assignment.is_pf_opted_out` — partially correct. EPFO rules allow opt-out only for new joinees earning above ₹15,000 who have never been EPF members. The current check does not verify new joiner status or previous EPF membership. **Minor gap**.

### 7.2 ESI (Employees' State Insurance)

**Statutory rule**: Employee: 0.75% of gross wages. Employer: 3.25%. Wage ceiling: ₹21,000/month. Half-yearly contribution period (Apr-Sep, Oct-Mar) — once an employee qualifies in a period they pay for the full period even if their wage exceeds ₹21,000 mid-period.

**Status**: **Compliant** (fixed from v2).

- `_resolve_esi_eligibility` correctly implements the half-year contribution period via `prior_window_coverage_exists` check (services.py:876-905).
- `ESIEligibilityMode.CONTINUED` forces ESI collection even above ₹21,000 if the employee was eligible at period start.
- Rates in `statutory.py`: 0.75% employee, 3.25% employer — correct (FY2022-23+ rates).

**Minor gap**: No model or check to handle ESI branch code (required for challan filing). ESI challan export in `esi.py` should validate branch code.

### 7.3 Professional Tax

**Statutory rule**: State-specific. MH: ₹200/month (₹300 in Feb) for salary >₹10,000. KA: ₹200/month (₹300 in Feb) for salary ≥₹25,000. TN: half-yearly slabs. WB/AP/TG/MP: monthly/annual slabs.

**Status**: **Compliant** for 7 states (fixed from v2).

- Gender-specific slabs for Maharashtra (female threshold ₹25,000) — correct.
- TN half-yearly basis (income_basis=HALF_YEARLY, deduction_frequency=HALF_YEARLY) — correct.
- MP annual slabs with monthly deductions — correct.
- `_resolve_professional_tax_amount` correctly scales basis by 6 (half-yearly) or 12 (annual) before slab lookup.
- **Gap**: No PT rules for GJ, HR, HP, OR, PB, RJ, CG, JH, TL (several PT-applicable states missing).
- **Gap**: Maharashtra female threshold ₹25,000 is seeded but the `effective_from` for that slab set is `date(2023, 7, 1)`. The female threshold was ₹10,000 before the 2023 amendment. Historical payroll re-runs (pre-July 2023) will use the wrong slab set.

### 7.4 Labour Welfare Fund

**Status**: **Compliant** for MH and KA.

- MH: ₹12/₹36 (employee/employer) for wages ≥ ₹3,000, half-yearly (June, December) — correct.
- KA: ₹20/₹40, annual (December) — correct.
- **Gap**: LWF not seeded for other states that have LWF (AP, TG, MP, HR, OR, etc.).

### 7.5 Income Tax — New Regime FY 2025-2026

**Statutory rule (Finance Act 2025)**:
- Slabs: 0% up to ₹4L, 5% ₹4L-₹8L, 10% ₹8L-₹12L, 15% ₹12L-₹16L, 20% ₹16L-₹20L, 25% ₹20L-₹24L, 30% above ₹24L.
- 87A Rebate: Up to ₹60,000 for income up to ₹12 lakh.
- Standard deduction: ₹75,000.

**Current implementation**:
```python
# statutory.py line 14
INDIA_REBATE_87A_THRESHOLD = Decimal('700000.00')  # ₹7 lakh — correct for FY24-25
INDIA_REBATE_87A_MAX = Decimal('25000.00')           # ₹25,000 — correct for FY24-25 only
```

**Bug**: For FY25-26 new regime, the threshold should be ₹12,00,000 and the maximum rebate should be ₹60,000.

**Correct formula for FY25-26 new regime**:
- If taxable income ≤ ₹12,00,000 → 87A rebate = min(tax_before_rebate, ₹60,000)
- If taxable income > ₹12,00,000 → no rebate

**Impact**: Any employee with FY25-26 income between ₹8L and ₹12L who is on the new regime is receiving no rebate (because income > ₹7L fails the threshold check), but should receive up to ₹60,000 rebate. This means they are overpaying TDS. This is a **Critical** compliance bug for FY25-26.

**Slabs** (FY25-26 new regime): Seeded correctly in `_NEW_REGIME_2025_SLABS` in `statutory_seed.py` — the 7-slab structure matches Finance Act 2025.

**Fix required**:
```python
# statutory.py — replace single constants with per-fiscal-year lookup
# OR pass rebate parameters from services.py based on fiscal_year and regime
INDIA_REBATE_87A_THRESHOLD_FY25_26_NEW = Decimal('1200000.00')
INDIA_REBATE_87A_MAX_FY25_26_NEW = Decimal('60000.00')
```

The cleanest fix is to pass `rebate_threshold` and `rebate_max` into `calculate_income_tax_with_rebate` from `services.py` after resolving them based on `fiscal_year` and `tax_regime`.

### 7.6 Income Tax — Old Regime

**Status**: **Compliant**.

Slabs for Individual (₹2.5L), Senior Citizen (₹3L), Super Senior (₹5L) — correctly seeded for FY24-25 and FY25-26. Age-based category lookup via `tax_category_for_fiscal_year` using `employee.profile.date_of_birth` — correct. 80C (₹1.5L cap), 80D (₹50K cap), 80TTA (₹10K cap) deductions applied correctly.

### 7.7 Surcharge

**Status**: **Mostly correct with a FY concern**.

- Old regime surcharge tiers: 10% above ₹50L, 15% above ₹1Cr, 25% above ₹2Cr, 37% above ₹5Cr — correct per old regime rules.
- New regime surcharge tiers: 10% above ₹50L, 15% above ₹1Cr, 25% above ₹2Cr — correct (37% tier removed for new regime by Finance Act 2023).
- Marginal relief implemented in `calculate_income_tax_with_rebate` — correct.
- **Gap**: Surcharge tiers are not per-fiscal-year. If government changes surcharge tiers in a future Finance Act, a code change is required. Should be DB-configurable like tax slabs.

### 7.8 Gratuity

**Status**: **Compliant**.

Formula: `(last_basic / 26) * 15 * service_years` — correct (statutory.py:266).
Ceiling: ₹20,00,000 — correct (GRATUITY_STATUTORY_CEILING = 2_000_000).
5-year eligibility with rounding: `calculate_gratuity_service_years` rounds up if more than 6 months served in the final year — correct (statutory.py:250).
**Gap**: Gratuity for employees covered under Gratuity Act for non-seasonal establishments uses 26 working days divisor (correct). No check that the organisation is covered by the Payment of Gratuity Act (10+ employees).

### 7.9 TDS Monthly Allocation — Mid-Year Joiner Bug

**Current implementation** (services.py line 1497):
```python
income_tax = (annual_tax_total / Decimal('12.00')).quantize(Decimal('0.01'))
```

**Problem**: For an employee joining on October 15 (month 7 of the fiscal year), the engine prorates their gross salary for the joining month but then calculates annual tax on `taxable_monthly * 12` — using the full-year extrapolation. The TDS per month is then `annual_tax / 12`, not `annual_tax / remaining_months`. An employee earning ₹1,50,000/month gross joining in October:
- Prorated October salary: ≈₹72,580 (17 of 31 days)
- Annual projection: ₹72,580 * 12 = ₹8,70,960 (wrong — should use remaining 6 months: ₹9,00,000 from Nov-Mar + ₹72,580 = ₹9,72,580)
- TDS: `annual_tax / 12` — incorrect, should be `annual_tax / remaining_months_in_fy`

**Correct approach** (Zoho Payroll, Keka): Calculate remaining months in the fiscal year from the payroll period. Monthly TDS = (projected annual tax) / (remaining months including current). This requires the `period_month` to drive the divisor:

```python
# FY runs Apr-Mar; months remaining = (Mar_of_FY - period_month_of_FY) + 1
fy_end_month = 3  # March
if period_month <= 3:
    months_in_fy_from_now = fy_end_month - period_month + 1
else:
    months_in_fy_from_now = 12 - period_month + fy_end_month + 1  # = 15 - period_month
income_tax = (annual_tax_total / Decimal(str(months_in_fy_from_now))).quantize(Decimal('0.01'))
```

**Severity**: High — all new joiners and employees with salary revisions will have incorrect TDS each month (either over- or under-deducted depending on the timing).

### 7.10 Form 16 and Form 24Q

**Status**: **Structurally present, not TRACES-certified**.

- Form 24Q XML schema implemented in `filings/form24q.py` with quarterly data.
- Form 16 XML + PDF skeleton in `filings/form16.py`.
- **Gap**: Form 24Q XML structure has not been validated against NSDL's official FVU (File Validation Utility) schema. The field names and nesting match common templates but are not verified against the current FVU version.
- **Gap**: Form 16 is a simplified XML/PDF — not the official TDS certificate format from TRACES. Employees cannot use this for ITR filing without regeneration from TRACES.

---

## 8. Control Tower Benchmark

### 8.1 Benchmark Reference

| Capability | Workday | SAP SuccessFactors | Zoho People | Darwinbox | Clarisal v3 |
|---|---|---|---|---|---|
| Tenant provisioning | Automated | Semi-automated | Guided wizard | Implementation console | Partial wizard |
| Feature/module toggle per org | Yes | Yes | Yes | Yes | **Yes** (v3) |
| Org-level config override | Yes | Yes | Limited | Yes | Partial |
| Impersonation / act-as | Yes (full) | Yes | Limited | Yes | **Yes** (v3, read-only) |
| Audit trail for super-admin actions | Yes | Yes | Yes | Yes | **Yes** (v3) |
| Onboarding workflow for new orgs | Yes | Yes | Yes | Yes | Partial (steps 3-7 incomplete) |
| Usage analytics per org | Yes | Yes | Yes | Yes | Placeholder only |
| Billing / subscription | Yes | Yes | Yes | Yes | Licence ledger (no gateway) |
| SLA monitoring | Yes | Yes | No | Yes | No |
| Data export per tenant | Yes | Yes | No | Yes | No |
| SSO / SAML per tenant | Yes | Yes | Yes | Partial | No |

### 8.2 CT Gap List

| Gap | Priority | Notes |
|---|---|---|
| Usage analytics per org | High | Planned in P17 but not implemented. CT admins cannot see active users, payroll runs, or feature adoption per tenant. |
| Guided onboarding (steps 3-7) | High | P17 Task 3 incomplete. CT must manually walk customers through leave plans, payroll setup, holidays, and first employee invite. |
| Payment gateway integration | High | Licence ledger and batch lifecycle are complete. No Razorpay/Stripe webhook integration for automated payment confirmation. |
| SSO / SAML | Medium | Single email/password auth. Enterprise customers expect SAML/OIDC per tenant. |
| Data export per tenant | Medium | No self-service data export (employee data, payslips ZIP, leave history) for tenant offboarding. |
| CT write actions while impersonating | Medium | Currently fully blocked. Should allow a limited set of CT-only actions (e.g., unlock account, reset onboarding) while impersonating. |
| Org-level config overrides | Medium | Some settings (leave types, holiday calendars) are org-configurable but not overridable from CT. |
| SLA monitoring | Low | No per-org response time or Celery queue depth monitoring. |

---

## 9. Prioritised Gap List

| # | Area | Gap | Severity | Effort | Recommended Fix | Reference |
|---|---|---|---|---|---|---|
| 1 | Compliance — Tax | 87A rebate threshold/max wrong for FY25-26 new regime (₹7L/₹25K instead of ₹12L/₹60K) | Critical | S | Pass `rebate_threshold` and `rebate_max` per fiscal year and regime into `calculate_income_tax_with_rebate`; derive from a DB table or per-FY constants map | Zoho Payroll, Keka update rebate params via configuration table |
| 2 | Compliance — Payroll | FnF leave encashment hardcoded to `ZERO` (services.py:413) | Critical | M | Query `timeoff.services.get_employee_leave_balances` for encashable leave types and sum the available units | Darwinbox FnF auto-fetches leave balance and applies encashment rate |
| 3 | Compliance — Tax | TDS monthly allocation divides annual tax by 12 regardless of joining month or FY position | High | M | Compute `months_remaining_in_fy` from `period_month`; use as divisor for monthly TDS allocation | Keka's TDS calculation uses remaining months from the payroll period |
| 4 | Feature — Core HR | Custom fields on employee master absent | High | L | Add `EmployeeCustomFieldDefinition` (org-level field spec) and `EmployeeCustomFieldValue` (per-employee value) models | Zoho People allows 50 custom fields per org; Darwinbox allows 100 |
| 5 | Feature — Payroll UX | Payroll run screen shows no per-employee breakdown before finalization | High | L | Extract `PayrollRunDetailPage` with expandable employee rows showing gross/deductions/net, exception drill-down, and pre-finalization payslip preview | Keka shows per-employee run detail; Zoho shows exception list with edit |
| 6 | Feature — Payroll | Payslip is text-only (no branded PDF) | High | M | Implement WeasyPrint or ReportLab PDF generation with org logo, structured layout, QR code for verification | Zoho, Keka, Darwinbox all produce pixel-perfect PDFs |
| 7 | Compliance — PT | Professional Tax rules missing for GJ, HR, PB, OR, RJ, HP, CG, JH | High | M | Add PT seed data for remaining PT-applicable states | All major HRMS products cover 15+ PT states |
| 8 | Compliance — Tax | Surcharge tiers not per-fiscal-year (hardcoded in `statutory.py`) | High | M | Move surcharge tiers to DB table linked to `PayrollTaxSlabSet` or a `SurchargeRule` model keyed by FY and regime | SAP SuccessFactors parameterises all tax rules per FY |
| 9 | Feature — Employee lifecycle | No transfer / promotion event model | High | L | Add `EmployeeTransferEvent` and `EmployeePromotionEvent` models with effective dates, old/new values, and approval hooks | Darwinbox has a full lifecycle event timeline |
| 10 | Feature — Attendance | No overtime pay calculation | Medium | M | Add `OvertimePolicy` per shift type; compute OT pay in payroll run from `attendance_overtime_minutes` already captured in snapshot | Keka's attendance module auto-computes OT earnings |
| 11 | Architecture | `StatutoryFilingBatch.artifact_binary` stored in PostgreSQL | Medium | S | Add `artifact_s3_key` field; store binary content in S3; keep DB record as metadata only | Industry standard: all HRMS store filing artifacts in object storage |
| 12 | Feature — Core HR | No designation master (free-text `designation` field on Employee) | Medium | M | Add `Designation` model with org FK; foreign-key `Employee.designation_id` | Darwinbox, Keka both use locked designation masters |
| 13 | Feature — CT | Usage analytics per org absent | Medium | L | Implement monthly aggregation Celery task; store `OrgUsageSnapshot` (active employees, payroll runs, leave requests per month) | Darwinbox implementation console shows per-tenant KPIs |
| 14 | Feature — CT | CT guided onboarding wizard incomplete (P17 Task 3) | Medium | L | Implement step-driven onboarding checklist: departments → locations → leave plan → payroll setup → holidays → first invite | Zoho People's network org wizard walks admins through 8 steps |
| 15 | Feature — Payroll | Form 24Q not validated against NSDL FVU schema | Medium | M | Run generated XML through NSDL's FVU 7.x; adjust schema to pass validation | Keka, Zoho both certify their Form 24Q against FVU before release |
| 16 | Feature — ESS | No Form 12BB generation from investment declarations | Medium | S | Generate Form 12BB PDF from `InvestmentDeclaration` records grouped by section | Zoho People generates Form 12BB; Keka offers bulk download |
| 17 | Feature — Payroll | No cost centre model | Medium | L | Add `CostCentre` model; allow split-allocation on `CompensationTemplateLine` | SAP SuccessFactors has full cost centre split |
| 18 | Architecture | No API versioning (`/api/v1/`) | Medium | M | Add `/api/v1/` prefix to all URL confs; support forward/backward compatibility for mobile clients | All enterprise HRMS APIs are versioned |
| 19 | Performance | PT/LWF rules queried per-employee per payroll run (no cache) | Medium | S | Cache PT/LWF rule lookups in `calculate_pay_run` using a request-scoped dict keyed by `state_code` | Pre-cache all active rules before the employee loop |
| 20 | Security | No Content-Security-Policy header in nginx | Medium | S | Add `add_header Content-Security-Policy "default-src 'self'; ..."` in nginx config | OWASP recommends CSP for all web apps |
| 21 | Feature — Payroll | PF opt-out does not verify new joiner status | Low | S | Add validation that `is_pf_opted_out` is only allowed when `date_of_joining` is after EPF membership establishment | EPFO circular clarifies opt-out eligibility |
| 22 | Feature — ESI | No ESI branch code validation for challan | Low | S | Add `esi_branch_code` field to Organisation; validate in ESI filing export | Required for ESIC portal challan matching |
| 23 | Feature — LWF | LWF not seeded for AP, TG, MP, HR, OR | Low | M | Add LWF seed data for remaining states that have LWF | Cross-reference Simpliance/Greytip LWF state list |
| 24 | Code quality | `calculate_professional_tax_monthly` in statutory.py is dead code | Low | S | Remove the function; it is never called in the production code path | — |
| 25 | Code quality | `_normalize_decimal` duplicated between services.py and statutory.py | Low | S | Import `normalize_decimal` from `statutory` in services; remove duplicate | — |
| 26 | Feature — Infra | No Sentry/structured logging | Low | S | Add Sentry DSN to production settings; switch to `structlog` for JSON logs | Industry standard for SaaS reliability |
| 27 | Feature — CT | No SSO/SAML per tenant | Low | XL | Add SAML 2.0 SP implementation (python3-saml); per-org SSO config | Enterprise customers require SAML |
| 28 | Feature — Attendance | No mobile punch-in or geo-fencing | Low | XL | Implement location-based punch-in with geo-fence radius per office location | Darwinbox has mobile app with GPS punch-in |

---

## 10. Recommended Roadmap

### Phase 1 — Statutory Compliance Fixes (Sprint 1-2, Critical/High)
These must be fixed before the next payroll run for any FY25-26 new regime employee or any departing employee.

1. **Fix 87A rebate for FY25-26** (Gap #1): 1-2 days. Add per-FY rebate parameter resolution in `services.py`. Backfill any already-processed FY25-26 payslips with corrected TDS.
2. **Fix FnF leave encashment** (Gap #2): 2-3 days. Query encashable leave balance from `timeoff.services`; add corresponding test.
3. **Fix TDS monthly allocation (remaining months)** (Gap #3): 2-3 days. Compute `months_remaining_in_fy` from `period_month`; add test for October joiner scenario.

### Phase 2 — Payroll UX and Core HR (Sprint 3-5, High)
4. **Payroll run detail page** (Gap #5): Per-employee expandable view with exception drill-down and pre-finalization payslip preview.
5. **Branded PDF payslips** (Gap #6): WeasyPrint integration. Should be unblocked before customer-facing rollout.
6. **Custom fields on employee master** (Gap #4): Foundation for all extensibility use cases.
7. **Designation master** (Gap #12): Replace free-text with foreign key.

### Phase 3 — Compliance Completeness (Sprint 6-7, High/Medium)
8. **PT seed data for missing states** (Gap #7): GJ, HR, PB, OR, RJ, HP, CG, JH.
9. **LWF seed data for remaining states** (Gap #23): AP, TG, MP, HR, OR.
10. **Surcharge tiers as DB-configurable per FY** (Gap #8): Move `NEW_REGIME_SURCHARGE_TIERS` and `OLD_REGIME_SURCHARGE_TIERS` to DB linked to `PayrollTaxSlabSet`.
11. **Form 24Q FVU validation** (Gap #15): Run against NSDL FVU 7.x; certify the export.
12. **Form 12BB generation** (Gap #16): PDF from `InvestmentDeclaration` records.

### Phase 4 — Architecture and CT Completeness (Sprint 8-10, Medium)
13. **Move filing artifacts to S3** (Gap #11): `artifact_s3_key` field; remove `artifact_binary`.
14. **API versioning** (Gap #18): `/api/v1/` prefix.
15. **CT usage analytics** (Gap #13): Monthly aggregation task + CT dashboard widget.
16. **CT guided onboarding wizard** (Gap #14): Complete P17 Task 3.
17. **Performance — query optimisation** (Gap #19): PT/LWF rule pre-cache in payroll run loop.
18. **CSP header** (Gap #20): nginx config.

### Phase 5 — Feature Expansion (Sprint 11+, Medium/Low)
19. **Employee transfer/promotion events** (Gap #9).
20. **Overtime pay calculation** (Gap #10).
21. **Cost centre model** (Gap #17).
22. **Payment gateway (Razorpay/Stripe) for licence billing** (Gap — billing).
23. **Performance management — full review cycle wiring**.
24. **Recruitment — onboarding handoff**.
25. **Mobile attendance / geo-fencing** (Gap #28).
26. **SSO/SAML** (Gap #27).

---

*End of HRMS Audit Report v3.0*
