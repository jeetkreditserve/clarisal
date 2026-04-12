# HRMS Audit Report

**Version**: v4.0
**Audit Date**: 2026-04-10 18:02 IST
**Auditor**: Claude Code (claude-sonnet-4-6)
**Prior Version**: v3.0 (2026-04-06 — `docs/HRMS_AUDIT_REPORT_20260406_164745.md`)
**Stack**: Django 4.2.16 · DRF 3.15.2 · PostgreSQL 15 · Celery 5.4 / Redis 7 · React 19 · TypeScript 5.9 · Vite 8 · Tailwind CSS 4 · Radix UI · WeasyPrint 62.3 · Sentry 2.20 · structlog 24.4 · Docker Compose · AWS S3

---

## Executive Summary

Clarisal v4 represents the most significant single-sprint maturation since the project began. All three critical/high statutory bugs from v3 have been fixed and verified in code:
- **87A rebate** is now per-fiscal-year/regime via `REBATE_87A_PARAMS` lookup dict
- **FnF leave encashment** now queries actual encashable leave balances (services.py:477–503)
- **TDS monthly allocation** now uses `_months_remaining_in_fiscal_year(period_month)` as the divisor

Beyond bug fixes, six new complete modules were delivered (P19 biometrics, P20 HR extensibility, P21 security hardening, P22 expenses, P23 assets, P24 payroll compliance, P25 payroll UX, P26 architecture hardening). The product is now functionally competitive with mid-market Indian HRMS products.

**The five most important findings in this v4 audit are:**

1. **Gratuity eligibility gate uses non-statutory rounding** — `_completed_service_years()` in `services.py:441–447` truncates to whole years, while `calculate_gratuity_service_years()` rounds up for >6 months of partial year (per the correct statutory interpretation). An employee with 4 years 7 months of service will be **incorrectly denied gratuity** at FnF settlement. This is a **High** severity compliance bug.

2. **Annual TDS income projection still uses ×12 for mid-year joiners** — `services.py:1710` computes `annual_taxable_gross = taxable_monthly × 12` regardless of joining month. The divisor fix (Bug 3 from v3) is correct, but the numerator is still wrong. An October joiner's annual tax should be projected on 6 months of income, not 12. This causes over-deduction in the first payroll month and self-corrects erratically. **Medium** severity.

3. **Leave lapse does not cascade to payroll LWP** — `process_cycle_end_lapse` (timeoff/services.py) creates a ledger EXPIRY entry but does not create a `LeaveWithoutPayEntry`. The `LEAVE_LAPSE` source value exists in the model enum but is never written. Leave lapse is operationally complete but does not feed into LWP payroll deduction as the model design intended. **Medium** severity.

4. **Two geo-fence systems coexist** — Web punch-in (`MyAttendancePunchInView`) enforces the legacy `AttendancePolicy.allowed_geo_sites` JSON field; mobile punch-in (`MyMobilePunchView`) enforces the new `GeoFencePolicy` table. An employee working in a geo-fenced office can be blocked on mobile but not on web browser. **Medium** severity.

5. **Pillow 10.4.0 has CVE-2024-28219** — A buffer overflow vulnerability in certain image processing modes. Upgrade to Pillow 11.x required. Django 4.2.16 is also behind 4.2.20 (4 patch releases); check for any security advisories in the delta. **Low–Medium** severity depending on image processing usage.

Three modules remain structurally incomplete: Performance Management (models exist, UI scaffolded, review cycles not wired), Recruitment (ATS pipeline present, no onboarding handoff), and the CT guided-onboarding wizard (a functional checklist exists but is not a proper step-driven wizard UX).

---

## Audit Scorecard

| Area | v1 Score | v2 Score | v3 Score | v4 Score | Delta v3→v4 | Notes |
|------|----------|----------|----------|----------|------------|-------|
| Core HR | 4/10 | 5/10 | 6/10 | 8/10 | +2 | Custom fields, designation master, transfer/promotion events, org chart, exit interviews |
| Attendance & Time | 3/10 | 5/10 | 5/10 | 7/10 | +2 | Comp-off, WFH, shift rotation, leave lapse, mobile GPS punch, geo-fencing |
| Payroll Engine | 4/10 | 7/10 | 8/10 | 8.5/10 | +0.5 | FnF and TDS fixed; cost centres; run detail page; gratuity gate bug + TDS projection remain |
| Statutory Compliance | 3/10 | 6/10 | 7/10 | 8/10 | +1 | 87A fixed; 15 PT states; 7 LWF states; SurchargeRule DB; Form 12BB; ESI branch code |
| ESS / MSS | 4/10 | 6/10 | 6/10 | 7/10 | +1 | IT declaration CRUD, Form 12BB download, payslip PDF; proof upload still plain text |
| Expense Management | 0/10 | 0/10 | 0/10 | 7/10 | +7 | P22 fully delivered — policy, claims, receipts, approval, reimbursement |
| Asset Lifecycle | 0/10 | 0/10 | 0/10 | 7/10 | +7 | P23 fully delivered — catalogue, issuance, acknowledgement, return, offboarding gate |
| Performance Mgmt | 0/10 | 1/10 | 2/10 | 2/10 | 0 | Models + UI scaffolded; review cycles not wired |
| Recruitment / ATS | 0/10 | 1/10 | 2/10 | 2/10 | 0 | ATS pipeline present; no onboarding handoff |
| Control Tower | 2/10 | 5/10 | 8/10 | 9/10 | +1 | Tenant data export, limited CT write during impersonation, P17 mostly complete |
| Architecture | 6/10 | 7/10 | 7/10 | 8/10 | +1 | API versioning (/api/v1/), indexes, S3 filing artifacts, idempotency, pagination |
| Security | 4/10 | 7/10 | 8/10 | 8.5/10 | +0.5 | CSP header, magic-byte upload, Sentry/structlog; Pillow CVE; 2 new low findings |
| Test Coverage | 2/10 | 3/10 | 5/10 | 7/10 | +2 | ~623 backend tests; CT frontend tests; P18/P19/P20/P22/P23 all have tests |
| UX vs Zoho/Keka | 3/10 | 4/10 | 4/10 | 6/10 | +2 | Payroll run detail page, branded PDF payslip, expense module, asset module |

---

## 1. Codebase Overview

### Tech Stack
- **Backend**: Django 4.2.16, DRF 3.15.2, PostgreSQL 15, Celery 5.4, Redis 7, WeasyPrint 62.3, `sentry-sdk[django,celery]` 2.20.0, `structlog` 24.4.0, `python-magic`, `qrcode` 8.0
- **Frontend**: React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4, Radix UI, React Router 6, TanStack Query, Vitest 4, Playwright
- **Auth**: JWT (SimpleJWT) + Django session, dual-mode (CT / Workforce), impersonation via ActAsSession, limited CT write during impersonation

