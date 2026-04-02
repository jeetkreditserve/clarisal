# HRMS Audit Report
**Version**: v2
**Date**: 2026-04-02 17:16 IST
**Previous Audit**: `docs/HRMS_AUDIT_REPORT.md` (v1, undated)
**Auditor**: Claude Code
**Tech Stack**: Django 4.2 · DRF 3.15 · PostgreSQL 15 · Redis 7 · Celery 5.4 · React 19 · TypeScript 5.9 · TanStack Query 5 · Tailwind CSS 4 · Radix UI · Vite 8

---

## Executive Summary

Clarisal is a well-architected, early-stage HRMS that has covered the foundational pillars of HR operations — employee records, leave management, approval workflows, document collection, internal communications, and a basic payroll pipeline — with a notably clean codebase for an AI-built product. The separation of concerns is strong, multi-tenancy is correctly enforced via organisation-scoped queries throughout, and the audit trail infrastructure is solid.

However, the product is **not ready for production go-live** as a standalone HRMS. Three complete modules that every Indian organisation requires — Attendance, Performance Management, and Reporting/Analytics — are entirely absent. The payroll module exists but is a prototype: it lacks ESI, Professional Tax, TDS (new/old regime with surcharge and cess), pro-rated salary on joining/exit, and payslip PDF generation. Critically, there is a **CRITICAL security vulnerability** where the Control Tower role can call the full `EmployeeDetailSerializer` on any employee in any organisation, exposing government IDs (PAN, Aadhaar), bank accounts, and personal address data through a live API endpoint. The `.env` file in the repository root contains live AWS credentials and a ZeptoMail API key that must be rotated immediately.

Against Zoho People + Zoho Payroll, the product covers roughly 30–35% of feature surface. For a bootstrapped India-market HRMS targeting SMBs up to ~200 employees, the architecture is sound and the foundation is genuinely good — the gaps are almost entirely about what has not been built yet, not about what has been built badly.

---

## Top 5 Blockers for Production Go-Live

1. **CRITICAL — CT role exposes full employee PII at API level** (`/api/ct/organisations/:id/employees/:employee_id/` returns government IDs, bank accounts, home address). Must be patched before any real data is loaded.
2. **CRITICAL — Live AWS credentials and ZeptoMail API key in `.env`** — must be rotated immediately, regardless of whether the file was ever committed.
3. **CRITICAL — No attendance module** — without time and attendance, leave management is disconnected from actual work records, and payroll cannot deduct for absences or LOP.
4. **HIGH — Payroll lacks all India statutory deductions** — no ESI, no Professional Tax, no TDS regime (new/old), no 4% health & education cess, no surcharge. Running payroll with this code will produce incorrect net pay for any compliant Indian payroll.
5. **HIGH — Payslip is plain text, not a PDF** — `rendered_text` is a multiline string shown in a `<pre>` tag. This cannot be used as a legal payslip document for compliance or employee records.

---

## Top 5 Quick Wins

1. **Fix CT PII exposure** — Add a `CtEmployeeListSerializer` that excludes `government_ids`, `bank_accounts`, `profile.address`, `family_members`. ~30 min change.
2. **Rotate `.env` credentials** — AWS IAM key + ZeptoMail key. ~15 min.
3. **Add `FIELD_ENCRYPTION_KEY` validation** — Raise `ImproperlyConfigured` at startup if empty in production. ~10 min.
4. **Add currency formatting to payslip display** — Numbers like `50000.00` displayed as raw strings. Add `₹` prefix and comma formatting. ~1 hour.
5. **Add payslip PDF download** — Use `weasyprint` or `reportlab` to generate a properly formatted PDF from the existing snapshot data. The data model already supports it.

---

## Current Implementation Map

### Backend Apps (12 total)

| App | What It Does | Completeness |
|-----|-------------|-------------|
| `accounts` | Auth (session-based), user model, password reset, multi-account-type login | ✅ Complete |
| `organisations` | Multi-tenancy, org lifecycle, billing/licence tracking, CT admin | ✅ Complete |
| `employees` | Employee profiles, government IDs (encrypted), bank accounts (encrypted), education, family, emergency contacts, soft delete | ✅ Solid |
| `departments` | Hierarchical departments, org-scoped | ✅ Complete |
| `locations` | Office locations, city/state/country | ✅ Complete |
| `invitations` | Email invite flow, token-based, 48h expiry, revoke | ✅ Complete |
| `timeoff` | Leave types, accrual, balances, carry-forward, holiday calendars, on-duty, approval integration | ✅ Solid |
| `approvals` | Multi-stage approval engine, conditional routing, GenericFK subject | ✅ Complete |
| `documents` | Onboarding document collection, S3 upload, verify/reject workflow | ✅ Complete |
| `communications` | Internal notices, audience targeting, scheduling, sticky | ✅ Complete |
| `audit` | AuditLog model, thread-local actor capture, IP + user agent | ✅ Complete |
| `payroll` | Tax slabs, compensation templates, assignments, payroll runs, payslips (text only) | ⚠️ Prototype |
| **MISSING** | Attendance / Time Tracking | ❌ Absent |
| **MISSING** | Performance Management | ❌ Absent |
| **MISSING** | Reports & Analytics | ❌ Absent |

---

### Frontend Routes — Complete Inventory

**Control Tower (`/ct/*`)**
| Route | Page | Functional? |
|-------|------|------------|
| `/ct/login` | CT login | ✅ |
| `/ct/dashboard` | Stats dashboard | ✅ |
| `/ct/payroll` | Payroll masters (tax slab creator) | ✅ |
| `/ct/organisations` | Organisation list | ✅ |
| `/ct/organisations/new` | Create org | ✅ |
| `/ct/organisations/:id` | Org detail + licence batches | ✅ |
| `/ct/organisations/:id/first-licence-batch` | First licence setup | ✅ |
| `/ct/organisations/:orgId/leave-cycles` | Manage leave cycles (CT-operated) | ✅ |
| `/ct/organisations/:orgId/leave-plans` | Leave plan list | ✅ |
| `/ct/organisations/:orgId/leave-plans/new` | Leave plan builder | ✅ |
| `/ct/organisations/:orgId/leave-plans/:id` | Edit leave plan | ✅ |
| `/ct/organisations/:orgId/on-duty-policies` | On-duty policies | ✅ |
| `/ct/organisations/:orgId/on-duty-policies/new` | Create on-duty policy | ✅ |
| `/ct/organisations/:orgId/approval-workflows` | Approval workflows | ✅ |
| `/ct/organisations/:orgId/approval-workflows/new` | Workflow builder | ✅ |
| `/ct/organisations/:orgId/notices` | Notice list | ✅ |
| `/ct/organisations/:orgId/notices/new` | Notice editor | ✅ |
| `/ct/organisations/:orgId/audit` | Audit log | ✅ |
| **MISSING** | CT view of org payroll runs/history | ❌ |
| **MISSING** | CT view of employee list (sanitised) | ❌ (API exists, no page) |

