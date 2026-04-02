# HRMS Audit Report
**Version**: v2  
**Date**: 2026-04-02 17:11 IST  
**Previous Audit**: `docs/HRMS_AUDIT_REPORT.md`

## Executive Summary
Clarisal has solid SaaS foundations for a multi-tenant HRMS, but it is not ready for production go-live as a full HRMS with attendance and payroll. The strongest areas today are employee onboarding data capture, documents, leave policy modeling, approvals, audit logging, and org setup. The largest product gaps are the absence of a real attendance engine, shallow India-specific payroll correctness, and a Control Tower access model that currently violates the intended privacy boundary.

The codebase is materially ahead of a prototype in structure, but not yet at the level of Zoho People/Zoho Payroll, Darwinbox, or Keka for real-world HR operations. Several surfaces look complete in the UI while the underlying business logic is thin or missing, especially for attendance and payroll. That creates a confidence risk: an HR admin could reasonably assume the product is operationally complete when it is not.

### Top 5 blockers for production go-live
- **No first-class attendance subsystem**. There are no punch, shift, late mark, half-day, absent, overtime, or attendance regularization models or APIs; only on-duty and workflow placeholders exist. Evidence: `backend/apps` has no attendance app, routes in `frontend/src/routes/index.tsx` have no attendance pages, and `backend/apps/timeoff/models.py` only covers leave, holidays, and on-duty.
- **Control Tower can access and modify employee data it should not**. `backend/apps/organisations/views.py` exposes `CtOrganisationEmployeeDetailView.get` and `.patch`, returning `EmployeeDetailSerializer`, which includes profile, government IDs, bank accounts, family members, and emergency contacts from `backend/apps/employees/serializers.py`.
- **Payroll is too shallow for India production use**. The engine in `backend/apps/payroll/services.py` supports tax slabs, templates, assignments, runs, and payslips, but does not implement proper PF/ESI/PT/TDS workflows, Form 16, investment declarations, arrears, or full & final settlement.
- **CT support/debug visibility is incomplete**. CT can manage global payroll masters and org configuration, but there is no CT-facing org payroll run explorer, org payroll exception view, or approval-inbox/history surface for support operations. Evidence: only `backend/apps/payroll/ct_urls.py` exposes `payroll/tax-slab-sets/`.
- **Leave logic is modeled well but not operationalized fully**. `backend/apps/timeoff/services.py` still recomputes credited balances during reads instead of using a scheduled accrual engine, and there is no comp-off or leave encashment.

### Top 5 quick wins
- Lock down CT employee APIs to a sanitised serializer and remove CT mutation access on employees.
- Hide or relabel attendance regularization concepts until a real attendance subsystem exists.
- Put a product warning/beta boundary around payroll and block language that implies statutory completeness.
- Add explicit confirmation and exception review steps to payroll finalization in `frontend/src/pages/org/PayrollPage.tsx`.
- Replace generic payroll and leave error toasts with domain-specific, actionable messages.

## Current Implementation Map

### Tech Stack
- **Backend**: Django 4.2, Django REST Framework, PostgreSQL, Celery, Redis, S3 via boto3, SMTP/ZeptoMail. Evidence: `backend/requirements.txt`, `backend/clarisal/settings/base.py`.
- **Auth**: Session-based auth with CSRF, not JWT. Evidence: `backend/apps/accounts/views.py`, `frontend/src/lib/api.ts`.
- **Frontend**: React 19, React Router, TanStack Query, Axios, Tailwind, Radix UI primitives, Vite. Evidence: `frontend/package.json`.

### Modules Present Today
- `accounts`: login, logout, workspace switching, password reset, invite acceptance.
- `organisations`: CT organisation lifecycle, licences, org admins, org setup, org profile.
- `locations`, `departments`: master data management.
- `employees`: employee invite, lifecycle, profile, education, emergency contacts, family, government IDs, bank accounts, onboarding, dashboard.
- `documents`: onboarding document types, requests, uploads, verification, download.
- `approvals`: workflow config, rules, stages, approvals inbox/actions.
- `timeoff`: leave cycles, leave plans, leave requests, holiday calendars, on-duty policies and requests, employee calendar.
- `communications`: notices and employee events feed.
- `audit`: searchable/exportable audit trail.
- `payroll`: tax slab sets, salary components/templates, compensation assignments, payroll runs, payslips.

### Major Modules Missing Entirely
- Attendance engine
- Performance management
- Recruitment / ATS
- Org chart
- Report builder / advanced HR analytics
- Tax declarations / proofs workflow

### Portal Map

#### Control Tower (CT)
**UI routes wired in `frontend/src/routes/index.tsx`:**
- `/ct/login`
- `/ct/reset-password`
- `/ct/reset-password/:token`
- `/ct/dashboard`
- `/ct/payroll`
- `/ct/organisations`
- `/ct/organisations/new`
- `/ct/organisations/:id`
- `/ct/organisations/:organisationId/licences/new`
- `/ct/organisations/:organisationId/profile`
- `/ct/organisations/:organisationId/locations`
- `/ct/organisations/:organisationId/departments`
- `/ct/organisations/:organisationId/leave-cycles`
- `/ct/organisations/:organisationId/leave-plans`
- `/ct/organisations/:organisationId/on-duty-policies`
- `/ct/organisations/:organisationId/approval-workflows`
- `/ct/organisations/:organisationId/notices`
- `/ct/organisations/:organisationId/audit`