### Module Inventory

| Backend App | Description | Status |
|---|---|---|
| `accounts` | User model, JWT auth, workspaces, CT impersonation | Complete |
| `organisations` | Multi-tenant core, feature flags, billing, act-as, usage analytics, tenant data export | Complete |
| `employees` | Employee master, custom fields, designation master, lifecycle, transfer/promotion events, exit interviews, bank accounts, PAN/Aadhaar encrypted | Solid |
| `departments` | Department / designation management | Complete |
| `locations` | Office locations with state code, geo-fence policies | Complete |
| `timeoff` | Leave types, plans, accrual, carry-forward, comp-off, LWP, leave lapse | Mostly complete |
| `attendance` | Shifts (fixed/overnight/rotation), WFH, OT, regularisation, mobile GPS punch, biometric ingest | Solid |
| `payroll` | Salary structure, EPF/ESI/PT(15 states)/LWF(7 states)/TDS, SurchargeRule, cost centres, run workflow, branded PDF payslips, FnF, Form 12BB, filings (ECR/ESI/PT/Form24Q/Form16) on S3 | Mostly complete |
| `approvals` | Multi-stage workflows with delegation, escalation, SLA | Complete |
| `audit` | Structured audit log with PII redaction | Complete |
| `documents` | Document upload to S3, magic-byte validation, expiry tracking absent | Partial |
| `biometrics` | 7-vendor registry, ADMS/eBioserver/REST/EXPORT_BRIDGE, real-time SSE | Complete |
| `notifications` | In-app + email (ZeptoMail/SMTP) | Complete |
| `communications` | Notices/announcements, scheduled publish, auto-expiry | Complete |
| `expenses` | P22 — policies, claims, lines, receipts, approvals, reimbursement | Complete |
| `assets` | P23 — catalogue, issuance, acknowledgement, maintenance, return, offboarding gate | Complete |
| `performance` | Goal cycles, reviews, 360 feedback models + UI scaffolding | Partial |
| `recruitment` | Job postings, applications, interviews, offers; no onboarding handoff | Partial |
| `reports` | Report generation stubs | Partial |

### Frontend Pages (new since v3)

| Area | New Pages | Status |
|---|---|---|
| Org Admin | `PayrollRunDetailPage`, `OrgChartPage`, `ExpensePoliciesPage`, `ExpenseClaimsPage`, `AssetsInventoryPage`, `AssetAssignmentsPage` | Delivered |
| Employee | `ExpensesPage`, `MyAssetsPage`, `TaxDeclarationsPage` | Delivered |
| CT | `CtOrgPayrollPage` test, `PayrollMastersPage` test, `OrganisationDetailPage` test | Tests added |

### Approximate LOC
- Backend Python: ~58,000 lines (apps only, excluding migrations) — up ~5,500 from v3
- Frontend TS/TSX: ~42,000 lines — up ~7,900 from v3
- Total: ~100,000 lines

### Test Coverage
- Backend: ~623 test functions across 80 test files
- Frontend: 41 test files (primarily smoke + interaction tests)

---

## 2. Feature Completeness Matrix