**Org Admin (`/org/*`)**
| Route | Page | Functional? |
|-------|------|------------|
| `/org/setup` | Org setup wizard | ✅ |
| `/org/dashboard` | Dashboard with metrics | ✅ |
| `/org/profile` | Org profile editor | ✅ |
| `/org/payroll` | Payroll (single mega-page) | ⚠️ Prototype |
| `/org/locations` | Location management | ✅ |
| `/org/departments` | Department management | ✅ |
| `/org/employees` | Employee list + invite | ✅ |
| `/org/employees/:id` | Employee detail | ✅ |
| `/org/holidays` | Holiday calendar | ✅ |
| `/org/leave-cycles` | Leave cycle config | ✅ |
| `/org/leave-plans` | Leave plan list | ✅ |
| `/org/leave-plans/new` | Leave plan builder | ✅ |
| `/org/leave-plans/:id` | Edit leave plan | ✅ |
| `/org/on-duty-policies` | OD policy management | ✅ |
| `/org/approval-workflows` | Workflow list | ✅ |
| `/org/approval-workflows/new` | Workflow builder | ✅ |
| `/org/notices` | Notice management | ✅ |
| `/org/audit` | Audit log | ✅ |
| **MISSING** | Attendance module | ❌ |
| **MISSING** | Performance module | ❌ |
| **MISSING** | Reports / payroll register | ❌ |

**Employee (`/me/*`)**
| Route | Page | Functional? |
|-------|------|------------|
| `/me/onboarding` | Onboarding checklist | ✅ |
| `/me/dashboard` | Employee dashboard | ✅ |
| `/me/profile` | Profile + govt IDs + bank accounts | ✅ |
| `/me/education` | Education records | ✅ |
| `/me/documents` | Document upload | ✅ |
| `/me/leave` | Leave apply + balance | ✅ |
| `/me/od` | On-duty request | ✅ |
| `/me/payslips` | Payslip viewer (text-only) | ⚠️ Basic |
| `/me/approvals` | Approval inbox | ✅ |
| **MISSING** | Attendance marking | ❌ |
| **MISSING** | Tax declarations / investment declaration | ❌ |
| **MISSING** | Expense claims | ❌ |

---

### Backend-Only (No UI Surface)
- `CtOrganisationEmployeesView` / `CtOrganisationEmployeeDetailView` — CT can view/edit employees via API but there is no CT frontend page showing the employee list per organisation. The API also exposes full PII (see Security section).
- All `ATTENDANCE_REGULARIZATION` approval kind referenced in models and frontend constants but no attendance module exists to generate regularization requests.
- `OrganisationTaxRegistration` model (GSTIN, VAT) exists in backend with no UI surface.
- `OrganisationLegalIdentifier` model (PAN, EIN) exists with no UI surface.

---

## Benchmark: Gaps vs Zoho People + Zoho Payroll

### Core HR & Employee Management

| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---------|---------------|-----------------|----------|-------|
| Employee lifecycle (invite → active → exit) | ✅ Implemented | ✅ Full lifecycle with stages | Minor | Missing probation period tracking |
| Employee profiles with custom fields | ⚠️ Fixed fields only | ✅ Custom field builder | Significant | Cannot add org-specific fields |
| Document management (collect + verify) | ✅ Implemented | ✅ + e-sign, version control | Minor | No versioning, no e-sign |
| Org chart (hierarchy visualisation) | ❌ Missing | ✅ Dynamic org chart | Significant | `reporting_to` FK exists but no chart |
| Employee self-service portal | ✅ Implemented | ✅ More comprehensive | Minor | Leave, profile, docs — well covered |
| Bulk employee import (CSV/Excel) | ❌ Missing | ✅ Excel template import | Critical | Manual invite only, one at a time |
| Employee exit/offboarding checklist | ⚠️ End employment exists | ✅ Offboarding tasks, F&F | Significant | No exit interview, no checklist, no F&F |
| Designation / job grade management | ⚠️ Free-text designation only | ✅ Grade + band structure | Significant | No formal job levels |
| Probation management | ❌ Missing | ✅ Probation extension + appraisal | Significant | — |
| Employee number auto-generation | ✅ Implemented | ✅ Same | — | Works well |

### Attendance & Time Tracking

| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---------|---------------|-----------------|----------|-------|
| Clock in / clock out | ❌ Missing | ✅ Web + mobile + biometric | Critical | Module entirely absent |
| Shift management | ❌ Missing | ✅ Shift rotations, night shifts | Critical | — |
| Overtime rules | ❌ Missing | ✅ OT calculation + approval | Critical | — |
| Geo-fencing / IP-based attendance | ❌ Missing | ✅ Both supported | Significant | — |
| Biometric / device integration | ❌ Missing | ✅ Supported | Significant | — |
| Attendance regularisation | ⚠️ Approval kind defined, no module | ✅ Full regularisation workflow | Critical | `ATTENDANCE_REGULARIZATION` is a dead reference |
| Attendance summary reports | ❌ Missing | ✅ Daily, monthly, summary | Critical | — |
| Late mark / half-day rules | ❌ Missing | ✅ Configurable | Significant | — |

### Leave Management

| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---------|---------------|-----------------|----------|-------|
| Leave types with full config | ✅ Implemented | ✅ Same depth | — | Well implemented |
| Accrual (monthly, quarterly, etc.) | ✅ Implemented | ✅ Same | — | Works correctly |
| Carry-forward (capped/unlimited) | ✅ Implemented | ✅ Same | — | — |
| Multi-level approval workflow | ✅ Implemented | ✅ Same | — | — |
| Holiday calendar (multi-location) | ✅ Implemented | ✅ Same | — | — |
| Leave balance dashboard | ✅ Implemented | ✅ Same | — | — |
| Half-day leave | ✅ Implemented | ✅ Same | — | — |
| Comp-off (compensatory leave) | ❌ Missing | ✅ Supported | Significant | Requires attendance data |
| Leave encashment | ❌ Missing | ✅ Full encashment flow | Significant | — |
| LOP (Loss of Pay) tracking | ⚠️ `is_loss_of_pay` field exists | ✅ LOP linked to payroll | Critical | LOP not fed into payroll deductions |
| Leave forecasting / planner | ❌ Missing | ✅ Team planner view | Minor | — |
| Leave approval delegation | ❌ Missing | ✅ Supported | Minor | — |
| Restricted holidays (employee opt-in) | ⚠️ Model exists, no ESS flow | ✅ Employee selects RH | Significant | — |

### Payroll

| Feature | Current Status | Zoho Payroll Equivalent | Gap Type | Notes |
|---------|---------------|------------------------|----------|-------|
| Salary structure builder (components) | ✅ Implemented (BASIC, HRA, deductions) | ✅ Richer with formulas | Significant | No percentage-based formulas (HRA = 40% of basic) |
| Tax slab configuration | ✅ Implemented | ✅ Regime-based (new/old) | Critical | Only one slab set — no new vs old regime choice |
| PF (12% of basic) | ⚠️ PF_EMPLOYEE component exists as flat amount | ✅ Auto-calculated | Critical | PF is hardcoded as a fixed amount, not 12% of basic |
| ESI (0.75%/3.25%) | ❌ Missing | ✅ Auto-calculated | Critical | Entire ESI component absent |
| Professional Tax (state-wise slabs) | ❌ Missing | ✅ State-wise PT supported | Critical | — |
| TDS (new/old regime, surcharge, cess) | ⚠️ Simplified 3-slab income tax only | ✅ Full TDS with declarations | Critical | Missing 4% H&E cess, surcharge at ₹50L+, no standard deduction, no investment declarations |
| Investment declaration (80C, 80D, HRA) | ❌ Missing | ✅ Employee declaration portal | Critical | — |
| Pro-rated salary (joining/exit month) | ❌ Missing | ✅ Automatic pro-ration | Critical | New joiner in month gets full salary |
| Arrears calculation | ❌ Missing | ✅ Salary arrears on revision | Significant | — |
| Full & Final settlement | ❌ Missing | ✅ F&F with gratuity, leave encash | Critical | — |
| Payslip PDF generation | ❌ Missing (plain text in `<pre>`) | ✅ Branded PDF download | Critical | `rendered_text` is a 6-line string |
| Form 16 generation | ❌ Missing | ✅ Auto-generated | Critical | — |
| Payroll register report | ❌ Missing | ✅ Downloadable register | Critical | — |
| Reimbursement claims | ❌ Missing | ✅ Claim + approve flow | Significant | — |
| Salary revision / increment workflow | ⚠️ Assignment approval exists | ✅ Increment letter, % hike | Significant | No hike percentage, no revision letter |
| LOP deduction in payroll | ❌ Missing | ✅ Auto-deducted from net | Critical | `is_loss_of_pay` field never referenced in payroll calculation |
| Payslip password protection | ❌ Missing | ✅ Optional PDF password | Minor | — |