**What CT can actually do today**
- Manage organisations, licences, lifecycle, org admins, locations, departments, leave cycles/plans, on-duty policies, approval workflows, notices, audit logs, and global payroll tax masters. Evidence: `backend/apps/organisations/urls.py`, `backend/apps/payroll/ct_urls.py`.
- View organisation employee list and open employee details from CT. Evidence: `frontend/src/pages/ct/OrganisationDetailPage.tsx`, `backend/apps/organisations/views.py`.

**What CT should not do but currently can**
- View employee detail payloads containing profile address/phone, masked government IDs, masked bank accounts, family members, emergency contacts. Evidence: `backend/apps/organisations/views.py`, `backend/apps/employees/serializers.py`.
- Patch employee records through `CtOrganisationEmployeeDetailView.patch`. This directly conflicts with the stated CT policy. Evidence: `backend/apps/organisations/views.py`.

**What CT cannot do but needs for support**
- No CT org payroll run history, payroll exception analysis, or org payroll summary.
- No CT approval inbox/history for debugging stuck workflows.
- No CT support-only view that is sanitised but operationally useful.

#### Org Admin
**UI routes wired in `frontend/src/routes/index.tsx`:**
- `/org/setup`
- `/org/dashboard`
- `/org/profile`
- `/org/payroll`
- `/org/locations`
- `/org/departments`
- `/org/employees`
- `/org/employees/:id`
- `/org/holidays`
- `/org/leave-cycles`
- `/org/leave-plans`
- `/org/on-duty-policies`
- `/org/approval-workflows`
- `/org/notices`
- `/org/audit`

**What Org Admin can do today**
- Complete guided setup, manage org profile and addresses, configure locations/departments, invite and manage employees, collect and verify onboarding documents, configure leave/holiday/on-duty policies, configure approval workflows, publish notices, inspect audit logs, and run the current payroll flows. Evidence: `backend/apps/organisations/org_urls.py`, `backend/apps/employees/urls.py`, `backend/apps/documents/urls.py`, `backend/apps/timeoff/org_urls.py`, `backend/apps/payroll/org_urls.py`.

**What is missing**
- No attendance setup, shifts, punch sources, geo/IP rules, biometrics, overtime, or attendance corrections.
- No reports center, custom report builder, or payroll register export.
- No performance or recruitment.
- No role beyond flat Org Admin.

#### Employee
**UI routes wired in `frontend/src/routes/index.tsx`:**
- `/auth/login`
- `/auth/reset-password`
- `/auth/reset-password/:token`
- `/auth/invite/:token`
- `/me/onboarding`
- `/me/dashboard`
- `/me/profile`
- `/me/education`
- `/me/documents`
- `/me/leave`
- `/me/od`
- `/me/payslips`
- `/me/approvals`

**What Employee can do today**
- Complete onboarding, manage personal profile basics, education, government IDs, bank accounts, upload documents, request leave, request on-duty, act on approvals assigned to them, and view payslips. Evidence: `backend/apps/employees/self_urls.py`, `backend/apps/documents/self_urls.py`, `backend/apps/timeoff/self_urls.py`, `backend/apps/approvals/self_urls.py`, `backend/apps/payroll/self_urls.py`.

**What is missing**
- No attendance page, attendance logs, regularization UI, time tracking, reimbursement, tax declaration, performance, org chart, or help desk.

### Backend API Inventory
**Auth**
- `/api/auth/csrf/`
- `/api/auth/login/`
- `/api/auth/control-tower/login/`
- `/api/auth/logout/`
- `/api/auth/me/`
- `/api/auth/workspace/`
- password reset and invite validate/accept endpoints

**CT**
- `/api/ct/dashboard/`
- `/api/ct/organisations/*`
- `/api/ct/audit/`
- `/api/ct/payroll/tax-slab-sets/`

**Org Admin**
- `/api/org/dashboard/`
- `/api/org/setup/`
- `/api/org/profile/*`
- `/api/org/locations/*`
- `/api/org/departments/*`
- `/api/org/employees/*`
- `/api/org/document-types/`
- `/api/org/employees/<employee_id>/document-requests/`
- `/api/org/employees/<employee_id>/documents/*`
- `/api/org/approvals/workflows/*`
- `/api/org/approvals/inbox/`
- `/api/org/approvals/actions/*`
- `/api/org/holiday-calendars/*`
- `/api/org/leave-cycles/*`
- `/api/org/leave-plans/*`
- `/api/org/leave-requests/`
- `/api/org/on-duty-policies/*`
- `/api/org/on-duty-requests/`
- `/api/org/notices/*`
- `/api/org/audit/`
- `/api/org/payroll/*`