| Feature | v4 Status | Severity of Gap | Notes |
|---|---|---|---|
| Employee master — core fields | Complete | — | |
| Employee master — custom fields | **Complete** (new) | — | `CustomFieldDefinition` + `CustomFieldValue` with 7 types, placement scoping |
| Org chart / reporting hierarchy | **Complete** (new) | Low | `OrgChartPage` with recursive tree; CSS-only, not graphical — see §3 |
| Department / designation management | Complete | — | `Designation` model with master CRUD, FK on Employee |
| Cost centre | **Complete** (new) | — | `CostCentre` model with GL code, parent/child, CRUD endpoints |
| Transfer / promotion events | **Complete** (new) | — | `EmployeeTransferEvent` + `EmployeePromotionEvent` with approval hooks |
| Onboarding workflow | Complete | — | |
| Employee confirmation | Partial | Low | No CONFIRMED status; probation_end_date=null is ambiguous |
| Employee exit / offboarding | Complete | — | FnF, asset-return gate, exit interview (backend) |
| Exit interview UI | Missing | Medium | Backend models complete; no frontend surface in EmployeeDetailPage |
| Document management | Partial | Medium | S3, magic-byte validation, SHA-256; **no expiry_date field** |
| Shift management — fixed/overnight | Complete | — | |
| Shift management — rotation | **Complete** (new) | — | `ShiftRotationTemplate` with interval-based sequence |
| Shift management — flexible/flexi-time | Missing | Medium | No "total hours per week" or "core hours + flexible window" type |
| Attendance capture — biometric | Complete | — | 7 vendors, push/pull/export-bridge |
| Attendance capture — mobile GPS | **Complete** (new) | — | `GeoFencePolicy` WARN/BLOCK with haversine; web punch uses legacy system |
| Geo-fence — consistency | Partial | Medium | Two geo-fence systems; web punch uses legacy JSON, mobile uses GeoFencePolicy table |
| Leave policy engine | Complete | — | Accrual, carry-forward (NONE/CAPPED/UNLIMITED), LWP, comp-off |
| CAPPED carry-forward enforcement | Missing | Medium | `CarryForwardMode.CAPPED` not processed by leave lapse task |
| Leave lapse → payroll LWP cascade | Missing | Medium | Lapse creates ledger EXPIRY but not `LeaveWithoutPayEntry` |
| Leave types — PL/CL/SL/ML/comp-off | Complete | — | Configurable system; no statutory minimum enforcement |
| Overtime — configuration | **Complete** (new) | — | `overtime_multiplier`, approval workflow, payroll OT lines |
| Overtime — NFNL holiday rate | Missing | Low | Single multiplier; no per-holiday-type differential |
| Regularisation (missed punch/OD/WFH) | Complete | — | |
| EPF | Compliant | Low | EPS/EPF employer split absent (3.67/8.33 not separated); affects ECR |
| ESI | Compliant | — | |
| PT — multi-state | **Complete** (15 states) | — | MH KA TN WB AP TG MP GJ HR PB OD HP CT JH RJ |
| LWF — multi-state | **Complete** (7 states) | — | MH KA AP TG MP HR OD; WB missing |
| 87A Rebate FY25-26 | **Fixed** | — | Per-FY/regime `REBATE_87A_PARAMS` dict |
| TDS monthly allocation divisor | **Fixed** | — | `_months_remaining_in_fiscal_year(period_month)` |
| TDS annual income projection | Partial | Medium | `taxable_monthly × 12` ignores joining month; over-projects for mid-year joiners |
| FnF leave encashment | **Fixed** | — | Queries actual encashable balances |
| Gratuity eligibility gate | Bug | High | `_completed_service_years()` truncates, denies eligible 4y7m+ employees |
| Gratuity amount formula | Compliant | — | 15/26, ₹20L ceiling, correct |
| SurchargeRule — DB-configurable | **Complete** (new) | — | `SurchargeRule` model; CT view for read-only; seed for both FYs |
| Surcharge seed — OLD regime 37% | Missing in seed | Low | 37% tier absent from `seed_surcharge_rules()` for OLD regime |
| Payroll run workflow | Complete | — | DRAFT → CALCULATED → APPROVAL_PENDING → APPROVED → FINALIZED |
| Payroll run — per-employee detail | **Complete** (new) | — | `PayrollRunDetailPage` with expandable rows, exception filter, pagination |
| Payslip — branded PDF | **Complete** (new) | — | WeasyPrint with org logo, QR code, structured tables |
| Payslip — raw `rendered_text` removal | Partial | Low | `rendered_text` pre-block still in `PayslipsPage.tsx:236` |
| Form 12BB | **Complete** (new) | — | PDF from `InvestmentDeclaration` records; ESS download endpoint |
| Form 24Q | Structurally present | Medium | Schema aligned with Protean/RPU 4.7; physical FVU validation not yet run |
| Statutory filings — artifacts on S3 | **Complete** (new) | — | `artifact_storage_key`; `artifact_binary` removed; presigned URL download |
| ESI branch code | **Complete** (new) | — | `esi_branch_code` on Organisation; appears in challan export |
| Investment declarations (ESS UI) | **Complete** (new) | — | CRUD with section caps; proof upload is plain text field (no file picker) |
| Expense management | **Complete** (new) | — | Policies, claims, receipts, approvals, reimbursement, payroll handoff |
| Asset lifecycle | **Complete** (new) | — | Catalogue, issuance, acknowledgement, maintenance, return, offboarding gate |
| CT impersonation | Complete | — | |
| CT feature flags | Complete | — | |
| CT guided onboarding | Partial | Medium | Server-persisted checklist in org detail; not a wizard UX |
| CT usage analytics | **Complete** (new) | — | `OrgUsageStat` model, daily aggregation task, CT dashboard cards |
| CT tenant data export | **Complete** (new) | — | ZIP export Celery task, presigned S3 URL, org-admin self-service |
| CT limited write during impersonation | **Complete** (new) | — | Whitelisted operations with mandatory audit log |
| Billing / subscription | Partial | Medium | Licence ledger + webhook abstraction; no payment gateway |
| API versioning `/api/v1/` | **Complete** (new) | — | 410 for legacy bare `/api/` paths |
| Performance management | Partial | Medium | Models + UI scaffolded; review cycles not wired |
| Recruitment / ATS | Partial | Medium | Pipeline present; no onboarding handoff |
| SSO / SAML | Missing | Low | Email/password only |
| Mobile attendance (beyond GPS punch) | Partial | Low | GPS punch present; no dedicated mobile app |

---

## 3. Screen-by-Screen UX Review

### 3.1 CT Dashboard (`/ct/dashboard`)
**What works**: Organisation list, status badges, billing status, usage analytics cards (`OrgUsageStat`).
**UX gaps**: No per-org activity heat map, no quick-action shortcuts (suspend org, bulk licence top-up). Darwinbox's implementation console shows per-tenant health metrics inline.
**Delta from v3**: Usage metric cards added. No structural change otherwise.

### 3.2 CT Organisations → Organisation Detail (`/ct/organisations/:id`)
**What works**: 13-tab navigation — overview, details, licences, admins, employees, onboarding, payroll, attendance, approvals, holidays, configuration, audit, notes. Act-as controls, feature flag toggles, tenant data export trigger, CT write-during-impersonation affordances.
**UX gaps**: Feature flag list has no description for what each flag does. No warning when disabling a module with outstanding records (e.g., disabling payroll with active runs). The "Onboarding" tab shows a checklist, not a step-driven wizard — CT must navigate to the tab, it is not surfaced at new org creation.
**File**: `OrganisationDetailPage.tsx` — 4,912 lines; should be broken into sub-components.

### 3.3 CT Payroll Masters (`/ct/payroll-masters`)
**What works**: Tax slab set CRUD with fiscal year, regime, and age category grouping. `EmptyMasterSlot` click-to-prefill is a strong UX pattern. PT/LWF state list with slab detail modal. Fiscal year format hint (`YYYY-YYYY`).
**UX gap**: Delete uses inline two-step confirm (local state Yes/No), inconsistent with `ConfirmDialog` used everywhere else for destructive actions.
**UX gap**: `PayrollMastersPage.test.tsx` confirms tests for the new interaction flows exist (9 test cases).

### 3.4 Org Admin Payroll Page (`/org/payroll`)
**What works**: Tab navigation. `PayrollPage.tsx` "View Details →" per run row linking to `PayrollRunDetailPage`.
**UX gap**: `PayrollRunDetailPage` table has ESI, PT, TDS columns but **no EPF employee deduction column** (plan spec called for it). This omission means the most common statutory deduction is not visible in the run drill-down.

### 3.5 Payroll Run Detail (`/org/payroll/runs/:id`) — **new in v4**
**What works**: Run header with exception count badge. Summary sidebar (Total Gross / Net / Deductions / Employee Count from aggregated fields). 10-column employee table with expandable inline row breakdown showing all component lines colour-coded by type, with cost centre name. Exception-only filter toggle. Pagination. Per-row payslip PDF preview in modal iframe. Status-gated actions (Submit/Finalize/Rerun). Bulk payslip ZIP download + notify.
**Comparison to Keka**: Matches Keka's run detail feature set. Keka shows additional YTD columns; this can be added incrementally.
**UX gap**: No salary revision comparison view (current vs previous assignment).
**Assessment**: This is the strongest screen in the application.

### 3.6 Employee Payslips Page (`/employee/payslips`)
**What works**: Structured line breakdown panels (earnings, deductions, employer). Fiscal year filter, slip number search. PDF download and fiscal year ZIP download.
**UX gap (P25 incomplete)**: `PayslipsPage.tsx:236` — `<pre className="...overflow-x-auto...">{selectedPayslip.rendered_text}</pre>` is still rendered unconditionally below the structured breakdown. This is the raw text fallback that P25 was supposed to remove. It looks like a developer artifact.
**Fix required**: Remove the `<pre>` block — branded PDF and structured panels supersede it.