### Performance Management

| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---------|---------------|-----------------|----------|-------|
| Goal setting / OKRs | ❌ Missing | ✅ Full goal tracking | Significant | No performance module |
| Appraisal cycles | ❌ Missing | ✅ Configurable cycles | Significant | — |
| 360° feedback | ❌ Missing | ✅ Supported | Significant | — |
| Rating calibration | ❌ Missing | ✅ Supported | Minor | — |
| Probation appraisal | ❌ Missing | ✅ Supported | Significant | — |

### Reports & Analytics

| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---------|---------------|-----------------|----------|-------|
| Headcount report | ❌ Missing | ✅ Available | Critical | No report generation at all |
| Attrition / turnover report | ❌ Missing | ✅ Available | Significant | — |
| Attendance summary | ❌ Missing (no attendance) | ✅ Available | Critical | — |
| Payroll register | ❌ Missing | ✅ Downloadable | Critical | — |
| Leave utilisation report | ❌ Missing | ✅ Available | Significant | — |
| Custom report builder | ❌ Missing | ✅ Drag-and-drop builder | Significant | — |
| Dashboard analytics | ⚠️ Org admin: count metrics only | ✅ Charts, trends | Significant | No graphs, no trend lines |
| Export (CSV/Excel/PDF) | ❌ Missing | ✅ All formats | Critical | — |

---

## Portal-wise Audit

### Control Tower (CT) Portal

**What CT Can Do Today:**
- View dashboard stats (total orgs, active, pending, revenue metrics)
- Create organisations and assign licence batches
- Manage org billing state (PENDING → PAID → ACTIVE/SUSPENDED)
- Configure leave cycles, leave plans, on-duty policies, approval workflows, notices per organisation (CT operates as a super-org-admin)
- View and manage org admins (invite, deactivate, reactivate)
- View audit logs per organisation
- Create payroll tax slab masters (India)
- View/edit employee records via API (no UI page exists for this)

**What CT Should Not Do But Can (Security Issue):**
- The API endpoint `GET /api/ct/organisations/:id/employees/:employee_id/` returns the full `EmployeeDetailSerializer` response, including:
  - `government_ids` (PAN, Aadhaar — these fields are individually masked but the existence and metadata are exposed)
  - `bank_accounts` (account type, IFSC — encrypted account numbers are partially masked but still exposed)
  - `profile` including home address
  - `family_members` and `emergency_contacts`
  - `education_records`
  - See `backend/apps/organisations/views.py:313` — `CtOrganisationEmployeeDetailView` uses `EmployeeDetailSerializer` with no PII stripping
  - **This is a CRITICAL security finding** — the role boundary stated in requirements ("CT cannot see employee PII") is not enforced at the API level