**Employee**
- `/api/me/onboarding/`
- `/api/me/dashboard/`
- `/api/me/profile/`
- `/api/me/family/*`
- `/api/me/emergency-contacts/*`
- `/api/me/education/*`
- `/api/me/government-ids/`
- `/api/me/bank-accounts/*`
- `/api/me/document-requests/`
- `/api/me/document-requests/<request_id>/upload/`
- `/api/me/documents/`
- `/api/me/documents/<doc_id>/download/`
- `/api/me/leave/overview/`
- `/api/me/leave/requests/`
- `/api/me/leave/requests/<id>/withdraw/`
- `/api/me/on-duty/policy/`
- `/api/me/on-duty/requests/`
- `/api/me/on-duty/requests/<id>/withdraw/`
- `/api/me/calendar/`
- `/api/me/approvals/inbox/`
- `/api/me/approvals/actions/*`
- `/api/me/notices/`
- `/api/me/events/`
- `/api/me/payroll/payslips/`
- `/api/me/payroll/payslips/<id>/`

### Backend Features With No Meaningful UI Surface
- Org approval inbox/actions exist in backend and hooks, but there is no dedicated org task-center page; they are folded into dashboard/workflow screens. Evidence: `backend/apps/approvals/views.py`, `frontend/src/hooks/useOrgAdmin.ts`, `frontend/src/pages/org/ApprovalWorkflowsPage.tsx`.
- Employee payslip detail endpoint exists, but the UI only lists slips already loaded from the list query and shows stored text, not a richer document view. Evidence: `backend/apps/payroll/self_urls.py`, `frontend/src/pages/employee/PayslipsPage.tsx`.

### UI Surfaces That Imply More Capability Than Actually Exists
- `attendance_regularization` is present in approval workflow types and employee assignment fields, but there is no attendance domain to produce or resolve those requests. Evidence: `backend/apps/approvals/models.py`, `backend/apps/employees/models.py`.
- Payroll UI suggests “control room” completeness, but the backing engine is still thin and synchronous. Evidence: `frontend/src/pages/org/PayrollPage.tsx`, `backend/apps/payroll/services.py`.

### Data Model Reality
**Employee data captured**
- Core employment record, reporting line, department, location, onboarding status: `backend/apps/employees/models.py`
- Profile address/contact/demographics: `EmployeeProfile`
- Education, family, emergency contacts
- Government IDs (PAN, Aadhaar, etc.) and bank accounts with encryption/masking helpers

**Leave/time-off data captured**
- Holiday calendars, location assignments, leave cycles, leave plans, leave types, leave balances, leave requests, on-duty policies, on-duty requests: `backend/apps/timeoff/models.py`

**Approval data captured**
- Workflow, rules, stages, approvers, approval runs/actions, request kinds including payroll-related kinds: `backend/apps/approvals/models.py`

**Payroll data captured**
- Tax slab sets/slabs, payroll components, compensation templates, compensation assignments, payroll runs/items, payslips: `backend/apps/payroll/models.py`

**Data not captured**
- Punches, shifts, attendance days, overtime rules, geofencing rules, biometric device mappings
- Performance goals, KRAs/OKRs, reviews, calibration
- Recruitment pipeline, candidates, offers
- Tax declarations, proofs, Form 16 artifacts, F&F settlement

## Benchmark: Gaps vs Zoho People + Zoho Payroll

Benchmark references used:
- Zoho People attendance general settings: https://www.zoho.com/people/help/adminguide/orgworkinghours.html
- Zoho People performance: https://www.zoho.com/people/help/adminguide/performance-intro.html
- Zoho Payroll payslip templates: https://www.zoho.com/in/payroll/payslip-templates/
- Keka attendance regularization: https://help.keka.com/hc/en-us/articles/39946870714385-How-to-apply-WFH-OD-Partial-day-Regularization
- Darwinbox HRMS overview: https://explore.darwinbox.com/lp/hrms-software
- BambooHR performance: https://www.bamboohr.com/hr-software/performance-management/

### Core HR
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Employee directory and lifecycle basics | Partial | Zoho employee records and lifecycle modules | Significant Gap | Invite/join/end-employment exists in `backend/apps/employees/services.py`, but no offboarding workflow, assets, resignation workflow, or lifecycle automation. |
| Employee profile, family, emergency, education | Implemented | Zoho employee records | Minor Gap | Good data capture exists via `backend/apps/employees/models.py` and self-service views. |
| Custom fields | Missing | Zoho custom forms/fields | Significant Gap | No generic custom field framework in models or serializers. |
| Document management | Partial | Zoho employee documents | Significant Gap | Uploads/verification exist in `backend/apps/documents/*`, but no retention policies, categories per org, no doc expiration tracking, no CT-safe document visibility model. |
| Org chart | Missing | Zoho org chart | Significant Gap | Only single `reporting_to` field exists; no org chart UI or dotted-line support. |
| ESS portal | Partial | Zoho employee self-service | Significant Gap | Leave/documents/profile exist, but no attendance, tax, reimbursement, or broader self-service. |