### 3.7 Employee Investment Declarations (`/employee/tax-declarations`)
**What works**: CRUD for `InvestmentDeclaration` with section selector, fiscal year filter, section caps, reviewer status, Form 12BB PDF download.
**UX gap**: `proof_file_key` is a plain `<input type="text" placeholder="Optional storage key">`. Employees cannot upload proof documents (rent receipts, PPF statements, insurance premium PDFs) from this screen — they must know their S3 key in advance. This is the single largest ESS UX gap vs Zoho People, which has guided proof upload with document type detection.

### 3.8 Expense Module (`/employee/expenses`, `/org/expenses/...`) — **new in v4**
**What works**: Multi-line claim with policy + category selection (policy-driven limits shown inline), receipt upload per line, draft save / submit dual-action. Reimbursement status badge. Org admin policy management and approval review queue.
**UX gap**: `claim_date` and `expense_date` use native `type="date"` inputs, not `AppDatePicker` — inconsistent with the rest of the app.
**UX gap**: Receipt download uses direct `href={receipt.download_url}` with no inline preview.
**Assessment**: Functionally complete and production-quality for v1 of the module.

### 3.9 Asset Lifecycle Module (`/employee/my-assets`, `/org/assets/...`) — **new in v4**
**What works**: Employee acknowledgement flow with `ConfirmDialog`. Inventory CRUD with asset tags, serial numbers, vendor, category, condition. Assignment and return operations. Offboarding gate for unresolved recoveries.
**UX gap**: Maintenance scheduling form uses `type="date"` native inputs.
**UX gap**: No asset QR code / printable label generation.
**UX gap**: No employee-side damage/loss incident reporting.

### 3.10 Org Chart (`/org/org-chart`) — **new in v4**
**What works**: Recursive `OrgChartBranch` component rendering `reporting_to`-based tree. Inactive employee toggle.
**UX gap (Medium)**: Pure CSS indented tree (`border-l` + `ml-4` pattern). No graphical node boxes, no zoom/pan, no search-within-tree. For orgs with 50+ employees this becomes visually unusable. Zoho People, BambooHR, and Darwinbox use D3/canvas-based interactive charts.

### 3.11 Employee Leave Page (`/employee/leave`)
**What works**: Leave balance display, leave application, approval status, leave history, calendar view, half-day support (via `duration_type`), withdrawal affordance (P20 T6).
**UX gap**: No half-day leave option visually differentiated in the calendar display.

### 3.12 Org Admin Employee List/Detail
**What works**: Custom field rendering in detail page (dynamic, org-configurable). Designation uses `AppSelect` backed by master. Transfer/promotion timeline in `CareerTimeline`. Bulk invite flow.
**UX gap**: No exit interview form visible in `EmployeeDetailPage` — backend models exist but frontend surface is absent.
**UX gap (v3, persists)**: Bank account editing shows masked value; admin could accidentally save masked string as real account number. Should use a separate "Update account number" modal.

---

## 4. Architecture Review

### 4.1 Backend

**API versioning**: All routes are now under `/api/v1/` via `path(f'api/{settings.API_VERSION}/', include(api_v1_patterns))` in `urls.py:70`. Legacy bare `/api/` paths return HTTP 410 (`legacy_api_gone` handler). `API_VERSION = "v1"` is env-configurable. **Complete.**

**Multi-tenancy**: Row-level tenancy intact. Every admin-facing query scoped via `get_active_admin_organisation(request)`. CT users bypass org scoping intentionally (`IsControlTowerUser` permission). No cross-org leaks found in the paths reviewed.

**Models**:
- `StatutoryFilingBatch.artifact_binary` removed; replaced with `artifact_storage_backend` + `artifact_storage_key` + `artifact_uploaded_at`. Filing downloads generate presigned S3 URLs. **Gap from v3 closed.**
- `CostCentre` model added with `gl_code`, `parent` FK (hierarchical), FK from `CompensationTemplateLine` and `CompensationAssignmentLine`.
- `SurchargeRule` model added — DB-configurable surcharge tiers per FY and regime.
- `CustomFieldDefinition` + `CustomFieldValue` for org-configurable employee fields.
- `GeoFencePolicy` per office location with WARN/BLOCK enforcement.
- `EmployeeTransferEvent` + `EmployeePromotionEvent` with approval hooks.
- `Designation` model with FK on `Employee`.

**Indexes** (P26 T2 confirmed):
- `Employee(organisation, status, date_of_joining)` — `employee_org_status_doj_idx` ✅
- `CompensationAssignment(employee, status, effective_from)` — `comp_assign_emp_status_eff_idx` ✅
- `Employee(reporting_to)` and `Employee(department)` — **still missing** (direct reports and department-filtered lists hit table scans at scale)

**Background jobs**:
- Celery idempotency via Redis distributed lock (`cache.add`) on payroll calculation task — **P26 T4 confirmed** ✅
- `CELERY_TASK_ACKS_LATE = True` — task acknowledged after successful completion ✅
- `aggregate_daily_usage_stats` iterates all organisations **without per-org try/except** — one failing org halts the entire aggregation loop. No retry policy on this task.
- `generate_tenant_data_export` Celery task — no `bind=True`, no `max_retries`, no `autoretry_for`. A crash is a silent failure.

**Caching**: Redis (DB 1) used for distributed locks and Celery results. No query result caching. PT/LWF rule pre-cache implemented in `calculate_pay_run()` (P24 T10) — rules pre-fetched as a dict keyed by state_code before the employee loop.

**`ensure_default_document_types()` on every read** (`documents/services.py:90`): `list_onboarding_document_types` calls `ensure_default_document_types()` which issues `update_or_create` for all 33 default document types on **every API call**. This is a hot-path write pattern that should be a one-time management command or `cache.get_or_set` guard.

**Audit URL duplicate include**: `apps.audit.urls` is included in both `ct/` and `org/` URL patterns (`urls.py:32, 43`). Verify that audit endpoints under `org/` are correctly permission-gated and not accessible to org-level employees.

### 4.2 Frontend

**Component architecture**: `PayrollPage.tsx` refactored into `CompensationSection`, `RunsSection`, `FilingsSection` named sub-components (P25 T5). `OrganisationDetailPage.tsx` is still 4,912 lines and should be broken into tab components. `PayrollRunDetailPage.tsx` is appropriately structured.