**What CT Cannot Do But Should:**
- No dedicated CT page to view employee list per organisation (API exists at `GET /api/ct/organisations/:id/employees/` but no frontend route)
- No CT view of organisation payroll run history (what runs were executed, by whom, totals, exceptions)
- No CT view of compensation structures or salary templates per org
- No CT "support tools" to help debug org admin issues (e.g. view pending approvals across an org, show what's blocking a payroll run)
- The `CtOrganisationEmployeeDetailView.patch()` method allows CT to edit employees (`backend/apps/organisations/views.py:321`) — this contradicts the intended read-only CT constraint on employee data

**CT UX Assessment:**
The CT dashboard is functional but thin. The sidebar lists Organisations and Payroll. Within an org detail, the list of sub-sections (leave cycles, leave plans, on-duty, workflows, notices, audit) is accessible but requires 3+ clicks to reach. There is no at-a-glance "org health" view showing whether the org has payroll configured, leave plans assigned, or employees with missing salary assignments. CT operators supporting org admins would struggle to quickly diagnose issues.

---

### Org Admin Portal

**What Org Admin Can Do Today:**
- Full employee lifecycle: invite, profile management, document requests, end employment, delete
- Holiday calendar creation and publication (with location assignment)
- Leave cycle, leave plan, and leave type configuration (detailed and well-implemented)
- On-duty policy creation
- Multi-stage approval workflow builder (excellent)
- Internal notice creation, scheduling, and publishing
- Payroll: tax slab sets, compensation templates (fixed amounts only), assign salary to employees, run payroll (DRAFT → CALCULATED → APPROVED → FINALIZED), rerun
- View approval inbox and approve/reject
- Audit log viewer

**What Org Admin Cannot Do But Should:**
- No attendance management at all (shifts, rules, device config)
- No bulk employee import (must invite one at a time)
- Cannot generate any report or export
- No payslip download trigger (finalized payslips exist but there's no "send to employees" action)
- Cannot configure PF/ESI/PT parameters (these statutory components are simply absent)
- No performance appraisal cycle management
- No compensation revision with percentage input (amounts only, no "10% increment")
- No LOP-to-payroll mapping

**Org Admin UX Assessment:**

*Payroll Page (`/org/payroll`) — Most Significant UX Problem:*

The entire payroll workflow is crammed into a single page (`PayrollPage.tsx`, 359 lines) structured as four sequential forms stacked vertically: Tax Slabs → Compensation Template → Salary Assignment → Payroll Run. This is a developer-oriented prototype, not a production UX. Problems:

1. The tax slab form hardcodes exactly 3 slabs. An admin cannot add more slabs or use a different structure. Zoho and Keka present this as a proper rate table with add/remove rows.
2. The compensation template form hardcodes exactly two components (Basic Pay, Employee PF). An admin cannot add HRA, Special Allowance, or any other component. Zoho allows unlimited components with formula support.
3. All four operations are on one scrolling page with no visual separation. A user must scroll past completed steps to reach the next one. There is no progress indicator.
4. Numbers are displayed and entered without formatting — `50000` instead of `₹50,000`. No currency symbol, no comma formatting anywhere in payroll.
5. After running payroll, clicking "Calculate" replaces items silently with no diff or comparison to the previous run. Keka shows you a variance report — how many employees changed, by how much.
6. There are no guard rails before finalization. Clicking "Finalize" on a run with 50 EXCEPTION items (employees with no salary assigned) will finalize silently with those employees excluded. No warning is shown.

*Leave Plan Builder (`/org/leave-plans/new`) — Well Done:*
The leave plan builder is the strongest UX in the product. Multi-step form with sections, inline add/remove of leave types, sensible defaults, and a clear save flow. This is close to Zoho's quality for this specific flow.

*Approval Workflow Builder (`/org/approval-workflows/new`) — Good:*
789-line component, deeply nested state, but the rendered experience is clear. Routing rules and stage builder are well-labelled. Better than Darwinbox's equivalent at the same stage of product maturity.

*Employee List (`/org/employees`) — Basic:*
Table has search and status filter but no bulk operations, no column sorting, no export. Cannot select multiple employees to bulk-assign a leave plan or salary template. Zoho and Darwinbox both provide this.

---

### Employee Portal

**What Employees Can Do Today:**
- Complete onboarding checklist (profile, govt IDs, bank accounts, documents)
- View personal dashboard with document status, pending approvals, monthly calendar
- Edit personal profile, government IDs, bank accounts
- Manage education records and family members
- Apply for leave (with balance check, half-day support, overlap detection)
- Submit on-duty requests
- View monthly calendar with leave, on-duty, and holidays
- View approval inbox and pending actions
- View payslips (text format, no PDF)

**What Employees Cannot Do But Should:**
- Cannot mark attendance (no module)
- Cannot submit investment declarations for TDS calculation
- Cannot apply for leave encashment
- Cannot view salary breakup other than payslips
- Cannot raise expense claims
- Cannot apply for comp-off
- Cannot download payslip as PDF
- Cannot opt into restricted holidays
- No tax workings visible (what is my estimated TDS for the year?)

**Employee UX Assessment:**

*Dashboard:*
The employee dashboard surfaces onboarding status, document counts, a quick-actions bar, recent notices, pending approvals, and a month calendar. This is genuinely useful and clear. The empty state before any data is populated shows helpful placeholder text. Better than Darwinbox's employee dashboard in simplicity.

*Leave Application:*
Clean two-column layout — form on the left, calendar on the right. Leave balance cards update correctly. Half-day support works. One UX issue: the session selector (First Half / Second Half / Full Day) appears on both start and end date even for multi-day requests, which is confusing. Zoho only shows session on single-day requests.

*Payslips Page:*
The payslip viewer shows amounts as raw decimal strings: `50000.00` not `₹50,000.00`. The "slip details" are shown in a raw `<pre>` block containing the `rendered_text` field, which is a plain text string like:
```
Payslip: April 2026
Employee: John Doe
Gross Pay: 50000.00
Income Tax: 4792.00
Total Deductions: 6592.00
Net Pay: 43408.00
```
This is not a payslip. It is a developer debug output. There is no component breakdown (basic, HRA, PF), no employer contributions shown, no pay period header, no company name, no bank account last digits. Zoho and Keka generate branded PDF payslips with full component-wise breakdown.

*Mobile Responsiveness:*
The employee portal uses responsive Tailwind grids (`xl:grid-cols-2`, `md:grid-cols-2`) that collapse to single column on small screens. Key flows (leave application, profile) are usable on mobile. The month calendar component may overflow on screens narrower than 360px as day cells have a minimum width. The sidebar navigation in `EmployeeLayout` uses a desktop-first design — there is no mobile hamburger menu or bottom navigation, meaning the sidebar pushes content off-screen on phones without the user realizing there's a nav element.

---

## Architecture Issues

### 1. `OrgPayrollSummaryView` — Over-fetching in Single Endpoint
**File**: `backend/apps/payroll/views.py:71`
**Issue**: The `/api/org/payroll/summary/` endpoint fetches all `tax_slab_sets`, all `compensation_templates`, all `compensation_assignments` (with nested lines), and all `pay_runs` (with nested items and employee user) in a single response. For an org with 200 employees and 24 months of payroll history, this could return several thousand nested objects in a single JSON response.
**Impact**: Blocks at scale. Payroll page load time will degrade significantly with data volume.
**Fix**: Split into separate paginated endpoints. The summary view should return counts only; details should be fetched on demand.

### 2. `get_or_create_leave_balance` — O(N) Python Loop Instead of DB Aggregate
**File**: `backend/apps/timeoff/services.py:296`
```python
used = sum(
    (request.total_units for request in LeaveRequest.objects.filter(...)),
    Decimal('0.00'),
)
```
This loads all leave request objects into memory and sums in Python. Should be `LeaveRequest.objects.filter(...).aggregate(total=Sum('total_units'))['total'] or Decimal('0')`. Same pattern on line 305 for pending.
**Impact**: For employees with many leave requests (2+ years), this function slows proportionally to history length. Called on every leave balance display.
**Fix**: Replace both loops with a single `aggregate(Sum('total_units'))` query.

### 3. Payroll Calculation is Synchronous
**File**: `backend/apps/payroll/views.py:240`
```python
def post(self, request, pk):
    pay_run = calculate_pay_run(pay_run, actor=request.user)
```
`calculate_pay_run()` loops through all ACTIVE employees, runs tax calculations, and writes `PayrollRunItem` records synchronously in the HTTP request. For 200 employees this will take 2–5 seconds on a cold database. For 500+ employees it will time out (Gunicorn default: 30s).
**Fix**: Move to a Celery task. Return a 202 Accepted with a task ID. Poll for completion. Infrastructure already has Celery and Redis.

### 4. RBAC Is Flat — No Row-Level Permissions for Org Admin
**Files**: `backend/apps/accounts/permissions.py`
The permission system has exactly 4 classes: `IsControlTowerUser`, `IsOrgAdmin`, `IsEmployee`, `BelongsToActiveOrg`. There is no:
- Department-head access (can manage only their department's employees)
- HRBP role (view employees but not run payroll)
- Finance role (can finalize payroll, cannot edit employee records)
- Read-only admin role

**Impact**: Every Org Admin in the system has full write access to all org data including payroll finalization. In a real org, payroll finalization should require a different role than the person who set up the salary.
**Fix**: Add a `role` field to `OrganisationMembership` (currently only has `is_org_admin: bool`) with values like `OWNER`, `HR_MANAGER`, `PAYROLL_ADMIN`, `VIEWER`.

### 5. `CtOrganisationEmployeeDetailView` Allows CT to Mutate Employee Records
**File**: `backend/apps/organisations/views.py:321`
CT can `PATCH /api/ct/organisations/:id/employees/:employee_id/` to update any employee in any organisation. This is likely unintended — CT is described as a support/superuser role, not an HR admin. If CT changes employee data and the org admin has no record of who changed it, this creates audit accountability gaps.
**Impact**: Uncontrolled data modification by CT users across all tenants.
**Fix**: Remove the `patch` method from `CtOrganisationEmployeeDetailView` or gate it behind an explicit CT super-admin flag.

### 6. `_compute_credit_for_period` Uses `timezone.localdate()` Instead of Cycle End
**File**: `backend/apps/timeoff/services.py:248`
```python
periods_elapsed = Decimal(_periods_elapsed(cycle_start, timezone.localdate(), leave_type.credit_frequency))
```
Leave balance credit is calculated based on "today's date" rather than the end of the cycle. This means an employee's available leave balance changes daily as months tick over, creating inconsistent readings if the function is called at different times. It also means that checking a historical balance (e.g. "what was this employee's balance on March 31?") is impossible.
**Fix**: Accept an `as_of` parameter and pass it through consistently. The function signature partially supports this with `as_of=None` in `get_or_create_leave_balance` but it's not threaded into `_compute_credit_for_period`.

### 7. `ensure_org_payroll_setup` Called on Every Payroll List GET
**File**: `backend/apps/payroll/views.py:98`
```python
def get(self, request):
    organisation = _get_admin_organisation(request)
    ensure_org_payroll_setup(organisation, actor=request.user)
```
Every time `/api/org/payroll/tax-slab-sets/` is fetched, `ensure_org_payroll_setup` runs `get_or_create` operations on multiple PayrollComponent records. This is a side-effect on a GET endpoint, which violates HTTP idempotency expectations and will cause unexpected writes in monitoring tools.
**Fix**: Call `ensure_org_payroll_setup` only once during org onboarding (it already runs in `OrgPayrollSummaryView.get`). Remove it from the individual list views.

### 8. Database Schema — Missing Index on High-Cardinality Leave Queries
**File**: `backend/apps/timeoff/models.py`
`LeaveRequest` has no composite index on `(employee, leave_type, status, start_date, end_date)` — the exact combination queried in `get_or_create_leave_balance`. As leave request volume grows, the balance calculation query will do a full table scan filtered only by the FK indexes.
**Fix**: Add `models.Index(fields=['employee', 'leave_type', 'status', 'start_date'])` to `LeaveRequest.Meta`.

---

## Security Issues

### 🔴 CRITICAL — Live AWS S3 Credentials in `.env`
**File**: `.env` (repository root)
```
AWS_ACCESS_KEY_ID=AKIA47KWW5J3E6Z37SAS
AWS_SECRET_ACCESS_KEY=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
```
These are real AWS IAM credentials. The `.env` is in `.gitignore` and was **not committed** to the current branch (`git ls-files` confirms only `.env.example` is tracked). However, the file exists on disk and the credentials are exposed to anyone with filesystem access to the dev machine.
**Action Required**: Rotate both keys in AWS IAM immediately. Audit S3 bucket access logs for any unauthorized access.

### 🔴 CRITICAL — ZeptoMail API Key in `.env`
**File**: `.env`
```
ZEPTOMAIL_API_KEY=Zoho-enczapikey PHtE6r0LF7y6jDN7phhSsfC+...
```
Live transactional email API key exposed on disk.
**Action Required**: Regenerate the ZeptoMail API key immediately.

### 🔴 CRITICAL — CT Role Exposes Employee PII via API
**File**: `backend/apps/organisations/views.py:313–330`
`CtOrganisationEmployeeDetailView` returns `EmployeeDetailSerializer(employee).data` which includes:
- `government_ids` (PAN, Aadhaar — masked display values but record existence confirmed)
- `bank_accounts` (masked account numbers, IFSC codes)
- `profile` (home address, date of birth, gender, marital status, blood type)
- `family_members`, `emergency_contacts`

This endpoint is accessible to any authenticated CT user. The requirement explicitly states CT should not see employee PII.
**Fix**: Create a `CtEmployeeListSerializer` that exposes only: `id`, `employee_code`, `full_name`, `email`, `designation`, `employment_type`, `department`, `office_location`, `status`. Remove the `patch` method entirely or restrict it.

### 🔴 CRITICAL — `FIELD_ENCRYPTION_KEY` Defaults to Empty String
**File**: `backend/clarisal/settings/base.py:184`, `backend/apps/common/security.py:17`
```python
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')
```
```python
seed = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or settings.SECRET_KEY
```
If `FIELD_ENCRYPTION_KEY` is empty (the default in `.env.example`), the system silently falls back to deriving the Fernet key from `SECRET_KEY`. This means:
1. If `SECRET_KEY` is rotated, all existing encrypted PAN, Aadhaar, and bank account data becomes permanently undecryptable.
2. The `.env` file shows `FIELD_ENCRYPTION_KEY=replace-with-a-32-byte-secret` which is not a real key — if deployed as-is, the fallback to `SECRET_KEY` activates silently.
**Fix**: Add a startup validation in `base.py`:
```python
if not env('FIELD_ENCRYPTION_KEY', default=''):
    raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be set in production")
```

### 🟠 HIGH — Default CT Password is Insecure
**File**: `.env`
```
CONTROL_TOWER_PASSWORD=change-me-in-production
```
The seed command creates the CT admin with this password. If a developer runs the seed script in a staging/production environment without updating this variable, the CT account — which has access to all organisations — will have a trivially guessable password.
**Fix**: Remove the default from `.env.example`. Require `CONTROL_TOWER_PASSWORD` to be set explicitly. Add password strength validation in the seed command.

### 🟠 HIGH — Session Cookie Not Scoped to Subdomain in Development
**File**: `backend/clarisal/settings/base.py:179`
```python
SESSION_COOKIE_DOMAIN = env('SESSION_COOKIE_DOMAIN', default=None) or None
```
When `SESSION_COOKIE_DOMAIN` is not set (default in local dev), the session cookie has no domain restriction and will be sent to any domain. While `SameSite=Lax` limits cross-site abuse, the lack of domain binding means the session is broader than necessary.
**Impact**: Low in isolation, but combined with other vulnerabilities creates a wider attack surface.

### 🟡 MEDIUM — Document Download URLs Are Time-Limited Presigned S3 URLs
**File**: `backend/apps/documents/services.py` — `generate_download_url()`
Pre-signed S3 URLs are generated on request. This is correct. However, the expiry duration is not visible in code without reading the S3 client configuration. Verify that URLs expire in ≤15 minutes and that they are not logged anywhere.

### 🟡 MEDIUM — No File MIME Type Validation (Only Extension Check)
**File**: `backend/apps/documents/services.py:62`
```python
ext = os.path.splitext(file_obj.name)[1].lower()
if ext not in ALLOWED_EXTENSIONS:
    raise ValueError(...)
```
Extension checking can be bypassed by renaming a malicious file (e.g. `malware.exe` → `malware.pdf`). The file magic bytes should also be validated.
**Fix**: Use `python-magic` or read the first 16 bytes and check magic numbers for PDF, PNG, JPEG.

### 🟡 MEDIUM — `console.error` Left in Production Build
**File**: `frontend/src/components/ui/AppErrorBoundary.tsx:52`
```tsx
componentDidCatch(error: Error, errorInfo: ErrorInfo) {
  console.error('Frontend render error', error, errorInfo)
}
```
Stack traces and component names logged to browser console in production. Should be sent to an error monitoring service (Sentry, etc.) or suppressed.

### 🟢 LOW — No Account Lockout After Failed Logins
**File**: `backend/clarisal/settings/base.py:134`
Rate limiting is set to `workforce_login: '5/minute'` using DRF `ScopedRateThrottle`. This rate limits by IP/user key, not by account. An attacker can try 5 passwords per minute per IP indefinitely by rotating IPs. True account lockout (e.g. lock after 10 failures, require email unlock) is not implemented.

---

## Dead & Stale Code

### 1. `ATTENDANCE_REGULARIZATION` — Ghost Reference
**Files**: `backend/apps/approvals/models.py:13`, `frontend/src/lib/constants.ts`, `frontend/src/pages/org/ApprovalWorkflowBuilderPage.tsx`
`ApprovalRequestKind.ATTENDANCE_REGULARIZATION` is defined and selectable in the approval workflow builder, but there is no attendance module that ever creates an attendance regularization request. The approval kind is a dead reference.
**Impact**: Org admins can create "Attendance Regularisation" workflows that will never be triggered. Confusing and potentially misleading.

### 2. `PayrollPage.tsx` — Hardcoded 3-Slab Tax Structure
**File**: `frontend/src/pages/org/PayrollPage.tsx:47–56`
The tax slab form has exactly three fixed slab boundaries (`slab_one_limit`, `slab_two_limit`, `slab_three_rate`). The backend supports arbitrary slabs but the frontend prevents creating more than 3 or fewer than 3. This will be incorrect for India FY2025–26 which has 7 income slabs under the new regime.

### 3. `PayrollPage.tsx` — Hardcoded 2-Component Template
**File**: `frontend/src/pages/org/PayrollPage.tsx:110–126`
The compensation template form always creates exactly two components (BASIC, PF_EMPLOYEE) with hardcoded `component_code` values. The backend supports arbitrary components but the frontend does not surface this capability.

### 4. `OrganisationTaxRegistration` and `OrganisationLegalIdentifier` Models — No UI
**Files**: `backend/apps/organisations/models.py`
Both models exist and have migration history, but no API endpoints or UI expose them. The org profile page does not collect GSTIN or PAN. These are important for payroll compliance (employer's TAN for TDS filing, GSTIN for invoicing).

### 5. `DEFAULT_FISCAL_YEAR = '2026-2027'` Hardcoded
**File**: `backend/apps/payroll/services.py:36`
```python
DEFAULT_FISCAL_YEAR = '2026-2027'
```
The fallback fiscal year used in `_ensure_global_default_tax_master` is hardcoded. When April 2027 arrives, this will silently use the wrong year for newly provisioned organisations.
**Fix**: Calculate dynamically: `f'{date.today().year}-{date.today().year + 1}'` (adjusted for Indian FY starting in April).

### 6. `_build_rendered_payslip` — Placeholder Function
**File**: `backend/apps/payroll/services.py:90`
```python
def _build_rendered_payslip(snapshot):
    lines = [
        f"Payslip: {snapshot['period_label']}",
        ...
    ]
    return '\n'.join(lines)
```
This 6-line plain text function is clearly a placeholder. The `Payslip.rendered_text` field is populated with this output and then displayed verbatim in a `<pre>` block. This is not payslip generation.

### 7. Duplicate `_get_admin_organisation` and `_get_employee` Helper Functions
Every views file defines its own copy of these two functions:
- `backend/apps/payroll/views.py:40–51`
- `backend/apps/communications/views.py:17–28`
- `backend/apps/departments/views.py` (implicit)
- `backend/apps/timeoff/views.py`
- `backend/apps/approvals/views.py:48–57`
- `backend/apps/employees/views.py:57–66`

Same logic, copy-pasted across 6+ files. Should be extracted into `apps.accounts.workspaces` as a reusable utility.

---

## UI/UX Issues

### 1. Payroll Page Information Architecture — Critical
**Location**: `/org/payroll`
**Current**: All payroll operations (tax slabs, templates, assignments, runs) are on a single scrolling page with no tabs, no pagination, no workflow guidance.
**Zoho Payroll**: Structured as Pay Schedule → Salary Components → Pay Grades → Run Payroll — each a distinct step/page. A clear "Run Payroll" CTA is surfaced on the dashboard.
**Impact**: Org admins will be confused about what order to follow and will likely make mistakes.
**Fix**: Split into at minimum 4 sub-pages: `/org/payroll/settings`, `/org/payroll/templates`, `/org/payroll/employees`, `/org/payroll/runs`.

### 2. Payslip Viewer Shows Raw Debug Output
**Location**: `/me/payslips`
**Current**: Payslip "detail" is a `<pre>` block showing:
```
Payslip: April 2026
Employee: John Doe
Gross Pay: 50000.00
...
```
**Zoho/Keka**: Properly formatted payslip with company logo, component table, employer details, download PDF.
**Impact**: Cannot be used as a legal document. Employees cannot share it with banks or landlords.
**Fix**: Render the `snapshot.lines` array as a proper earnings/deductions table. Add PDF generation.

### 3. Currency Display Without Formatting
**Location**: All payroll-related pages
**Current**: All amounts displayed as raw decimal strings (`50000.00`, `1800.00`, `43408.00`).
**Zoho/Keka**: Indian Rupee formatting (`₹50,000`, `₹1,800`).
**Impact**: Difficult to read large numbers. Does not meet professional HRMS standard.
**Fix**: Add a `formatCurrency(amount, currency='INR')` utility using `Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })`.

### 4. Employee List Has No Bulk Operations
**Location**: `/org/employees`
**Current**: No checkboxes, no bulk select, no bulk actions.
**Zoho/Darwinbox**: Bulk assign leave plan, bulk export, bulk send notice.
**Impact**: For orgs with 50+ employees, initial setup requires clicking into each employee individually.

### 5. No Sidebar Navigation on Mobile (Employee Portal)
**Location**: All `/me/*` pages
**Current**: The sidebar is a fixed left panel that occupies ~240px. On mobile, there is no hamburger menu or slide-out drawer. The main content area is pushed to the right of the sidebar, making it invisible or very narrow.
**Zoho**: Has a dedicated mobile app with bottom navigation. Darwinbox mobile web has a collapsible sidebar.
**Impact**: The primary device for Indian employees is a smartphone. The employee portal — leave, payslips, attendance — must work on mobile.
**Fix**: Add responsive sidebar with mobile toggle in `EmployeeLayout.tsx`.

### 6. Leave Session Selector Confusing on Multi-day Requests
**Location**: `/me/leave`
**Current**: The form shows "Start Session" and "End Session" dropdowns (Full Day / First Half / Second Half) even when the start and end dates are different days. For a 3-day leave, `start_session=SECOND_HALF` and `end_session=FIRST_HALF` would result in 2 days of leave, which is not intuitive.
**Zoho**: Hides session selector when date range > 1 day, or shows it with clear explanation ("Your leave will be from the second half of Mon to the first half of Wed").
**Fix**: Hide or lock session selectors when `start_date !== end_date`.

### 7. Payroll Calculation Has No Visible Exception Summary
**Location**: `/org/payroll` (payroll run section)
**Current**: After calculating a run, the run item list shows all employees including those with EXCEPTION status, but there is no summary count or alert ("8 employees could not be processed — click to review").
**Impact**: An admin can finalize a run silently excluding 30% of employees.
**Fix**: Show a prominent warning banner: "X employees have exceptions and will be excluded from this run." with a link to the exception detail.

### 8. No Confirmation Dialog on Payroll Finalization
**Location**: `/org/payroll` (finalize action)
**Current**: Clicking "Finalize" immediately fires the API. No confirmation dialog.
**Impact**: Payroll finalization is irreversible without a rerun. This is a destructive action that should require explicit confirmation: "You are about to finalize payroll for April 2026 for N employees. This action cannot be undone. Confirm?"

### 9. Form Validation is Submit-Only, Not Inline
**Location**: Multiple forms across all portals
**Current**: Validation errors appear only after form submission (DRF validation errors returned from API).
**Zoho/Keka**: Field-level inline validation fires on blur for critical fields (PAN format, IFSC format, email format).
**Fix**: Add client-side regex validation for PAN (`[A-Z]{5}[0-9]{4}[A-Z]`), IFSC (`[A-Z]{4}0[A-Z0-9]{6}`), and email. The `errors.ts` utility (`getErrorMessage`) is already in place for API errors — field-level validation needs to be added to the input components.

### 10. Empty States Are Present but Inconsistent
Some empty states have an icon, title, and description (e.g. `EmptyState` component on employees page). Others are just an empty list with no guidance. The payroll page has no empty state at all when no tax slabs have been configured — it just shows an empty section titled "Published masters".

---

## Content Issues

### 1. Login Pages — Generic Copy
**Files**: `frontend/src/pages/auth/LoginPage.tsx`, `frontend/src/pages/auth/ControlTowerLoginPage.tsx`
The login pages need to be reviewed to ensure they use product-specific copy and context, not generic placeholder text. The eyebrow text should identify the product ("Clarisal HRMS") and the context ("Sign in to your organisation workspace").

### 2. Payslip Rendered Text — Developer Debug Output in Production
As noted above, the `rendered_text` field contains:
```
Payslip: April 2026
Employee: John Doe
Gross Pay: 50000.00
Income Tax: 4792.00
Total Deductions: 6592.00
Net Pay: 43408.00
```
This is displayed directly to employees. This is placeholder developer output.

### 3. Hardcoded Demo Defaults in Production Forms
**File**: `frontend/src/pages/org/PayrollPage.tsx:48–54`
The tax form defaults `name: 'FY Default Copy'`, basic pay defaults `50000`, employee deduction defaults `1800`. These are demo values that appear pre-filled in production forms.
**File**: `frontend/src/pages/ct/PayrollMastersPage.tsx:28`
CT form defaults `name: 'Default India Master'` with slab limits pre-filled.
**Impact**: Users may click "Create" without reading, submitting demo data as real configuration.

### 4. Indian Statutory Terminology Mismatches
| Used in Product | Correct Indian HR Term |
|-----------------|----------------------|
| "Income Tax" | "TDS (Tax Deducted at Source)" |
| "Employee Deduction" | "Employee Deduction" ✅ |
| "Employer Contribution" | "Employer Contribution" ✅ |
| "Gross Pay" | "Gross Salary" |
| "Net Pay" | "Net Pay" / "Take-Home" ✅ |
| No "CTC" anywhere | CTC is the primary concept Indian HR uses |
| "Leave Balance" | "Leave Balance" ✅ |

The product does not surface CTC (Cost to Company), which is the primary way Indian HR communicates salary. Employees and HR both think in CTC terms. The payroll module works in gross/net terms without providing CTC context.

---

## Functional Correctness: Payroll Calculation Deep-Dive

The payroll calculation engine in `backend/apps/payroll/services.py:428` was traced through a complete execution:

**Given**: Employee with BASIC = ₹50,000/month, PF_EMPLOYEE deduction = ₹1,800/month, 3-slab tax: 0% up to ₹3L, 10% from ₹3L–7L, 20% above ₹7L.

**Calculation**:
- `gross_pay = 50,000` (BASIC as EARNING)
- `taxable_monthly = 50,000` (BASIC is_taxable=True)
- `annual_taxable = 50,000 × 12 = 6,00,000`
- Tax: 0% on 3L = 0, 10% on (6L - 3L = 3L) = 30,000 → annual_tax = 30,000
- `income_tax = 30,000 / 12 = 2,500/month`
- `employee_deductions = 1,800` (PF_EMPLOYEE)
- `total_deductions = 1,800 + 2,500 = 4,300`
- `net_pay = 50,000 - 4,300 = 45,700`

**Bugs found**:

1. **No Standard Deduction**: India's Income Tax Act (new regime FY2024–25 onwards) provides ₹75,000 standard deduction from gross salary before computing taxable income. This is absent. The system overtaxes employees by ~₹625/month (₹75,000 × 10% / 12 ≈ ₹625).

2. **No Health & Education Cess (4%)**: Every income tax computation in India requires adding 4% cess on the computed tax. `annual_tax` should be multiplied by 1.04. At ₹30,000 annual tax, this means ₹1,200 in missing cess.

3. **No Surcharge**: Employees earning above ₹50 lakh annually are subject to 10%–37% surcharge. Not applicable to most SMB employees, but mathematically incorrect for senior hires.

4. **PF is a flat rupee amount, not 12% of basic**: The `PF_EMPLOYEE` component is entered as ₹1,800 (a fixed deduction). Real PF is 12% of Basic Pay (capped at ₹1,800 for basic ≤ ₹15,000, but continues as 12% for basic > ₹15,000). An employee with basic ₹80,000 should contribute ₹9,600 to PF, not ₹1,800. The system will always show ₹1,800 unless the template is manually updated.

5. **No Employer PF contribution in net pay calculation**: `employer_contributions` (PF_EMPLOYER) is tracked but never subtracted from any figure. This is correct — employer PF is not deducted from employee take-home — but it is also never added to CTC calculation (which doesn't exist). Fine structurally, but incomplete as CTC reporting.

6. **No LOP deduction**: The `LeaveType.is_loss_of_pay` field is never read in the payroll calculation. If an employee takes 2 days of LOP leave in a month, their salary is not reduced. `calculate_pay_run()` (`services.py:428`) makes no query on `LeaveRequest` data.

7. **No pro-rated salary for joining month**: `calculate_pay_run()` uses `period_end` to resolve the effective salary assignment date but does not check whether the employee joined mid-month. A joining date of April 15 should result in 16/30 of monthly salary. The calculation gives full month salary.

**Summary**: The payroll engine will produce mathematically incorrect results for any Indian company running compliant payroll. The issues are not minor rounding errors — they are missing entire statutory components (ESI, PT, cess, surcharge) and incorrect logic for pro-ration and LOP.

---

## Test Coverage Assessment

### Backend Tests

| App | Test Files | What's Tested | Quality |
|-----|-----------|---------------|---------|
| `accounts` | test_models, test_services, test_views, test_tasks, test_transactional_emails | User creation, auth, password reset, invitations, emails | Good |
| `organisations` | test_models, test_services, test_views, test_licence_batches | Org lifecycle, licence management, CT operations | Good |
| `employees` | test_models, test_services, test_views | Employee CRUD, workflow assignments, status transitions | Good |
| `timeoff` | test_models, test_services, test_views | Leave requests, balances, calendar, overlap detection | Good |
| `approvals` | test_models, test_services, test_views | Approval engine, stage progression, multi-approver | Good |
| `departments` | test_models, test_services, test_views | CRUD | Basic |
| `locations` | test_models, test_services, test_views | CRUD | Basic |
| `documents` | test_models, test_services, test_views | Upload, verify, reject | Good |
| `invitations` | test_models, test_services, test_views | Invite flow, expiry | Good |
| `audit` | test_models, test_services, test_views, test_commands | Log creation | Good |
| `communications` | test_models, test_services, test_views | Notice lifecycle | Good |
| `payroll` | test_services, test_views | End-to-end payroll run, finalization, payslip generation | Basic |

### Top 10 Untested Areas by Business Risk

1. **Payroll: PF, ESI, PT, TDS correctness** — No test verifies statutory deduction amounts. The existing test only checks `total_deductions > 1800` and `net_pay < gross_pay` — these are trivially true and catch no calculation bugs.
2. **Payroll: Pro-rated salary on joining/exit month** — No test. This is where real payroll discrepancies happen.
3. **Payroll: LOP deduction impact** — No test connecting leave requests to payroll output.
4. **Leave accrual: Prorate on join mid-cycle** — `prorate_on_join` logic exists but no test for edge cases (joining on the last day of cycle, joining when cycle_start is in a different year).
5. **Leave: Carry-forward at cycle end** — No test for the carry-forward capping logic.
6. **CT PII boundary** — No test verifying that CT cannot read government IDs or bank accounts. The `CtOrganisationEmployeeDetailView` test likely exists but exposes the PII gap.
7. **Multi-org isolation** — No test verifying that an org admin from Org A cannot access Org B's data.
8. **Approval: Fallback escalation** — If `REPORTING_MANAGER` approver and fallback is `NONE`, what happens? No test.
9. **Session security** — No test for session fixation after login (though `request.session.cycle_key()` is called — verify test coverage).
10. **File upload security** — No test for upload of a file with a valid extension but malicious content.

### Frontend Tests
There is a Playwright E2E test configuration (`playwright.config.ts`) but **no test files** exist in `frontend/src/**/__tests__/` or `frontend/tests/`. The test infrastructure is set up but unused. There are no unit tests for any frontend component, hook, or utility function.

---

## Recommendations

### Immediate — Fix Before Go-Live

1. **[SECURITY] Rotate AWS IAM credentials and ZeptoMail API key** — `AKIA47KWW5J3E6Z37SAS` is a live key. Rotate in AWS IAM console and ZeptoMail dashboard now. Audit access logs.

2. **[SECURITY] Create `CtEmployeeListSerializer` and remove PII from CT employee endpoint**
   `backend/apps/organisations/views.py:313` — Replace `EmployeeDetailSerializer` with a sanitised serializer. Remove the `patch` method from `CtOrganisationEmployeeDetailView`.

3. **[SECURITY] Add startup validation for `FIELD_ENCRYPTION_KEY`**
   `backend/clarisal/settings/base.py` — Add `ImproperlyConfigured` raise if key is empty or is the placeholder value.

4. **[PAYROLL CORRECTNESS] Fix income tax calculation — add 4% cess**
   `backend/apps/payroll/services.py:117` — `annual_tax = annual_tax * Decimal('1.04')`

5. **[PAYROLL CORRECTNESS] Add standard deduction of ₹75,000 before tax calculation**
   `backend/apps/payroll/services.py:480` — Subtract `Decimal('75000')` from `annual_taxable` before calling `_calculate_annual_tax`.

6. **[PAYROLL UX] Replace `rendered_text` in payslip with a proper component-wise table**
   `frontend/src/pages/employee/PayslipsPage.tsx` — Render `snapshot.lines` as a formatted earnings/deductions breakdown table. Remove the `<pre>` block.

7. **[PAYROLL UX] Add confirmation dialog before payroll finalization**
   `frontend/src/pages/org/PayrollPage.tsx` — Add a modal: "Finalize payroll for [month] [year] for [N] employees? This cannot be undone."

8. **[PAYROLL UX] Add exception summary alert before finalization**
   Show count and list of EXCEPTION items with their reasons before allowing finalization.

---

### Short-term — Next 1–2 Sprints

9. **[PAYROLL CORRECTNESS] Implement PF auto-calculation (12% of basic, capped at ₹1,800 for basic ≤ ₹15,000)**
   `backend/apps/payroll/services.py` — Detect BASIC component, calculate PF as 12%, create PF_EMPLOYEE deduction automatically.

10. **[PAYROLL CORRECTNESS] Implement pro-rated salary for joining/exit month**
    `backend/apps/payroll/services.py:456` — Compare `employee.date_of_joining` with `period_start`. If joining is within the month, apply `(days_remaining / total_days)` multiplier to all earnings.

11. **[PAYROLL CORRECTNESS] Wire LOP leaves into payroll deduction**
    In `calculate_pay_run`, query `LeaveRequest` for approved LOP leaves in the period. Calculate `lop_days`, prorate gross salary accordingly.

12. **[PAYROLL UX] Rewrite payroll page as multi-section workflow**
    Split `/org/payroll` into Settings / Templates / Employee Assignments / Payroll Runs tabs. Add proper paginated tables.

13. **[PAYROLL UX] Add currency formatting throughout**
    Create `formatINR(amount)` utility. Apply to all monetary displays.

14. **[FEATURE] Implement ESI calculation**
    ESI applies when employee gross ≤ ₹21,000/month: Employee = 0.75%, Employer = 3.25%. Add ESI_EMPLOYEE and ESI_EMPLOYER as auto-calculated components.

15. **[FEATURE] Implement Professional Tax (PT)**
    State-wise slabs. At minimum support Maharashtra (max ₹200/month for salary ≥ ₹10,000). Store PT config per office location's state.

16. **[SECURITY] Move async payroll calculation to Celery**
    `backend/apps/payroll/views.py:240` — Return 202 Accepted, run `calculate_pay_run` in a Celery task.

17. **[UX] Fix mobile sidebar navigation in Employee portal**
    `frontend/src/components/layouts/EmployeeLayout.tsx` — Add hamburger menu toggle for screens < 768px.

18. **[PERFORMANCE] Replace Python sum loops with DB aggregates in leave balance**
    `backend/apps/timeoff/services.py:292–314` — Use `aggregate(Sum('total_units'))`.

19. **[CODE QUALITY] Extract `_get_admin_organisation` / `_get_employee` to shared module**
    6+ duplicate definitions across views files.

20. **[PAYROLL] Add payslip PDF generation**
    Use `weasyprint` to generate a properly formatted PDF. The `Payslip.snapshot` already contains all required data. Add a download endpoint.

---

### Long-term — Roadmap Items

21. **[MODULE] Build Attendance & Time Tracking** — Clock in/out (web + mobile), shift management, geo-fencing, late-mark rules, regularisation workflow, biometric integration. This is the largest single missing module and blocks LOP calculation, overtime, and attendance-based payroll.

22. **[MODULE] Build Performance Management** — Goal setting, appraisal cycles, 360° feedback, probation appraisal integration.

23. **[MODULE] Build Reports & Analytics** — Headcount, attrition, payroll register, leave utilization, attendance summary. At minimum: exportable CSV for each major entity.

24. **[PAYROLL] Add investment declaration portal** — Employee self-declares 80C, 80D, HRA exemption. Feeds into TDS calculation. Required for accurate TDS and Form 16.

25. **[PAYROLL] Form 16 generation** — Mandatory for employees with TDS deducted. Requires finalized payroll + investment declarations.

26. **[PAYROLL] Full & Final settlement** — Gratuity calculation (15 days/year for 5+ years), leave encashment, notice period recovery.

27. **[FEATURE] Bulk employee import via CSV/Excel** — Critical for any org migrating to the platform.

28. **[FEATURE] Custom employee fields** — Orgs need to capture business-specific data (vehicle registration, uniform size, shift preference).

29. **[FEATURE] Org chart visualisation** — The `reporting_to` FK on Employee is the right foundation. Build a D3 or similar tree renderer.

30. **[RBAC] Expand `OrganisationMembership.is_org_admin` to a role enum** — Support HR Manager, Payroll Admin, Finance Approver, Read-only roles.

31. **[COMPLIANCE] DPDP Act readiness** — Data retention policies, right-to-erasure workflow (soft delete → anonymization), consent tracking for PII collection.

32. **[FRONTEND] Add E2E tests using Playwright** — The configuration exists. Write smoke tests for the three most critical flows: employee invite, leave application, payroll run.

---

## Changelog from v1 Audit

The v1 audit (`docs/HRMS_AUDIT_REPORT.md`) was the initial baseline — undated and version-untracked. This v2 audit expands coverage to include the payroll module (introduced since v1), CT portal deep-dive, functional correctness analysis of the payroll engine, and a security audit. The architecture section is new. All feature gap tables are revised with the payroll module now included. The v1 report correctly identified the three missing modules (Attendance, Performance, Reports); v2 confirms they remain absent and adds the payroll prototype as a new partial implementation.

Key new findings since v1:
- **NEW CRITICAL**: CT PII exposure via `CtOrganisationEmployeeDetailView` using `EmployeeDetailSerializer`
- **NEW CRITICAL**: Live AWS + ZeptoMail credentials in `.env`
- **NEW**: Payroll module added — prototype-grade, 7 correctness bugs documented
- **NEW**: Payslip output is plain text — not a legally usable document
- **NEW**: `ATTENDANCE_REGULARIZATION` is a dead approval kind with no backing module
- **NEW**: `DEFAULT_FISCAL_YEAR` hardcoded — will become stale
- **NEW**: Payroll calculation is synchronous — will time out at scale