### Attendance
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Clock in / clock out | Missing | Zoho attendance capture modes | Critical Gap | No models or routes for punches. |
| Shift management | Missing | Zoho shift settings and notifications | Critical Gap | No shift tables/models. |
| Late mark / half-day / absent engine | Missing | Zoho attendance policies | Critical Gap | No attendance computation domain. |
| Geo/IP attendance | Missing | Zoho People attendance capture modes and controls | Significant Gap | No geofence, IP, or mobile attendance controls. |
| Biometric/device integration | Missing | Zoho biometric/device integrations | Significant Gap | No device integration surfaces. |
| Attendance regularization workflow | Misleading Partial | Zoho and Keka attendance regularization | Critical Gap | Approval kinds exist, but there is no attendance request source or correction domain. |
| Holiday calendars by location | Implemented | Zoho holiday calendars | Minor Gap | Good location-aware holiday model exists in `backend/apps/timeoff/models.py`. |

### Leave
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Leave cycles and policy rules | Implemented | Zoho leave policies | Minor Gap | Strong data model in `backend/apps/timeoff/models.py`. |
| Accrual policy fields | Partial | Zoho leave accrual automation | Significant Gap | Policy fields exist, but `get_or_create_leave_balance` in `backend/apps/timeoff/services.py` still computes credits during reads. |
| Carry-forward controls | Partial | Zoho carry forward rules | Significant Gap | Model supports caps/modes, but no end-of-cycle job/operational automation is visible. |
| Leave balance visibility | Implemented | Zoho leave balances | Minor Gap | ESS leave page shows balances in `frontend/src/pages/employee/LeavePage.tsx`. |
| Multi-level approvals | Partial | Zoho approval workflows | Significant Gap | Backend workflows support multi-stage logic, but the builder and inbox UX are limited. |
| Comp-off | Missing | Zoho / Keka comp-off | Significant Gap | No comp-off models or overtime integration. |
| Leave encashment | Missing | Zoho Payroll leave encashment / F&F tie-ins | Significant Gap | No leave-to-payroll settlement path. |

### Payroll
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Salary structure builder | Partial | Zoho Payroll salary components/structure | Significant Gap | `frontend/src/pages/org/PayrollPage.tsx` only captures basic pay plus one deduction in UI; backend templates are more generic but still limited. |
| Payroll run lifecycle | Partial | Zoho Payroll run processing | Significant Gap | Draft/calculate/submit/finalize/rerun exist in `backend/apps/payroll/services.py`, but inline, synchronous, and thin. |
| Payslips | Partial | Zoho Payroll payslips | Significant Gap | Payslips exist but are text snapshot views in `frontend/src/pages/employee/PayslipsPage.tsx`, not downloadable branded documents. |
| PF / ESI / PT / TDS | Incorrect / Incomplete | Zoho Payroll India statutory payroll | Critical Gap | The service only applies generic tax slabs and template deductions; there is no correct India statutory engine. |
| Investment declarations / proofs | Missing | Zoho Payroll declarations/proofs | Critical Gap | No models, endpoints, or UI. |
| Form 16 | Missing | Zoho Payroll Form 16 | Critical Gap | Absent entirely. |
| Arrears / F&F / off-cycle settlement | Missing | Zoho Payroll F&F and payroll adjustments | Significant Gap | Only rerun exists; no statutory settlement or arrears domain. |

### Performance
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Goals / KRAs / OKRs | Missing | Zoho performance goals/KRAs | Significant Gap | No performance models or routes. |
| Review cycles / self appraisal / 360 | Missing | Zoho/BambooHR performance reviews | Significant Gap | Absent entirely. |
| Probation management | Missing | Darwinbox/Keka lifecycle controls | Minor Gap | No probation-specific logic beyond onboarding status. |

### Recruitment / Onboarding
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Employee invite and onboarding docs | Partial | Zoho onboarding tasks/docs | Minor Gap | Good invite + document collection exists. |
| Offer letters / ATS | Missing | Zoho Recruit / Darwinbox hiring | Significant Gap | No candidate or offer pipeline. |
| Onboarding task checklist | Partial | Zoho/Keka onboarding checklists | Significant Gap | Onboarding is data/document completion-driven, not task-driven. |
| Access provisioning workflows | Missing | Enterprise onboarding workflow tools | Significant Gap | No SaaS/app provisioning or IT checklist support. |

### Reports & Analytics
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Dashboard metrics | Partial | Zoho dashboard widgets | Minor Gap | CT/org/employee dashboards exist. |
| Audit explorer | Implemented | Audit trails in enterprise HRMS | Minor Gap | Stronger than many early products. Evidence: `frontend/src/pages/org/AuditPage.tsx`. |
| HR report builder | Missing | Zoho report builder | Significant Gap | No configurable report module. |
| Payroll register / tax reports | Missing | Zoho Payroll reports | Critical Gap | No payroll register or statutory reports. |
| Attendance reporting | Missing | Zoho attendance analytics | Critical Gap | Attendance domain absent. |

### Notifications & Workflows
| Feature | Current Status | Zoho Equivalent | Gap Type | Notes |
|---|---|---|---|---|
| Approval workflow engine | Partial | Zoho approvals | Minor Gap | Good backend workflow primitives exist. |
| Escalations / delegation / SLA | Missing | Zoho/Darwinbox workflow maturity | Significant Gap | No escalation timers or delegation. |
| In-app approvals | Partial | Zoho approvals inbox | Significant Gap | Employee inbox exists; org inbox lacks a dedicated task center and CT has none. |
| Email notifications | Partial | Zoho workflow alerts | Significant Gap | Invite/password-reset email exists, but there is no broad approval/operational notification system. |