**Form handling**: No form library (React Hook Form / Zod). Newer forms (expense claims, asset management) use the same `useState` + backend-validation pattern. Two newer forms regress to native `type="date"` inputs instead of `AppDatePicker`.

**Error states**: Mutation errors consistently surface via `toast.error(getErrorMessage(err))`. Query failures (e.g., 500 from run-item list endpoint) **have no inline error state** — the table silently renders empty. `AppErrorBoundary` provides a catch-all via `routes/index.tsx:70`.

**Test coverage**: 41 frontend test files. CT page coverage substantially improved (PayrollMastersPage, CtOrgPayrollPage, OrganisationDetailPage, PayrollRunDetailPage all have interaction-level tests). New module tests for expenses and assets exist. Missing: `TaxDeclarationsPage`, `OrgChartPage`, `NewOrganisationPage`.

### 4.3 Infrastructure

**Logging**: `structlog` configured for JSON in production, human-readable in development (`settings/base.py`). `payroll/services.py` and `organisations/tasks.py` converted to structlog `get_logger`. **P21 T6 complete.**

**Monitoring**: Sentry SDK configured with `traces_sample_rate`, `environment`, and `release` (from `GIT_SHA` env var). Health check at `/api/health/`. **P21 T6 complete.**

**Static assets**: nginx `gzip` enabled for JS/CSS/JSON. CSP header added: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' [S3-origin]; ...`. **P21 T4 complete.**

**Security headers gap**: `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = 'DENY'` are only in `production.py`, not `base.py`. A staging environment using non-production settings inherits none of these headers.

---

## 5. Code Quality Findings

### 5.1 Stale Code (not dead code — see P21 T8 analysis)
- `calculate_professional_tax_monthly` (statutory.py) — confirmed used in tests; intentionally retained
- `DEFAULT_TAX_SLABS` (services.py) — intentional bootstrap fallback with comment; **slabs are FY2024-25 not updated to FY2025-26** (low risk if seed command always runs)
- `_normalize_decimal` / `normalize_decimal` dual presence — 40+ call sites; impractical to remove without coordinated refactor

**Active TODOs indicating known gaps:**
- `form24q.py:236` — `# TODO(P24-T7-001): persist monthly challan tax/cess splits instead of proportionally deriving them` — known approximation in challan generation
- `form24q.py:294` — `# TODO(P24-T7-002): enrich Annexure II once previous-employer and HRA/lender disclosure data is modelled explicitly` — Annexure II incomplete

### 5.2 Unsafe Exception Handling

| File | Line | Pattern | Risk |
|---|---|---|---|
| `employees/services.py` | 716, 723 | `except Exception` swallows payroll/assets imports in `get_employee_offboarding_summary` | No logging — silent failures in a user-visible summary |
| `employees/services.py` | 1020 | `except Exception` swallows entire approvals + leave + events block in `get_employee_dashboard` | Operator blind to bugs in these services |
| `recruitment/views.py` | 187 | `except Exception as exc` — no `# noqa`, no logger | Silent failure in offer letter creation |

### 5.3 Code Patterns

**`__import__()` antipattern in serializers**: `serializers.py` lines 550, 570, 588, 606, 647, 662, 690 use dynamic `__import__('apps.employees.models', fromlist=[...])` inside `class Meta: model = ...`. The models are already imported at the top of the file. Should be replaced with standard top-level imports.

**`soft_delete()` bypassed**: Four service functions (`delete_emergency_contact`, `delete_family_member`, `delete_education_record`, `delete_bank_account`) manually assign `is_deleted=True; deleted_at=now()` instead of calling the `SoftDeleteModel.soft_delete()` method that exists on the model (`models.py:122`).

**Duplicate STATUS_CHOICES**: `EmployeeTransferEvent.STATUS_CHOICES` and `EmployeePromotionEvent.STATUS_CHOICES` are identical 6-item lists defined separately. Should be a shared `EventStatusChoices` TextChoices class.

**`invite_employee` unconditional re-invite overwrite** (services.py:324–331): Re-inviting an existing INVITED/PENDING employee unconditionally overwrites all fields including department, designation, date_of_joining. No guard for "only update if new value is non-empty." A partial re-invite can silently downgrade the employee record.

### 5.4 Test Coverage

**Backend well-covered**: ~623 test functions. Payroll module has ~200 tests covering statutory calculations, run calculation, filings, FnF, investment declarations, cost centres, surcharge DB tiers.

**Backend gaps**:
- FnF leave encashment with non-zero leave balance — no end-to-end test
- Mid-year joiner TDS projection — no test verifying `annual_taxable_gross = taxable_monthly × remaining_months`
- Gratuity eligibility gate inconsistency (4y7m case) — not tested
- Telangana 'TS' alias — not tested
- EPF EPS/EPF split — not covered
- Shift rotation sequence cycling — not tested
- `CAPPED` carry-forward enforcement — not tested
- `ensure_default_document_types()` hot-path write — not benchmarked