## Portal-wise Audit

### Control Tower (CT)
**Exposed features**
- Global org management, licences, org admins, master data, leave/OD/workflow config, notices, audit explorer, and global payroll tax masters.

**Access control problems**
- **Issue**: CT can fetch full employee details using `CtOrganisationEmployeeDetailView.get`.
  - **File**: `backend/apps/organisations/views.py`
  - **Why it matters**: The stated product rule is that CT must not see employee PII beyond sanitised workforce visibility.
  - **Suggested fix**: Replace `EmployeeDetailSerializer` with a CT-safe serializer exposing only name, employee code, department, designation, location, and status; remove nested profile, IDs, bank, family, and emergency data.
- **Issue**: CT can patch employee records.
  - **File**: `backend/apps/organisations/views.py`
  - **Why it matters**: This directly breaks the intended role boundary and creates support-to-admin privilege creep.
  - **Suggested fix**: Remove `patch` support entirely from CT employee detail or gate it behind a narrowly scoped emergency-support capability with audit justification.

**Feature gaps**
- **Issue**: CT cannot inspect org payroll runs or payroll exceptions.
  - **Files**: `backend/apps/payroll/ct_urls.py`, `frontend/src/components/layouts/CTLayout.tsx`
  - **Why it matters**: CT is supposed to help debug org admin issues, but today it only has global tax masters, not org payroll operations.
  - **Suggested fix**: Add CT read-only org payroll summary/run history with employee data redaction.
- **Issue**: CT has no approval inbox/history for org support.
  - **Files**: `backend/apps/approvals/urls.py`, `frontend/src/routes/index.tsx`
  - **Why it matters**: Support staff cannot trace why approvals are blocked without impersonation or DB inspection.
  - **Suggested fix**: Add CT read-only approval-run explorer by organisation.

### Org Admin
**Exposed features**
- Best-covered persona today. Org Admin can manage most existing modules and has the only meaningful payroll operating surface.

**Role-fit issues**
- **Issue**: There is no dedicated payroll-admin role; all payroll power is given to Org Admin.
  - **Files**: `backend/apps/accounts/models.py`, `backend/apps/accounts/permissions.py`
  - **Why it matters**: Real HRMS deployments separate HR, finance/payroll, and admin duties.
  - **Suggested fix**: Introduce granular RBAC and payroll-specific permissions.

**Missing capabilities**
- **Issue**: No attendance administration at all.
  - **Files**: `backend/apps`, `frontend/src/routes/index.tsx`
  - **Why it matters**: For India-focused HRMS buyers, attendance is not optional.
  - **Suggested fix**: Build attendance as its own app with shifts, punches, regularization, and reporting.
- **Issue**: No custom reports/export center beyond audit CSV export.
  - **Files**: `frontend/src/pages/org/AuditPage.tsx`
  - **Why it matters**: HR teams need operational reporting for headcount, leave, attendance, and payroll.
  - **Suggested fix**: Add a reports module with saved filters and exports.

### Employee
**Exposed features**
- Onboarding, profile, education, documents, leave, on-duty, approvals, payslips.

**Feature gaps**
- **Issue**: No attendance experience.
  - **Files**: `frontend/src/components/layouts/EmployeeLayout.tsx`, `frontend/src/routes/index.tsx`
  - **Why it matters**: For most Indian employees, attendance, leave, and payslips are the three core ESS pillars.
  - **Suggested fix**: Add employee attendance page with today status, logs, regularization, and shift info.
- **Issue**: No tax declaration / proof / payroll history tools beyond payslip snapshots.
  - **Files**: `frontend/src/pages/employee/PayslipsPage.tsx`
  - **Why it matters**: Payroll ESS is incomplete without tax interaction.
  - **Suggested fix**: Add declarations, proofs, tax summary, and richer payslip documents.

**Access-fit observations**
- Employee API scoping is generally sound; document, leave, payslip, and bank-account endpoints scope to the active employee. Evidence: `backend/apps/documents/views.py`, `backend/apps/employees/views.py`, `backend/apps/payroll/views.py`.

## Architecture Issues

### 1. Shared serializer reuse breaks role boundaries
- **File**: `backend/apps/organisations/views.py`, `backend/apps/employees/serializers.py`
- **Problem**: CT and Org Admin both use `EmployeeDetailSerializer`, despite different privacy requirements.
- **Why it matters**: Shared serializers create accidental overexposure and make policy drift easy.
- **Suggested fix**: Split serializers by audience: CT-safe, Org Admin, Employee-self.

### 2. Payroll processing is synchronous request-time business logic
- **File**: `backend/apps/payroll/services.py`
- **Problem**: payroll calculation and finalization run inline, including iterating employees and generating payslips.
- **Why it matters**: This will not scale to 500+ employees and gives poor recovery behavior on partial failure.
- **Suggested fix**: Move pay-run calculation/finalization to Celery jobs with job status, retries, and exception review.

### 3. Attendance regularization is modeled in workflows without an attendance domain
- **Files**: `backend/apps/approvals/models.py`, `backend/apps/employees/models.py`
- **Problem**: approval request kinds and employee workflow assignments mention attendance regularization, but there is no attendance subsystem to back them.
- **Why it matters**: The architecture implies a feature that does not exist, increasing maintenance confusion and product misrepresentation.
- **Suggested fix**: Either build attendance next or remove/hide attendance regularization until it is real.

### 4. API error responses are ad hoc
- **Files**: multiple `views.py` files, e.g. `backend/apps/payroll/views.py`, `backend/apps/documents/views.py`
- **Problem**: Many endpoints return `{'error': str(exc)}` manually; other errors rely on DRF validation responses.
- **Why it matters**: Frontend error handling becomes inconsistent and hard to make user-friendly.
- **Suggested fix**: Standardize an API error envelope with code, message, field errors, and traceable context.

### 5. No API versioning
- **File**: `backend/clarisal/urls.py`
- **Problem**: All APIs are under `/api/*` with no versioning.
- **Why it matters**: Backward compatibility becomes painful once attendance/payroll mature.
- **Suggested fix**: Introduce `/api/v1/` before more surface area hardens.

### 6. Stale duplicate package artifact exists
- **File**: `backend/calrisal/settings/__pycache__/base.cpython-312.pyc`
- **Problem**: A misspelled backend package residue exists next to the real `backend/clarisal`.
- **Why it matters**: Confusing project structure is a maintenance smell and can mislead tooling or contributors.
- **Suggested fix**: Remove the stale tree and ensure generated artifacts are ignored consistently.

### 7. Leave accrual is not operationally separated from balance reads
- **File**: `backend/apps/timeoff/services.py`
- **Problem**: `get_or_create_leave_balance` recalculates credited/used/pending state during reads.
- **Why it matters**: This blurs read-model and posting-model responsibilities and makes accrual auditing harder.
- **Suggested fix**: Move to scheduled ledger postings and keep reads purely representational.

## Security Issues

### CRITICAL
- **CT employee detail API exposes prohibited PII and allows mutation**
  - **Files**: `backend/apps/organisations/views.py`, `backend/apps/employees/serializers.py`
  - **Issue**: CT can fetch and patch employee records beyond the allowed sanitised view.
  - **Why it matters**: Violates least privilege, increases insider-access risk, and contradicts the product policy for support users.
  - **Suggested fix**: Replace serializer, remove patch, add CT-specific permission tests.

- **Field encryption silently falls back to `SECRET_KEY`**
  - **Files**: `backend/apps/common/security.py`, `backend/clarisal/settings/base.py`
  - **Issue**: If `FIELD_ENCRYPTION_KEY` is unset, encrypted fields derive from `SECRET_KEY`.
  - **Why it matters**: Secret-key rotation can silently break decryption of PAN/Aadhaar/bank data.
  - **Suggested fix**: Make `FIELD_ENCRYPTION_KEY` mandatory in non-dev environments and fail fast on startup.

### HIGH
- **Default/dev credentials and credential echoing in seed flow**
  - **File**: `backend/apps/accounts/management/commands/seed_control_tower.py`
  - **Issue**: The seed command defines fallback passwords and prints effective credentials to stdout.
  - **Why it matters**: Unsafe in shared environments and encourages production-like use of demo credentials.
  - **Suggested fix**: Remove fallback passwords, require env vars, and never print secrets.

- **CT UI displays address and phone data**
  - **File**: `frontend/src/pages/ct/OrganisationDetailPage.tsx`
  - **Issue**: The CT employee modal explicitly shows phone and address.
  - **Why it matters**: Even if masked identifiers were removed later, the current UI already breaches the stated CT data policy.
  - **Suggested fix**: Remove the modal fields and replace with a sanitised support snapshot.

- **Payroll item and payslip serializers expose detailed snapshots without audience partitioning**
  - **Files**: `backend/apps/payroll/serializers.py`, `backend/apps/payroll/views.py`
  - **Issue**: Snapshot payloads contain full line-level pay data, and there is no CT-safe or finance-safe serializer separation.
  - **Why it matters**: As CT payroll support expands, overexposure risk will recur unless serializers are role-specific.
  - **Suggested fix**: Define audience-aware serializers before adding CT payroll support.

- **File upload validation is extension/size-based only**
  - **File**: `backend/apps/documents/services.py`
  - **Issue**: `_validate_upload` checks extension and size but not content sniffing, malware scanning, or MIME trustworthiness.
  - **Why it matters**: HR systems routinely hold high-value documents and should not trust extension alone.
  - **Suggested fix**: Add MIME validation and malware scanning before storage.

### MEDIUM
- **Role model is too coarse**
  - **Files**: `backend/apps/accounts/models.py`, `backend/apps/accounts/permissions.py`
  - **Issue**: Only `CONTROL_TOWER`, `ORG_ADMIN`, and `EMPLOYEE` roles exist.
  - **Why it matters**: Real HRMS needs payroll admin, HRBP, manager, recruiter, auditor, and field-level access variants.
  - **Suggested fix**: Introduce granular permission sets or capability-based RBAC.