**Frontend thin coverage**:
- `TaxDeclarationsPage`, `OrgChartPage`, `NewOrganisationPage` — zero tests
- Query failure error states — no tests
- Proof document upload flow — no tests (the feature doesn't exist yet)
- P18 E2E Playwright journey — explicitly incomplete (P18 plan line 87: `[ ]`)

---

## 6. Security Findings

| # | Finding | Severity | File | Details |
|---|---|---|---|---|
| 1 | Pillow 10.4.0 — CVE-2024-28219 | Low–Medium | `requirements.txt:31` | Buffer overflow in certain image processing modes. Upgrade to Pillow 11.x. |
| 2 | Django 4.2.16 behind 4.2.20 | Low | `requirements.txt:1` | 4 patch releases behind. Check for security advisories in delta. Upgrade recommended. |
| 3 | Non-SSL security headers missing from `base.py` | Low | `settings/base.py` | `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS` are in `production.py` only. A staging environment without `production.py` lacks these headers. Move to `base.py`. |
| 4 | Offboarding PATCH bypasses serializer validation | Low | `employees/views.py:258–261` | `exit_reason` and `exit_notes` read via `request.data.get(...)` directly. No max-length enforcement at API layer; DB column is `CharField(max_255)` and `TextField`. |
| 5 | `generate_download_url` no org scope check | Low | `documents/services.py:216` | Takes any `Document` object. Access control relies entirely on calling views. No test validates cross-employee document access rejection. |
| 6 | ZK_ADMS no application-level auth | Low–Info | `biometrics/views.py:34–85` | ADMS endpoint matches on serial number only; no shared secret. Inherent to the ZKTeco ADMS protocol. Mitigate with IP allowlisting at infrastructure level (not currently enforced). |
| 7 | Mantra/CP PLUS export endpoints no auth | Low–Info | `biometrics/views.py:210–274` | Only `device_id` checked; no secret verification. Add IP allowlisting. |
| 8 | `aggregate_daily_usage_stats` no per-org isolation | Low | `organisations/tasks.py:20–25` | No try/except per org. One failing org aborts all subsequent orgs silently. |
| 9 | Salary data not encrypted at rest | Info | `payroll/models.py` | `monthly_amount` in compensation lines, `PayrollRunItem` amounts stored as plaintext `DecimalField`. Industry standard but worth noting for compliance-sensitive orgs. |
| 10 | `SECRET_KEY` fallback for PII encryption in dev | Info | `common/security.py:37` | `FIELD_ENCRYPTION_KEY` falls back to `SECRET_KEY` in dev. Rotating `SECRET_KEY` makes all dev-encrypted PII unreadable. Production guard prevents deployment without `FIELD_ENCRYPTION_KEY`. |
| 11 | Duplicate `audit.urls` include | Info | `clarisal/urls.py:32, 43` | Included under both `ct/` and `org/` prefixes. Verify that org-level audit endpoints are correctly gated to org-admins only, not org employees. |

**Confirmed resolved from v3**: Missing CSP header, missing magic-byte upload validation, silent decrypt failures, `artifact_binary` in DB, no Sentry, no structured logging.

---

## 7. Indian Compliance Audit

### 7.1 EPF
**Status: Mostly Compliant** — Rates and ceiling correct. **Minor gap**: `calculate_epf_contributions()` (statutory.py:213–227) returns a single `employer` figure without splitting into EPS (8.33%, capped ₹1,250/month) and EPF (3.67%). The ECR export (`filings/ecr.py`) should independently verify that it correctly splits employer contributions. If ECR uses the unsplit figure, ECR submissions will be non-compliant with EPFO format.

PF opt-out: New joiner guard confirmed (services.py:146–153). VPF ≥12% enforcement confirmed.

### 7.2 ESI
**Status: Compliant.** 0.75% employee, 3.25% employer, ₹21,000 ceiling. Half-yearly contribution period correctly handled via `_resolve_esi_eligibility()`. ESI branch code added to Organisation model and challan export (P24 T9 complete).

### 7.3 Professional Tax
**Status: Compliant for 15 states.**

| State | Code | Status | Notes |
|---|---|---|---|
| Maharashtra | MH | ✅ | Gender-split slabs, Feb balancing month |
| Karnataka | KA | ✅ | Updated ₹25,000 threshold (Apr 2025) |
| Tamil Nadu | TN | ✅ | Half-yearly basis |
| West Bengal | WB | ✅ | |
| Andhra Pradesh | AP | ✅ | |
| Telangana | TG | ✅ | **ISO alias 'TS' not mapped** — `PAYROLL_STATE_CODE_ALIASES` missing `'TS': 'TG'` |
| Madhya Pradesh | MP | ✅ | Annual basis |
| Gujarat | GJ | ✅ | New in v4 |
| Haryana | HR | ✅ | New in v4 (district-administered note in seed) |
| Punjab | PB | ✅ | New in v4, female exempt |
| Odisha | OD | ✅ | New in v4 (alias OR→OD handled) |
| Himachal Pradesh | HP | ✅ | New in v4 |
| Chhattisgarh | CT | ✅ | New in v4 (alias CG→CT handled) |
| Jharkhand | JH | ✅ | New in v4 |
| Rajasthan | RJ | ✅ | Zero-PT sentinel; abolished 2017 |

**Missing**: West Bengal LWF (WB has PT; WB LWF is separate — see §7.4).

### 7.4 Labour Welfare Fund
**Status: Compliant for 7 states.** MH (half-yearly), KA, AP, TG, MP, HR, OD (all annual).

**Missing**: West Bengal LWF (significant state; employers with WB offices will produce LWF = 0 silently — no exception is raised for unmapped states).

### 7.5 Income Tax — New Regime FY 2025-26
**Status: Compliant.** ✅ **Fixed from v3.**
- Per-FY/regime `REBATE_87A_PARAMS` dict with `('2025-2026', 'NEW'): (₹12,00,000, ₹60,000)`.
- Tests confirm: income ₹10L → rebate applies; income ₹12L → full rebate; income ₹12.01L → no rebate.
- FY2025-26 7-slab structure correctly seeded.

### 7.6 Income Tax — Old Regime
**Status: Compliant.** Individual/Senior/Super Senior slabs for FY2024-25 and FY2025-26 all present and correct. 80C (₹1.5L), 80D (₹50K), 80TTA (₹10K) deductions applied.

### 7.7 Surcharge
**Status: Mostly Compliant.**
- `NEW_REGIME_SURCHARGE_TIERS`: caps at 25% — **correct** (Finance Act 2023).
- `OLD_REGIME_SURCHARGE_TIERS`: includes 37% at ₹5Cr — **correct** (OLD regime retains 37%).
- `SurchargeRule` DB model added (P24 T6). CT read-only view implemented.
- **Gap**: `seed_surcharge_rules()` does not seed the 37% tier for OLD regime. Harmless today (services.py:1725 uses hardcoded constants), but a latent bug if the call site switches to DB-sourced tiers. Fix: add 37% tier rows for both fiscal years for OLD regime.

### 7.8 Gratuity
**Status: Formula Compliant; Eligibility Gate Bug.**

Formula: `(last_basic / 26) × 15 × years_of_service`, ceiling ₹20L — **correct**.

**Bug**: `_completed_service_years()` (services.py:441–447) uses plain calendar year subtraction (truncates). `calculate_gratuity_service_years()` (statutory.py:303–322) correctly rounds up for >6 months of partial year. The FnF code uses `_completed_service_years()` as the eligibility gate (≥5 years check) and `calculate_gratuity_service_years()` for the amount. An employee with 4 years 7 months will:
- Pass `calculate_gratuity_service_years()` → 5 years (eligible)
- Fail `_completed_service_years()` → 4 years (gate blocks gratuity)
- **Result**: Gratuity = ₹0 despite statutory eligibility.

Fix: Replace the gate at services.py:505–509 to use `calculate_gratuity_service_years() >= 5`.

### 7.9 TDS Monthly Allocation
**Status: Partially Fixed.**

**Fixed (v3 Bug 3)**: Divisor is now `_months_remaining_in_fiscal_year(period_month)`. October joiner: divides by 6. April: divides by 12. ✅

**Residual issue (Medium)**: The annual income projection (`services.py:1710`) is still `taxable_monthly × 12`. For a mid-year joiner, the correct projection is `taxable_monthly × remaining_months`. The fix to the divisor distributes the over-projected tax over fewer months, which means TDS is over-deducted monthly (the extra tax is spread faster). A joiner in October with ₹1.5L/month salary will project annual income as ₹18L (not ₹9L), compute higher annual tax, and divide by 6 months — resulting in roughly double the correct monthly TDS.

Industry standard (Keka, Zoho Payroll): `projected_annual = taxable_monthly × months_remaining`; `monthly_tds = calculate_tax(projected_annual) / months_remaining`.

### 7.10 Form 16 and Form 24Q
**Status: Structurally present; physical FVU validation not yet run.**
- Form 24Q schema aligned against Protean/RPU 4.7 notes and FVU 9.0 release notes (P24 T7 complete).
- Physical validation using NSDL FVU Java JAR not yet performed — explicitly noted as a manual pre-release checklist item in the plan.
- Two known deviations documented as TODO comments: monthly challan tax/cess approximation (form24q.py:236), Annexure II previous-employer data (form24q.py:294).

---

## 8. Control Tower Benchmark

### 8.1 Benchmark Matrix (Updated)

| Capability | Workday | SAP SF | Zoho People | Darwinbox | Clarisal v4 |
|---|---|---|---|---|---|
| Tenant provisioning | Automated | Semi-auto | Guided wizard | Implementation console | Checklist (not wizard) |
| Feature/module toggle per org | Yes | Yes | Yes | Yes | **Yes** |
| Org-level config override | Yes | Yes | Limited | Yes | Partial |
| Impersonation / act-as | Full | Full | Limited | Yes | **Yes** (limited write allowed) |
| Audit trail for super-admin actions | Yes | Yes | Yes | Yes | **Yes** |
| Guided onboarding | Yes | Yes | Yes | Yes | Partial (checklist, not wizard) |
| Usage analytics per org | Yes | Yes | Yes | Yes | **Yes** (daily aggregation) |
| Billing / subscription | Yes | Yes | Yes | Yes | Licence ledger (no gateway) |
| Tenant data export | Yes | Yes | No | Yes | **Yes** (ZIP + presigned URL) |
| CT write during impersonation | Limited | Limited | No | Limited | **Yes** (whitelisted operations) |
| SLA monitoring | Yes | Yes | No | Yes | No |
| SSO / SAML per tenant | Yes | Yes | Yes | Partial | No |

### 8.2 CT Gap List

| Gap | Priority | Notes |
|---|---|---|
| Payment gateway (Razorpay/Stripe) | High | Licence ledger + webhook abstraction present; no automated payment confirmation |
| Guided onboarding wizard UX | Medium | Functional checklist in org detail tab; not a new-org-creation wizard |
| P17 T6 — stale CT inline setup logic | Medium | Still unchecked in plan |
| SSO / SAML per tenant | Medium | Enterprise requirement |
| SLA / queue monitoring | Low | No per-org Celery queue depth or response time monitoring |
| CT write whitelist UI | Low | Backend whitelist enforced; CT UI affordances for unlock/reset could be clearer |

---

## 9. Prioritised Gap List

| # | Area | Gap | Severity | Effort | Recommended Fix | Reference |
|---|---|---|---|---|---|---|
| 1 | Compliance — Gratuity | `_completed_service_years()` gate truncates years; employees with 4y7m+ incorrectly denied gratuity | High | S | Replace gate at services.py:509 with `calculate_gratuity_service_years() >= eligibility_years` | Keka/Darwinbox use the statutory rounding for both eligibility and amount |
| 2 | Compliance — TDS | Annual income projected as `taxable_monthly × 12`; should be `× months_remaining` for mid-year joiners | Medium | S | Change services.py:1710 to `taxable_monthly × _months_remaining_in_fiscal_year(period_month)` | Zoho Payroll, Keka use remaining-months projection |
| 3 | Compliance — Leave | Leave lapse doesn't create `LeaveWithoutPayEntry`; lapsed leave never reaches payroll LWP deduction | Medium | S | In `process_cycle_end_lapse`, call `LeaveWithoutPayEntry.objects.create(source=LEAVE_LAPSE, ...)` after the ledger EXPIRY entry | Model design implies this flow |
| 4 | Compliance — Attend | Two geo-fence systems: web punch uses legacy `allowed_geo_sites`; mobile punch uses `GeoFencePolicy` table | Medium | M | Migrate `record_employee_punch` to read from `GeoFencePolicy` table; deprecate `AttendancePolicy.allowed_geo_sites` | Consistent enforcement required |
| 5 | Compliance — Leave | `CAPPED` carry-forward mode has no enforcement task; only `NONE` mode is lapsed | Medium | S | Add a second Celery task path in `run_leave_lapse_for_all_active_cycles` for `CAPPED` balances | Carries-forward must be capped at cycle-end |
| 6 | Security — Deps | Pillow 10.4.0 has CVE-2024-28219 | Low–Med | S | Upgrade to `Pillow>=11.0.0` in requirements.txt | NIST NVD |
| 7 | Security — Deps | Django 4.2.16 is behind 4.2.20 | Low | S | Upgrade to `Django>=4.2.20` | Django security releases page |
| 8 | Security — Settings | Non-SSL security headers only in production.py | Low | S | Move `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS` to base.py | OWASP |
| 9 | Compliance — Tax | Surcharge seed missing OLD regime 37% tier | Low | S | Add 37% tier rows in `seed_surcharge_rules()` for both FY2024-25 and FY2025-26 OLD regime | Finance Act |
| 10 | Compliance — PT | Telangana ISO alias 'TS' not mapped to seeded code 'TG' | Low | S | Add `'TS': 'TG'` to `PAYROLL_STATE_CODE_ALIASES` in services.py:93 | ISO 3166-2 |
| 11 | Compliance — EPF | Employer EPS/EPF split absent from `calculate_epf_contributions()` | Low | M | Return separate `eps_employer` (8.33%, capped ₹1250) and `epf_employer` (3.67%); verify ECR uses them | EPFO ECR format |
| 12 | UX — ESS | Proof document upload in IT declarations is a plain text field | Medium | M | Replace `proof_file_key` input with `DocumentUploadWidget` backed by existing `documents` S3 flow | Zoho People, Keka offer guided proof upload |
| 13 | UX — ESS | `rendered_text` pre-block still in `PayslipsPage.tsx:236` | Low | S | Remove the `<pre>` block; PDF and structured panels supersede it | P25 cleanup |
| 14 | UX — Payroll | EPF employee column missing from `PayrollRunDetailPage` table | Low | S | Add `epf_employee` column to the 10-column run detail table (plan spec item) | P25 spec |
| 15 | UX — Org Chart | CSS-only indented tree unusable for 50+ employees | Medium | L | Implement D3-based graphical org chart with zoom/pan/search | Darwinbox, BambooHR |
| 16 | UX — HR | Exit interview UI absent from `EmployeeDetailPage` | Medium | M | Build exit interview response form in offboarding tab; backend models complete | BambooHR, Darwinbox |
| 17 | Code — Performance | `ensure_default_document_types()` issues 33 `update_or_create` on every document type list API call | Medium | S | Replace with one-time management command + `cache.get_or_set` guard | Common pattern |
| 18 | Code — Reliability | `aggregate_daily_usage_stats` no per-org error isolation | Medium | S | Wrap each org iteration in try/except with per-org structlog error | Prevents one bad org from silently blocking all others |
| 19 | Code — Reliability | `generate_tenant_data_export` task no retry policy | Low | S | Add `bind=True, max_retries=3, autoretry_for=(Exception,)` | Celery best practice |
| 20 | Code — Quality | `__import__()` antipattern in serializers (7 locations) | Low | S | Replace with standard top-level imports | PEP 8, maintainability |
| 21 | Code — Quality | `soft_delete()` method bypassed in 4 service functions | Low | S | Call `record.soft_delete()` in `delete_emergency_contact`, `delete_family_member`, `delete_education_record`, `delete_bank_account` | DRY |
| 22 | Feature — Attend | LWP deduction uses gross pay base, not basic salary | Info | — | Document as an explicit design choice; most Indian payroll systems use basic | Keka, Greythr use basic salary |
| 23 | Feature — HR | No document expiry tracking | Medium | M | Add `expiry_date` + `expires_soon_days` to `Document`; Celery task alerts for approaching expiry | BambooHR surfaces expiry prominently |
| 24 | Feature — CT | Payment gateway integration | High | XL | Razorpay/Stripe webhook ingestion for automated payment confirmation | Licence lifecycle otherwise manual |
| 25 | Feature — CT | CT guided onboarding as wizard | Medium | L | Implement step-driven `NewOrganisationPage` wizard (not just detail-tab checklist) | Zoho People 8-step wizard |
| 26 | Feature — Payroll | WB Labour Welfare Fund not seeded | Low | S | Seed WB LWF (₹3/month employee, ₹6/month employer — verify current rates) | Simpliance/Greythr reference |
| 27 | Feature — Payroll | FnF TDS on gratuity/leave encashment not computed | Low | L | Calculate tax liability including Section 10(10) and 10(10AA) exemptions explicitly in `_calculate_fnf_totals` | Keka auto-computes FnF tax |
| 28 | Feature — MSS | No dedicated manager/MSS layer | Medium | L | Add "My Team" page with direct-report leave balances, attendance deviations, and filtered approvals | Darwinbox, Keka both have manager mode |
| 29 | Feature — Performance | Review cycle wiring absent | Medium | L | Wire goal cycles → review triggers → 360 feedback → calibration workflow | P10 deferred |
| 30 | Feature — Recruit | No onboarding handoff from ATS | Medium | M | Add "Convert candidate to employee" action at offer acceptance; pre-populate employee invite fields | Darwinbox, Keka both have this flow |

---

## 10. Recommended Roadmap

### Sprint 1 — Statutory Fixes (1–2 weeks, Critical/High compliance risk)

1. **Fix gratuity eligibility gate** (Gap #1): 30-minute fix. Replace `_completed_service_years() >= 5` with `calculate_gratuity_service_years() >= 5` at services.py:509. Run all FnF tests.
2. **Fix TDS annual income projection** (Gap #2): 1 day. Change services.py:1710 to `taxable_monthly × _months_remaining_in_fiscal_year(period_month)`. Add October-joiner test.
3. **Fix leave lapse → LWP cascade** (Gap #3): 1 day. In `process_cycle_end_lapse`, create `LeaveWithoutPayEntry(source=LEAVE_LAPSE)` after the ledger entry. Add CAPPED carry-forward task.
4. **Unify geo-fence systems** (Gap #4): 2 days. Migrate `record_employee_punch` to use `GeoFencePolicy` table; deprecate `allowed_geo_sites` JSON field.

### Sprint 2 — Security and Quality (1 week)

5. **Upgrade Pillow and Django** (Gaps #6, #7): 1 hour. Bump `requirements.txt`.
6. **Move security headers to base.py** (Gap #8): 30 minutes.
7. **Surcharge seed 37% tier and TS alias** (Gaps #9, #10): 30 minutes each.
8. **`ensure_default_document_types()` hot-path fix** (Gap #17): 1 day. Management command + cache guard.
9. **Per-org error isolation in Celery tasks** (Gap #18, #19): 1 day.
10. **`__import__()` → standard imports, `soft_delete()` usage** (Gaps #20, #21): 2 hours.

### Sprint 3 — UX Polish and ESS Completion (2 weeks)

11. **IT declaration proof upload widget** (Gap #12): 2 days. Wire existing S3 document upload to proof_file_key.
12. **Remove `rendered_text` pre-block** (Gap #13): 30 minutes.
13. **Add EPF column to run detail table** (Gap #14): 30 minutes.
14. **Document expiry tracking** (Gap #23): 2 days. `expiry_date` field + Celery alert.
15. **Exit interview UI** (Gap #16): 2 days. Response form in offboarding tab.

### Sprint 4 — Feature Expansion (3–4 weeks)

16. **Graphical org chart** (Gap #15): 3 days. D3 force-directed or tree layout.
17. **Manager MSS layer** (Gap #28): 5 days. "My Team" page with filtered views.
18. **EPF EPS/EPF split** (Gap #11): 2 days. Update `calculate_epf_contributions()` + ECR export.
19. **FnF TDS computation** (Gap #27): 3 days. Section 10(10) + 10(10AA) exemption calculation.
20. **CT guided onboarding wizard** (Gap #25): 5 days. Convert `NewOrganisationPage` to step wizard.

### Sprint 5 — Module Completion and Integrations (4–6 weeks)

21. **Performance review cycle wiring** (Gap #29).
22. **Recruitment → employee onboarding handoff** (Gap #30).
23. **Payment gateway integration** (Gap #24): Razorpay webhook handling.
24. **WB LWF seed** (Gap #26).
25. **Physical Form 24Q FVU validation** (§7.10): Manual pre-release checklist item.

---

*End of HRMS Audit Report v4.0*