- **No signed-document download audit trail at request granularity**
  - **Files**: `backend/apps/documents/views.py`, `backend/apps/documents/services.py`
  - **Issue**: Presigned URLs are generated, but download issuance is not clearly audited as a separate sensitive event.
  - **Why it matters**: For PII access reviews, download trails matter.
  - **Suggested fix**: Log download-url issuance with actor, document, and purpose.

### LOW
- **Session auth and CSRF posture is reasonable**
  - **Files**: `backend/apps/accounts/views.py`, `frontend/src/lib/api.ts`
  - **Observation**: CSRF bootstrap and `withCredentials` session handling are correctly wired for a server-rendered session pattern.
  - **Follow-up**: Keep, but add stricter session settings in production.

- **Document downloads use S3 presigned URLs**
  - **File**: `backend/apps/documents/s3.py`
  - **Observation**: URLs expire after 900 seconds and are not guessable public paths.
  - **Follow-up**: Good baseline; pair with download auditing.

## Dead & Stale Code

### 1. Stale backend package residue
- **File**: `backend/calrisal/settings/__pycache__/base.cpython-312.pyc`
- **Issue**: Misspelled duplicate package residue exists.
- **Why it matters**: Creates structural confusion and suggests cleanup gaps.
- **Suggested fix**: Remove and ignore compiled artifacts consistently.

### 2. Skipped Playwright tests
- **Files**:
  - `frontend/e2e/org/leave-plans.spec.ts`
  - `frontend/e2e/employee/leave.spec.ts`
  - `frontend/e2e/employee/onboarding.spec.ts`
- **Issue**: Multiple tests are explicitly skipped.
- **Why it matters**: Critical user flows appear covered but are not.
- **Suggested fix**: Either restore them or delete dead tests and replace with working coverage.

### 3. Hook lint suppressions
- **Files**:
  - `frontend/src/pages/org/NoticeEditorPage.tsx`
  - `frontend/src/pages/org/LeavePlanBuilderPage.tsx`
  - `frontend/src/pages/org/ApprovalWorkflowBuilderPage.tsx`
  - `frontend/src/pages/org/OnDutyPolicyBuilderPage.tsx`
- **Issue**: `eslint-disable-next-line react-hooks/set-state-in-effect` suppressions remain.
- **Why it matters**: They may be justified, but they should be audited because state-setting-in-effect often hides lifecycle bugs.
- **Suggested fix**: Rework state derivation or add comments that explain why suppression is safe.

### 4. Attendance regularization workflow scaffolding is stale relative to product reality
- **Files**: `backend/apps/approvals/models.py`, `backend/apps/employees/models.py`, `frontend/src/pages/org/EmployeeDetailPage.tsx`
- **Issue**: Regularization workflow wiring exists without any actual attendance product behind it.
- **Why it matters**: This is feature debt disguised as completeness.
- **Suggested fix**: Hide or complete it.

## UI/UX Issues

### 1. Employee navigation duplicates profile destinations and omits attendance
- **File**: `frontend/src/components/layouts/EmployeeLayout.tsx`
- **Current experience**: `Profile`, `Identity`, and `Banking` all point to `/me/profile`; there is no attendance entry.
- **What Zoho/Keka does instead**: Attendance is a first-class ESS menu item, and profile subsections are clearly segmented.
- **User impact**: Employees cannot find attendance because it does not exist, and the nav overpromises granularity for profile management.
- **Suggested fix**: Replace duplicate links with true subsection tabs inside profile, and add attendance only when functional.

### 2. CT employee modal presents itself as read-only support visibility while showing PII
- **File**: `frontend/src/pages/ct/OrganisationDetailPage.tsx`
- **Current experience**: The modal says “Read-only employee visibility from Control Tower” but exposes phone/address.
- **What Zoho/Darwinbox does instead**: Support/admin consoles use restricted views or impersonation with audit.
- **User impact**: Support staff get more personal data than policy allows; compliance risk is obscured by the UI language.
- **Suggested fix**: Change both data and copy; show only sanitised support fields.

### 3. Org payroll flow is too compressed for a high-risk task
- **File**: `frontend/src/pages/org/PayrollPage.tsx`
- **Current experience**: Tax slabs, template creation, assignments, and payroll runs are all on one long page with minimal explanation and no wizarding.
- **What Keka/Zoho does instead**: Breaks payroll into structured setup, validation, exceptions, approvals, and publishing flows.
- **User impact**: High cognitive load and high risk of incorrect setup.
- **Suggested fix**: Split payroll into setup, structures, assignments, run processing, and results tabs with explicit validation steps.

### 4. Payroll actions lack confirmation and exception-review affordances
- **File**: `frontend/src/pages/org/PayrollPage.tsx`
- **Current experience**: Finalize and rerun are direct action buttons.
- **What Keka does instead**: Uses staged confirmation and exception review before lock-in.
- **User impact**: Admins can finalize payroll without a confidence-building checkpoint.
- **Suggested fix**: Add confirmation dialogs and an exception summary before finalization.

### 5. Employee payslip UX is too raw
- **File**: `frontend/src/pages/employee/PayslipsPage.tsx`
- **Current experience**: Users see cards plus a `pre` block of rendered text.
- **What Zoho Payroll does instead**: Provides branded, printable, structured payslips/PDFs with richer line-item presentation.
- **User impact**: Low trust and poor usability for a finance-critical artifact.
- **Suggested fix**: Render a proper payslip layout and support download/export.

### 6. Employee dashboard is informative but not operationally complete
- **File**: `frontend/src/pages/employee/DashboardPage.tsx`
- **Current experience**: Good onboarding/documents/leave context, but no attendance or payroll alerts.
- **What Zoho/Keka does instead**: Dashboard is anchored on daily actionability, especially attendance and leave.
- **User impact**: Employees still need to hunt for core tasks, and the dashboard does not reflect daily HR reality.
- **Suggested fix**: Add attendance status, upcoming leave, payslip availability, and pending actions as first-class widgets.

### 7. Org setup is better than a blank start, but still fragmented
- **Files**: `frontend/src/components/org/OrgSetupBanner.tsx`, `frontend/src/pages/org/SetupPage.tsx`
- **Current experience**: There is a guided setup banner and redirect logic, but setup still happens by jumping among regular admin pages.
- **What Zoho/Keka does instead**: Uses tighter setup wizards with context and dependencies made explicit.
- **User impact**: First-time admins can skip steps without understanding downstream impact.
- **Suggested fix**: Introduce a proper guided setup workspace with completion validation per step.

### 8. Tables are serviceable but not enterprise-grade
- **Files**: `frontend/src/pages/org/EmployeesPage.tsx`, `frontend/src/pages/org/AuditPage.tsx`
- **Current experience**: Search/filter/pagination exist selectively, but there is no column chooser, saved filters, or broad export support.
- **What Zoho does instead**: More mature list views with saved views and custom columns.
- **User impact**: Admin workflows become slower as data volume grows.
- **Suggested fix**: Standardize a table framework with filters, export, bulk actions, and column control.

## Content Issues

### 1. Login copy is acceptable but slightly internal-facing
- **Files**: `frontend/src/pages/auth/LoginPage.tsx`, `frontend/src/pages/auth/ControlTowerLoginPage.tsx`
- **Issue**: Phrases like “collated admin workspace” are not standard HR software language.
- **Why it matters**: First-touch copy should reduce ambiguity, not introduce it.
- **Suggested fix**: Use simpler HR terms and clarify the difference between employee, HR admin, and platform operator access.

### 2. Empty states are generally good
- **Files**: many pages, e.g. `frontend/src/pages/org/EmployeesPage.tsx`, `frontend/src/pages/employee/PayslipsPage.tsx`
- **Issue**: This is actually a strength; empty states usually explain the next step.
- **Why it matters**: Early-stage HR products often fail here.
- **Suggested fix**: Keep this pattern and extend it to payroll/attendance once those modules mature.

### 3. Error messaging is too generic on high-risk flows
- **Files**: `frontend/src/pages/org/PayrollPage.tsx`, `frontend/src/pages/employee/LeavePage.tsx`
- **Issue**: Many flows fall back to “Unable to…” toasts from `getErrorMessage`.
- **Why it matters**: HR and payroll operators need clear failure causes and fixes.
- **Suggested fix**: Surface domain-specific backend validation codes and map them to actionable UI copy.

### 4. No obvious lorem ipsum or fake placeholder prose in production screens
- **Observation**: This is positive. The product language is mostly productised rather than scaffold text.

## Recommendations

### Immediate — fix before go-live
- Remove CT employee mutation and replace CT employee detail with a sanitised serializer and UI. Files: `backend/apps/organisations/views.py`, `backend/apps/employees/serializers.py`, `frontend/src/pages/ct/OrganisationDetailPage.tsx`.
- Enforce `FIELD_ENCRYPTION_KEY` in production and remove dev-secret fallbacks/credential echoing. Files: `backend/apps/common/security.py`, `backend/clarisal/settings/base.py`, `backend/apps/accounts/management/commands/seed_control_tower.py`.
- Put payroll behind a beta boundary or internal-only flag until statutory correctness is materially expanded. Files: `frontend/src/pages/org/PayrollPage.tsx`, `backend/apps/payroll/services.py`.
- Remove attendance regularization from visible workflow/assignment surfaces until attendance exists, or implement attendance next. Files: `backend/apps/approvals/models.py`, `frontend/src/pages/org/EmployeeDetailPage.tsx`.
- Add confirmations and exception review for payroll finalization and rerun. File: `frontend/src/pages/org/PayrollPage.tsx`.

### Short-term — next 1–2 sprints
- Build the attendance subsystem: shifts, punches, attendance days, regularization, holiday interplay, employee attendance UI, org attendance admin.
- Add CT read-only support surfaces for org payroll runs, approval history, and config diffs with role-safe serializers.
- Refactor payroll into async jobs plus richer validation, exception handling, and structured payslip documents.
- Split serializers and permission layers by audience to stop CT/Org Admin/Employee data leakage through reuse.
- Add a dedicated reports center for headcount, leave, payroll, and audit exports.

### Long-term — roadmap items
- Performance management: goals, reviews, 360, probation.
- Recruitment / ATS and onboarding task orchestration.
- Granular RBAC with payroll/HR/manager/support/auditor personas.
- Org chart and manager analytics.
- Mobile-first ESS improvements or dedicated mobile app/PWA for attendance-heavy usage.
