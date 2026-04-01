# Clarisal HRMS — Comprehensive Audit Report

**Generated**: April 1, 2026
**Auditor**: AI-assisted codebase analysis (Claude Code)
**Scope**: Full-stack audit excluding payroll (backend + frontend)
**Benchmark**: Zoho People (primary), Darwinbox, GreytHR, Keka, BambooHR

---

## Executive Summary

Clarisal is a well-architected, multi-tenant HRMS platform built on Django 4.2 and React 19. The engineering team has laid strong foundations: the database schema is properly tenant-scoped, the backend cleanly separates concerns across service/repository/view layers, and the frontend's custom design system is polished and visually consistent. For a system at this stage of development, the architectural quality is notably high — scoring 8/10 on architecture and 7/10 on code quality.

However, the platform currently covers approximately **35–40% of feature parity** with leading HRMS tools like Zoho People or GreytHR. Three entire modules — Attendance & Time Tracking, Performance Management, and Reports & Analytics — are either absent or embryonic. The Leave Management module (the most complete at ~70%) is missing comp-off, leave encashment, and forecasting. RBAC is restricted to three flat roles with no granular department-level permissions, which will limit enterprise sales. These are not architectural failures — the codebase is ready to extend — but they represent significant product work before Clarisal can compete for mid-market HR buyers.

On security, the most urgent iss`:que is credential exposure: if a `.env` file containing the `SECRET_KEY` and `AWS_SECRET_ACCESS_KEY` has ever been committed to the repository, those credentials must be treated as compromised and rotated immediately. Additionally, the `FIELD_ENCRYPTION_KEY` defaults to an empty string, meaning sensitive employee data (PAN, Aadhaar, bank accounts) may currently be encrypted with the Django `SECRET_KEY` — a fragile arrangement that would silently corrupt all encrypted records on a key rotation. These two issues require immediate attention before any production deployment.

---

## Table of Contents

1. [Tech Stack & Module Map](#1-tech-stack--module-map)
2. [Feature Gap Analysis](#2-feature-gap-analysis)
3. [Architecture Review](#3-architecture-review)
4. [Code Quality Findings](#4-code-quality-findings)
5. [UI/UX Evaluation](#5-uiux-evaluation)
6. [Prioritized Recommendations](#6-prioritized-recommendations)
7. [Appendix A: Dead Code & TODO Catalogue](#appendix-a-dead-code--todo-catalogue)
8. [Appendix B: Security Configuration Checklist](#appendix-b-security-configuration-checklist)

---

## 1. Tech Stack & Module Map

### 1.1 Backend Stack

| Component | Version | Technology |
|-----------|---------|-----------|
| Framework | 4.2.16 | Django |
| REST API | 3.15.2 | Django REST Framework |
| Database | 2.9.9 | PostgreSQL (psycopg2) |
| Task Queue | 5.4.0 | Celery |
| Cache / Broker | 5.1.1 | Redis |
| File Storage | 1.35.30 | AWS S3 (boto3 + django-storages) |
| Authentication | — | Session-based (no JWT) |
| CORS | 4.4.0 | django-cors-headers |
| Rate Limiting | 4.1.0 | django-ratelimit |
| Field Encryption | 45.0.7 | cryptography (Fernet) |

Key settings (`backend/calrisal/settings/base.py`):
- `AUTH_USER_MODEL = 'accounts.User'`
- `AUTHENTICATION_BACKENDS = ['apps.accounts.auth_backends.AudienceEmailBackend']`
- Session cookie: `HttpOnly=True`, `SameSite=Lax`, `age=12h`
- Global throttle: `anon: 300/hr`, `user: 3000/hr`; per-endpoint overrides (login: 5/min, approval actions: 60/hr)
- CORS: whitelist from env, defaults to `http://localhost:5173`
- Celery result backend: django-db

### 1.2 Frontend Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 19.2.4 |
| Router | React Router DOM | 7.13.2 |
| Server State | TanStack Query | 5.95.2 |
| HTTP Client | Axios | 1.14.0 |
| UI Components | Custom + Radix UI primitives | — |
| Icons | Lucide React | 1.7.0 |
| Animations | Motion (Framer Motion) | 12.38.0 |
| Styling | Tailwind CSS | 4.2.2 |
| Build | Vite | 8.0.1 |
| E2E Testing | Playwright | 1.58.2 |
| Fonts | Plus Jakarta Sans (body), JetBrains Mono (code) | — |

`frontend/src/App.tsx` configures TanStack Query with `staleTime: 5min`, `retry: 1`.

### 1.3 Django App Inventory

| App | Purpose | Key Models |
|-----|---------|-----------|
| `accounts` | Auth, user management, RBAC | User, PasswordResetToken |
| `organisations` | Multi-tenancy, billing, lifecycle | Organisation, OrganisationMembership, OrganisationLicenceBatch, OrganisationAddress, Department, OfficeLocation |
| `employees` | Employee records, profiles, documents | Employee, EmployeeProfile, EducationRecord, EmployeeBankAccount, EmployeeGovernmentId, EmployeeFamilyMember, EmployeeEmergencyContact |
| `timeoff` | Leave, on-duty, holidays | LeaveCycle, LeavePlan, LeavePlanRule, LeaveType, LeaveBalance, LeaveBalanceLedgerEntry, LeaveRequest, HolidayCalendar, Holiday, OnDutyPolicy, OnDutyRequest |
| `approvals` | Workflow engine | ApprovalWorkflow, ApprovalWorkflowRule, ApprovalStage, ApprovalStageApprover, ApprovalRun, ApprovalAction |
| `documents` | Document storage, onboarding | Document, EmployeeDocumentRequest, OnboardingDocumentType |
| `invitations` | Invite flows | Invitation |
| `audit` | Event logging | AuditLog |
| `communications` | Notices, announcements | Notice |
| `common` | Shared utilities | — (security.py: Fernet encryption) |

### 1.4 API Route Structure

```
/api/auth/     → Login, logout, password reset (accounts)
/api/ct/       → Control Tower: orgs, dashboard, audit (organisations)
/api/org/      → Org admin: employees, locations, departments, timeoff, approvals, notices
/api/me/       → Employee self-service: profile, documents, leave, on-duty, approvals
```

### 1.5 Frontend Route Map

**Public:** `/auth/login` · `/ct/login` · `/auth/invite/:token` · `/auth/reset-password` · `/ct/reset-password`

**Control Tower** (`requiredAccess="CONTROL_TOWER"`): `/ct/dashboard` · `/ct/organisations` · `/ct/organisations/:id`

**Org Admin** (`requiredAccess="ORG_ADMIN"`): `/org/dashboard` · `/org/profile` · `/org/employees` · `/org/locations` · `/org/departments` · `/org/holidays` · `/org/leave-cycles` · `/org/leave-plans` · `/org/on-duty-policies` · `/org/approval-workflows` · `/org/notices`

**Employee Self-Service** (`requiredAccess="EMPLOYEE"`): `/me/onboarding` · `/me/dashboard` · `/me/profile` · `/me/education` · `/me/documents` · `/me/leave` · `/me/od` · `/me/approvals`

---

## 2. Feature Gap Analysis

### 2.1 Summary Matrix

| Module | Completeness | Key Missing Features |
|--------|-------------|---------------------|
| Employee Management | 60% | Org chart, custom fields, skill matrix, offboarding workflow |
| Leave Management | 70% | Comp-off, encashment, forecasting, restricted periods |
| Attendance & Time Tracking | 5% | Check-in/out, shifts, biometrics, regularization — almost entirely absent |
| On-Duty Requests | 65% | Mobile OD, geolocation, bulk OD |
| Approvals & Workflows | 50% | Escalation, delegation, bulk approvals, parallel stages; builder UI incomplete |
| Documents & Onboarding | 55% | E-signature, task checklists, document expiry, welcome kits |
| Communications / Notices | 40% | Email delivery, read tracking, notification center |
| Audit & Compliance | 35% | Old/new value diffs, retention policies, access logs, DPDP |
| Organisation & Master Data | 75% | Cost centers, soft-delete on dept/location |
| RBAC & Access Control | 30% | Only 3 flat roles; no custom roles, no dept-scoped manager access, no SSO |
| Reports & Analytics | 10% | Only 2 dashboards; no reports module, no export, no charts |
| Performance Management | 0% | Entire module missing |
| Payroll & Compensation | 0% | Out of scope for this audit |

**Overall: ~35–40% feature parity with market leaders**

---

### 2.2 Employee Management

**Implemented:**
- Core record: `employee_code`, `designation`, `employment_type` (FULL_TIME/PART_TIME/CONTRACT/INTERN), `status` (INVITED/PENDING/ACTIVE/RESIGNED/RETIRED/TERMINATED), `date_of_joining`, `date_of_exit`, `reporting_to` (self-referential FK)
- EmployeeProfile: personal details, address, contact
- EducationRecord: degree, institution, field_of_study, grade
- EmployeeGovernmentId: PAN/Aadhaar (Fernet-encrypted + masked)
- EmployeeBankAccount: bank details (encrypted), primary account flag
- EmployeeFamilyMember, EmployeeEmergencyContact
- Soft delete on Employee and all satellite records
- Employee invite flow with document request assignment
- `org/EmployeesPage.tsx`: directory with search, status filter, pagination, invite form

**Missing / Gaps:**
- **No org chart** — `reporting_to` FK exists but no tree traversal API and no frontend visualization. Zoho People has interactive drill-down org charts.
- **No custom fields** — all employee attributes are hard-coded. Darwinbox/GreytHR allow tenant-level custom fields (cost center, project, etc.).
- **No skill matrix or competency tracking**.
- **No probation period logic** — onboarding status tracks document completion but not probation end date or confirmation workflow.
- **No bulk employee import** (CSV/Excel).
- **No offboarding workflow** — RESIGNED/TERMINATED statuses exist, but no exit interview, asset return, or access revocation checklist.
- **No succession planning**.

---

### 2.3 Leave Management

**Implemented** (strongest module):
- `LeaveCycle` with 4 cycle types: CALENDAR_YEAR, FINANCIAL_YEAR, CUSTOM_FIXED_START, EMPLOYEE_JOINING_DATE
- `LeavePlan` with priority-based rule matching (department / location / employment_type / employee)
- `LeaveType`: entitlement, credit frequency (MONTHLY/QUARTERLY/HALF_YEARLY/YEARLY), carry-forward (NONE/CAPPED/UNLIMITED), pro-ration on join, half-day, attachment requirement, notice days, max consecutive days, past/future request flags, max balance cap
- `LeaveBalance` with full ledger (`LeaveBalanceLedgerEntry`): OPENING, CREDIT, ADJUSTMENT, DEBIT, CARRY_FORWARD, EXPIRY
- `LeaveRequest` with full lifecycle
- `HolidayCalendar` with classification (PUBLIC/RESTRICTED/COMPANY), location assignment, publish workflow
- Frontend: `LeavePage.tsx`, `LeavePlansPage.tsx`, `LeaveCyclesPage.tsx`, `HolidaysPage.tsx`

**Missing / Gaps:**
- **No Compensatory Off (Comp-Off)** — no models, no auto-generation from overtime. Required by GreytHR, Darwinbox, Keka.
- **No comp-off expiry rules**.
- **No leave encashment** — converting unused leave to payout on exit is a statutory requirement in India.
- **No leave forecasting** — Zoho People shows projected balances for next 12 months.
- **No restricted leave periods** (blackout dates).
- **No bulk leave approval** — managers must approve one request at a time.
- **No carry-forward expiry automation** — cap exists in model but no scheduled expiry job.
- Only one active leave plan per employee (OneToOne assignment).

---

### 2.4 Attendance & Time Tracking

**Implemented:**
- `OnDutyPolicy` and `OnDutyRequest` with FULL_DAY/FIRST_HALF/SECOND_HALF/TIME_RANGE, purpose, destination, full lifecycle
- Frontend: `OnDutyPage.tsx`, `OnDutyPoliciesPage.tsx`

**Missing (near-total gap):**
- **No attendance check-in/check-out** — no models, no API, no UI. This is the single largest missing feature for Indian SMB HRMS buyers.
- **No shift scheduling** — no shift models.
- **No overtime tracking or auto-comp-off generation**.
- **No attendance regularization** — employees can't correct late marks or missed punches.
- **No biometric integration**.
- **No mobile check-in or geolocation enforcement**.
- **No attendance reports**.

---

### 2.5 Approvals & Workflows

**Implemented:**
- `ApprovalWorkflow` with `ApprovalWorkflowRule` — priority-based matching on department/location/employee_type/designation/leave_type
- `ApprovalStage`: sequential, configurable mode (ALL approvers vs ANY approver)
- `ApprovalStageApprover`: REPORTING_MANAGER / SPECIFIC_EMPLOYEE / PRIMARY_ORG_ADMIN
- `ApprovalFallback`: NONE / SPECIFIC_EMPLOYEE / PRIMARY_ORG_ADMIN
- `ApprovalRun` with GenericForeignKey (supports LeaveRequest and OnDutyRequest)
- `ApprovalAction` per-user per-stage with comment and timestamp
- Frontend: `employee/ApprovalsPage.tsx` (inbox), `org/ApprovalWorkflowsPage.tsx` (config)

**Missing / Gaps:**
- **No escalation** — no auto-escalation after N days of inaction.
- **No approval delegation** — managers cannot delegate approvals while on leave.
- **No bulk approval UI** — managers must action each pending request individually.
- **No parallel approvals** — only sequential stages.
- **No email/push notification to approvers** — approval requests are in-app only.
- **Workflow builder UI is incomplete** — `org/ApprovalWorkflowsPage.tsx` can create a workflow by name/description but the rule-matching and stage configuration UI is read-only; multi-stage workflows cannot be built through the UI.
- **No workflow versioning**.

---

### 2.6 Documents & Onboarding

**Implemented:**
- `OnboardingDocumentType`: 11 document categories + custom support
- `EmployeeDocumentRequest`: REQUESTED/SUBMITTED/VERIFIED/REJECTED/WAIVED lifecycle
- `Document`: file storage with mime type, file hash, version, reviewed_by
- `employee/OnboardingPage.tsx`: multi-section form (basic details, family, emergency, education, documents) with upload progress
- `employee/DocumentsPage.tsx`: document management

**Missing / Gaps:**
- **No onboarding task checklists** — document requests exist but no broader task framework (IT setup, buddy assignment, training enrollment).
- **No e-signature** — policy acknowledgments cannot be signed digitally.
- **No document expiry tracking** — passport, visa, and other time-limited documents have no expiry date or alert.
- **No probation completion workflow**.
- **No welcome kit generation**.
- **No conditional document requests** based on employment type.

---

### 2.7 Communications & Notices

**Implemented:**
- `Notice`: org-scoped, audience segmentation (ALL_EMPLOYEES/DEPARTMENTS/OFFICE_LOCATIONS/SPECIFIC_EMPLOYEES), DRAFT/SCHEDULED/PUBLISHED/ARCHIVED states
- `org/NoticesPage.tsx`: create, publish, archive

**Missing:** No email delivery, no read/view tracking, no surveys, no notification center (bell icon) for employees.

---

### 2.8 Audit & Compliance

**Implemented:**
- `AuditLog`: actor, organisation, action, target_type, target_id, payload, ip_address, user_agent with indexes on (organisation, actor)
- `AuditTimeline` component displays log entries per entity
- Auth events (login/logout/failed-login) logged via signals (`accounts/signals.py`)

**Missing / Gaps:**
- **No old-value/new-value diff recording** — `AuditLog.payload` captures current state but not the before/after delta. "Salary changed from ₹50K to ₹70K" is impossible to surface.
- **No data retention or purge policies** — GDPR/DPDP requires defined retention periods.
- **No access log** — no tracking of who viewed which employee's sensitive record.
- **No compliance report templates** — no statutory reports (EPF, ESI, Form 16 data).
- **No DPDP (India Digital Personal Data Protection Act) readiness** — no consent tracking, no right-to-erasure workflow.

---

### 2.9 RBAC & Access Control

**Implemented:**
- `AccountType`: CONTROL_TOWER / WORKFORCE; `UserRole`: CONTROL_TOWER / ORG_ADMIN / EMPLOYEE
- Permission classes: `IsControlTowerUser`, `IsOrgAdmin`, `IsEmployee`, `BelongsToActiveOrg`, `OrgAdminMutationAllowed`, `ApprovalActionsAllowed`
- Workspace-based session switching (active_admin_org_id, active_employee_org_id in session)
- Org operations guard (blocks mutations on licence expiry)

**Missing / Gaps (significant):**
- **Only 3 roles** — no HR_MANAGER, DEPT_MANAGER, PAYROLL_ADMIN, or custom role. Zoho People has 20+ predefined roles plus a custom role builder.
- **No department-scoped manager access** — managers see all employees in the org.
- **No field-level permissions** — salary data, government IDs visible to all org admins.
- **No SSO / SAML** — enterprise identity federation not supported.
- **No API keys** — no mechanism for third-party integrations to authenticate.

---

### 2.10 Reports & Analytics

**Implemented:**
- `CTDashboardStatsView`: org count, employee count, licence usage
- `OrgDashboardStatsView`: 7 metrics (total/active/invited/pending employees, licences, approvals, docs)
- `org/DashboardPage.tsx`: metric cards, department/location distribution (inline text bars), recent leave/OD/joins

**Missing (critical gap):**
- Only 2 dashboard summaries vs. 50+ standard reports in Zoho People
- **No reports module** — no leave usage, no attendance summary, no headcount trends, no exit reports, no document compliance, no approval turnaround time
- **No data export** to CSV/Excel
- **No custom report builder**
- **No scheduled/emailed reports**
- **No charts or graphs** — all metrics are text-based; no line charts, bar charts, or pie charts

---

### 2.11 Performance Management

Not implemented. Zero models, endpoints, or UI exist. Entire module missing: appraisal cycles, review templates, goal setting, OKR tracking, 360-degree feedback, rating calibration, competency frameworks, succession planning.

---

## 3. Architecture Review

### 3.1 Separation of Concerns — Excellent

The backend uses a clean three-layer architecture:

```
Views       (permission checks + request/response)
  ↓
Services    (business logic + validation + DB mutations + audit logging)
  ↓
Repositories (query optimization)
```

`employees/services.py:invite_employee()` handles licence validation, user creation, employee record, document request assignment, invitation email, and audit logging — none of this leaks into the view. Signals (`accounts/signals.py`, `organisations/signals.py`) are deliberately limited to audit logging only; `organisations/signals.py` contains an explicit comment: "Audit logging is intentionally handled in services.py."

### 3.2 Multi-Tenancy — Excellent

Every employee-related model carries an `organisation` FK with `on_delete=CASCADE`. All queries open with `.filter(organisation=organisation)`. Session-based workspace switching (`get_workspace_state()` in `accounts/workspaces.py`) validates org billing state before serving any data, and the `WorkspaceState` dataclass cleanly separates admin memberships from employee records — allowing a user to be an org admin in Company A and an employee in Company B simultaneously.

### 3.3 N+1 Query Prevention — Good (one known gap)

`employees/repositories.py:13-26` uses both `select_related` and `prefetch_related` comprehensively, loading `user`, `department`, `office_location`, `reporting_to__user`, `education_records`, `government_ids`, `bank_accounts`, `documents`, `document_requests__document_type_ref`, `family_members`, and `emergency_contacts` in a single query set.

**Known gap**: `employees/services.py:~600` (inside `get_employee_dashboard()`) iterates over approval actions and accesses `action.approval_run.subject_label` and `action.approval_run.request_kind` per iteration without `.select_related('approval_run')`. This fires one query per pending approval action on every employee dashboard load.

### 3.4 API Design — Good

- Consistent REST conventions; custom exception handler in `accounts/exceptions.py` normalizes all DRF error shapes
- Per-endpoint `throttle_scope` configuration
- **No API versioning** — all routes are unversioned (`/api/org/employees/`). Breaking changes will affect all clients simultaneously
- No OpenAPI/Swagger documentation generated

### 3.5 Auth & Security — Good (with two critical gaps)

- Session cookies: `HttpOnly=True`, `SameSite=Lax`, 12-hour age
- CSRF tokens auto-attached to all non-GET requests via Axios interceptor (`lib/api.ts`)
- Global 401/403 handler dispatches `clarisal:auth-lost` event triggering logout
- Permission classes stacked in composition on every view
- No JWT — sessions only. Limits mobile API and third-party integration scenarios

Critical gaps: see §4.1.1 and §4.1.2.

### 3.6 State Management (Frontend) — Clean

- `AuthContext` holds auth state only; all business data via TanStack Query
- No prop drilling — custom domain hooks (`useOrgAdmin`, `useEmployeeSelf`, `useCtOrganisations`) compose queries and mutations
- `staleTime: 5min`, `retry: 1` in `App.tsx`
- Cache invalidation is broad (`queryClient.invalidateQueries({ queryKey: ['org'] })`) — acceptable at MVP scale but will cause unnecessary refetches as query surface grows; should migrate to entity-level keys (e.g., `['org', orgId, 'profile']`)

### 3.7 Configuration vs. Hardcoding

Mostly configurable, with exceptions:
- Employee code format hardcoded as `EMP{counter:03d}` in `employees/services.py:~82` — should be a per-org configurable template
- `DASHBOARD_NOTICE_LIMIT = 3` in `employee/DashboardPage.tsx` — UI constant, should be configurable
- Leave accrual types, cycle types, employment types: configurable via Django choices ✅
- Approval workflow rules: fully configurable via UI/API ✅

### 3.8 Database Schema

**Indexing is well-considered:**

| Table | Index | Purpose |
|-------|-------|---------|
| employees | (organisation, status, is_deleted) | Active employee list |
| employees | (user, organisation, is_deleted) | User's employee record |
| approval_runs | (organisation, status) | Pending approvals |
| approval_runs | (content_type, object_id) | Find approval for a request |
| audit_logs | (organisation, created_at) | Org audit timeline |
| leave_requests | (employee, leave_plan, cycle_start) | Balance calculations |

`migrations/0007` adds covering indexes retroactively to the employees table — a good sign of iterative optimization.

**Field encryption** (`common/security.py`): Fernet with `sha256(FIELD_ENCRYPTION_KEY)` key derivation. Silent `InvalidToken → return ''` on decryption failure — see §4.1.2.

---

## 4. Code Quality Findings

### 4.1 Critical

#### 4.1.1 Potential Credential Exposure in Version Control

If the `.env` file containing `SECRET_KEY`, `AWS_SECRET_ACCESS_KEY`, `EMAIL_HOST_PASSWORD`, or the database URL has ever been committed to git, those credentials are part of the history and must be treated as compromised.

**Immediate actions:**
1. Confirm `.env` is in `.gitignore`
2. Run `git log --all --full-history -- .env` to check if it was ever tracked
3. If tracked: rotate Django `SECRET_KEY`, AWS IAM keys, database password, email credentials
4. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, or environment injection via CI/CD) for production

**File**: `backend/calrisal/settings/base.py:16` — default fallback `'django-insecure-dev-key-change-in-production'` confirms the secret key is expected from environment.

#### 4.1.2 FIELD_ENCRYPTION_KEY Defaults to Empty String → Falls Back to SECRET_KEY

**File**: `backend/calrisal/settings/base.py:161`
```python
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')
```

**File**: `backend/apps/common/security.py:19`
```python
seed = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or settings.SECRET_KEY
```

If `FIELD_ENCRYPTION_KEY` is not set in the environment, encryption silently falls back to `SECRET_KEY`. Rotating the Django secret key — a standard security response to a compromise — will make every PAN, Aadhaar number, and bank account number silently unreadable. `decrypt_value()` returns `''` on `InvalidToken` without logging, so data corruption is invisible.

**Fix**: Make `FIELD_ENCRYPTION_KEY` a required environment variable. Add a Django check at startup. Document a key rotation migration strategy.

#### 4.1.3 Bare `except Exception: pass` on Critical Data Path

**File**: `backend/apps/employees/services.py:621`
```python
except Exception:  # noqa: BLE001
    pass
```

This silences the entire dashboard data aggregation (approvals, leave balance, documents). Any bug in that code path returns an incomplete dashboard with no log, no alert, no error response.

Additional bare-except sites: `accounts/views.py:206, 231`, `timeoff/views.py:78, 93`.

**Fix**: Catch specific exceptions; add `logger.exception(...)` before returning defaults.

### 4.2 High Priority

#### 4.2.1 N+1 Query on Every Employee Dashboard Load

**File**: `backend/apps/employees/services.py:~600-622`

```python
approvals = get_pending_approval_actions_for_user(...)
items = [
    {
        'label': action.approval_run.subject_label,       # DB hit per action
        'request_kind': action.approval_run.request_kind, # DB hit per action
    }
    for action in approvals
]
```

With 10 pending approvals: 10 extra queries per dashboard load.

**Fix**: Add `.select_related('approval_run')` to the approvals queryset.

#### 4.2.2 Silent Decryption Failure Returns Empty String

**File**: `backend/apps/common/security.py:40`
```python
except InvalidToken:
    return ''  # No log, no alert
```

Data corruption in encrypted fields is completely invisible to operators and users.

**Fix**: Add `logger.error(f"Decryption failed for {context}")` before returning `''`.

#### 4.2.3 Approval Workflow Builder UI Does Not Match Backend Capability

`org/ApprovalWorkflowsPage.tsx` can create a workflow by name and description. The backend supports rich multi-stage conditional routing (rules matching department/location/employment type/designation/leave type, sequential stages with ALL/ANY mode, fallback policies). None of this is configurable through the UI — org admins must use the API directly or the Django admin panel to build any non-trivial workflow.

#### 4.2.4 `window.confirm()` for Destructive Actions

**File**: `frontend/src/pages/ct/OrganisationDetailPage.tsx:150, 227`

Browser-native confirm dialogs are unstyled, inaccessible (no ARIA), and break the design system. The codebase already has a `ApprovalDecisionDialog` Radix component that should be extended and reused for all destructive confirmations.

#### 4.2.5 No `onError` Handlers on TanStack Mutations

**File**: `frontend/src/hooks/useOrgAdmin.ts:84-100`
```typescript
return useMutation({
  mutationFn: updateOrgProfile,
  onSuccess: () => { queryClient.invalidateQueries(...) },
  // No onError handler
})
```

Multiple mutations across `useOrgAdmin.ts` and `useEmployeeSelf.ts` lack `onError`. Failed mutations produce no user-facing feedback. The `getErrorMessage` utility and `toast.error` are available and already used in page-level handlers; they need to be wired into the mutation hooks.

### 4.3 Medium Priority

#### 4.3.1 Employee Code Format Hardcoded

**File**: `backend/apps/employees/services.py:~82`
```python
code = f'EMP{counter:03d}'
```
All tenants get the same format. Should be a per-organisation configurable template.

#### 4.3.2 Error Response Collapses Multiple Validation Errors to One

**File**: `backend/apps/accounts/exceptions.py:36-38`
```python
response.data = {'error': response.data['non_field_errors'][0]}  # Only first error
```
When multiple fields fail simultaneously, the frontend receives only the first. Users must fix and resubmit iteratively.

#### 4.3.3 No `MAX_PAGE_SIZE` on Pagination

**File**: `backend/calrisal/settings/base.py:140`

No `MAX_PAGE_SIZE` set. A client can request `?page_size=100000` and receive the entire dataset in one response, potentially causing DoS via memory exhaustion.

#### 4.3.4 `console.error` in Production Code

**File**: `frontend/src/components/ui/AppErrorBoundary.tsx`
```typescript
console.error('Frontend render error', error, errorInfo)
```
Should be gated by `import.meta.env.DEV` to avoid leaking stack traces to browser consoles in production.

### 4.4 Test Coverage

- 125 Python test files found across backend apps
- Test configuration (`calrisal/settings/test.py`) uses SQLite in-memory, fast MD5 hashing, disabled throttling — well-structured for CI speed
- Backend test infrastructure is solid
- Frontend: Playwright E2E testing configured but no unit or component tests (`*.test.*`, `*.spec.*` absent from `frontend/src/`)
- No frontend unit tests for hooks, API functions, or component logic

---

## 5. UI/UX Evaluation

### 5.1 Design System — Excellent

`frontend/src/index.css` defines a comprehensive HSL token system: 20+ semantic color tokens, light/dark theme support via `:root[data-theme='dark']`, consistent border-radius tokens, shadow system, and typography (Plus Jakarta Sans + JetBrains Mono).

**Reusable component library:**
- `PageHeader`, `SectionCard`, `StatusBadge` (5-tone), `MetricCard`, `EmptyState`
- Skeleton loaders: `SkeletonMetricCard`, `SkeletonPageHeader`, `SkeletonTable`, `SkeletonFormBlock`
- `ApprovalDecisionDialog` (Radix UI), `AuditTimeline`, `AppErrorBoundary`, `FieldErrorText`
- Consistent button system: `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger`
- Consistent form system: `.field-input`, `.field-select`, `.field-textarea`, `.field-label`

Overall visual consistency is high — all cards use the same border-radius, all tables use the same `.table-shell` / `.table-head-row` / `.table-row` classes, all forms use the same field classes.

### 5.2 Page Ratings

| Page | Rating | Key Issues |
|------|--------|------------|
| `auth/LoginPage.tsx` | Good (4/5) | Missing ARIA labels, no form reset after error |
| `auth/ControlTowerLoginPage.tsx` | Good (4/5) | Duplicate of LoginPage — should share a component |
| `auth/InviteAcceptPage.tsx` | Good (4/5) | No password strength indicator |
| `auth/ResetPasswordPage.tsx` | Good (4/5) | Loading screen has minimal context text |
| `employee/DashboardPage.tsx` | Excellent (5/5) | Leave balances text-only (no progress bars); no approval history |
| `employee/LeavePage.tsx` | Excellent (4.5/5) | No withdrawal confirmation dialog |
| `employee/ApprovalsPage.tsx` | Good (4/5) | No approval history, no bulk actions, no pagination |
| `employee/DocumentsPage.tsx` | Good (4/5) | No drag-drop, dual upload forms are confusing |
| `employee/OnDutyPage.tsx` | Good (4/5) | No date picker, no time-range validation |
| `employee/OnboardingPage.tsx` | Needs Work (3.5/5) | Address fields as textarea, no required indicators, no auto-save |
| `org/DashboardPage.tsx` | Excellent (5/5) | No time-range filter, no period comparison, text-only bars |
| `org/EmployeesPage.tsx` | Excellent (4.5/5) | No column sorting, 7-column table not mobile-ready |
| `org/LeavePlansPage.tsx` | Good (4/5) | Cannot add multiple leave types in UI, no edit capability |
| `org/HolidaysPage.tsx` | Good (4/5) | No duplicate date check, no publish confirmation |
| `org/NoticesPage.tsx` | Good (4/5) | No preview, no scheduled publish |
| `org/ApprovalWorkflowsPage.tsx` | Needs Work (3/5) | Workflow builder UI incomplete for multi-stage rules |
| `org/ProfilePage.tsx` | Good (4/5) | Address form conditional logic could be clearer |
| `org/LeaveCyclesPage.tsx` | Good (4/5) | Start month/day as number inputs (should be select) |
| `ct/OrganisationDetailPage.tsx` | Excellent (4.5/5) | Cognitive overload (8+ sections), browser-native confirm dialogs |

### 5.3 Cross-Cutting UX Issues

**Forms:**
- **No required field indicators (asterisks)** anywhere in the codebase — users must guess which fields are mandatory. This affects every form across every page.
- `employee/OnboardingPage.tsx`: address `line1`/`line2` rendered as `<textarea>` when they should be `<input type="text">`
- `org/LeaveCyclesPage.tsx`: start_month (1–12) and start_day (1–31) as `<input type="number">` — should be `<select>` with human-readable labels
- Inline validation only triggers on submit — no real-time email format, password strength, or GSTIN format feedback
- Some forms reset state after success (`LeavePage.tsx:38`); others do not (`LeavePlansPage.tsx`) — inconsistent behavior

**Navigation:**
- **No breadcrumbs** on any page — users in `/org/employees/:id` have no visible path back
- No employee-facing sidebar visible in employee page source
- No back links except on CT detail pages

**Accessibility:**
- **No ARIA labels** on icon-only buttons (ThemeToggle, edit/delete icon buttons throughout)
- **No `aria-expanded`** on collapsible sections (employee invite form toggle, etc.)
- **No `aria-live` regions** for toast notifications — screen readers won't announce them
- No visible focus indicators on custom components beyond browser defaults
- Radix UI `Dialog` has built-in accessibility — used correctly for `ApprovalDecisionDialog` ✅

**Mobile:**
- `org/EmployeesPage.tsx` 7-column table and `ct/OrganisationDetailPage.tsx` licence table require horizontal scroll on mobile with no visual indicator
- No hamburger menu — sidebar stacks vertically on small screens rather than collapsing
- Toast position `top-right` (`App.tsx:27`) may be off-screen on narrow viewports

### 5.4 Zoho People UX Comparison

| Feature | Zoho People | Clarisal | Assessment |
|---------|-------------|----------|------------|
| Pending actions widget | Present | Dashboard cards | Similar |
| Leave balance progress bars | Visual fill bars | Text-only metric cards | Clarisal behind |
| Approval history timeline | Full history with actors | Only pending count | Clarisal behind |
| Notification center (bell) | Present | Not implemented | Clarisal missing |
| Org chart visualization | Interactive drill-down | Not implemented | Clarisal missing |
| Document folder structure | Folder-based | Flat file uploads | Clarisal behind |
| Quick-action floating buttons | FAB buttons | Top-nav buttons only | Clarisal simpler |
| Calendar view | Full calendar | MonthCalendar component | Similar |
| Dark mode | Partial | Full system support | Clarisal ahead |
| Audit timeline per entity | Limited | AuditTimeline component | Clarisal ahead |
| Holiday calendar by location | Single calendar | Location-specific calendars | Clarisal ahead |
| On-duty policy management | Nested under travel | Dedicated page | Clarisal ahead |

---

## 6. Prioritized Recommendations

### 🔴 Critical — Fix Before Production

| # | Issue | Location | Action |
|---|-------|----------|--------|
| C1 | **Credential exposure risk** | `.env`, `.gitignore`, `settings/base.py` | Audit git history for `.env`; rotate SECRET_KEY, AWS keys, DB password if ever committed |
| C2 | **FIELD_ENCRYPTION_KEY defaults to empty** → falls back to SECRET_KEY | `settings/base.py:161`, `common/security.py:19` | Make required in production settings; add startup assertion; document key rotation strategy |
| C3 | **Silent decryption failure** returns empty string with no log | `common/security.py:40` | Add `logger.error(...)` on `InvalidToken` before returning `''` |
| C4 | **Bare `except Exception: pass`** on dashboard data path | `employees/services.py:621` | Replace with specific exception + `logger.exception(...)` |
| C5 | **Approval workflow builder UI incomplete** | `org/ApprovalWorkflowsPage.tsx` | Implement rule-matching and multi-stage configuration UI matching the backend model |

### 🟠 High Priority — Next Sprint

| # | Issue | Location | Action |
|---|-------|----------|--------|
| H1 | **Attendance module missing entirely** | — | Design and implement: check-in/out model, daily attendance records, basic attendance report |
| H2 | **N+1 query on employee dashboard** | `employees/services.py:~600` | Add `.select_related('approval_run')` to approvals queryset |
| H3 | **No required field indicators** on any form | All form pages | Add asterisk indicators; update `.field-label` CSS |
| H4 | **Browser-native confirm dialogs for destructive actions** | `OrganisationDetailPage.tsx:150, 227` | Replace with custom `ConfirmDialog` component (extend `ApprovalDecisionDialog`) |
| H5 | **No `onError` handlers on mutations** | `useOrgAdmin.ts`, `useEmployeeSelf.ts` | Add `onError: (e) => toast.error(getErrorMessage(e))` to all `useMutation` calls |
| H6 | **No reports module** | — | Implement 10 core reports: headcount, leave usage, approval turnaround, joiners/leavers, document compliance |
| H7 | **RBAC has only 3 flat roles** | `accounts/models.py`, permission classes | Design HR_MANAGER and DEPT_MANAGER roles; add department-scoped employee visibility |
| H8 | **No API versioning** | `calrisal/urls.py` | Add `/api/v1/` prefix; document versioning policy |

### 🟡 Medium Priority — Next Quarter

| # | Issue | Location | Action |
|---|-------|----------|--------|
| M1 | **No comp-off management** | `timeoff/models.py` | Add `CompOffPolicy`, `CompOffBalance` models; link to on-duty and overtime |
| M2 | **No leave encashment** | `timeoff/models.py` | Add encashment model and payout calculation for exit processing |
| M3 | **No approval escalation or delegation** | `approvals/models.py` | Add `ApprovalEscalationPolicy` and `ApprovalDelegation` models |
| M4 | **No ARIA labels on icon buttons** | Multiple UI components | Add `aria-label` to all icon-only `<button>` elements |
| M5 | **Employee code format hardcoded** | `employees/services.py:~82` | Add `Organisation.employee_code_format` field; generate codes from template |
| M6 | **Onboarding form UX issues** | `employee/OnboardingPage.tsx` | Fix textarea→input for address, add required indicators, add debounced auto-save |
| M7 | **No `MAX_PAGE_SIZE`** | `settings/base.py:140` | Add `'MAX_PAGE_SIZE': 100` to DRF pagination config |
| M8 | **Error response collapses to single error** | `accounts/exceptions.py:36` | Return field-level error dict; update `FieldErrorText` to handle multiple errors |
| M9 | **No document expiry tracking** | `documents/models.py` | Add `expiry_date` to `Document`; add Celery periodic task for expiry alerts |
| M10 | **Mobile table layout for wide tables** | `EmployeesPage.tsx`, `OrganisationDetailPage.tsx` | Add responsive column collapse on small screens |
| M11 | **No breadcrumbs** | All pages | Add `Breadcrumb` component to `PageHeader`; wire up in all nested routes |
| M12 | **AuditLog missing old/new value diff** | `audit/models.py` | Add `old_value` and `new_value` JSONFields to `AuditLog` |
| M13 | **`console.error` in production** | `AppErrorBoundary.tsx` | Gate with `if (import.meta.env.DEV)` |

### 🟢 Nice to Have — Backlog

| # | Feature | Notes |
|---|---------|-------|
| N1 | Performance management module | Appraisal cycles, goal tracking, rating templates |
| N2 | Leave forecasting | Show projected balance for next 12 months |
| N3 | Org chart visualization | Tree rendering from `reporting_to` FK using D3 or react-flow |
| N4 | Charts and data visualization | Integrate Recharts/Chart.js for department distribution, leave trends |
| N5 | Custom report builder | Drag-and-drop with field selection, grouping, filters, CSV export |
| N6 | SSO / SAML 2.0 | django-saml2 or similar for enterprise identity federation |
| N7 | Notification center | Bell icon in nav, in-app notification model, read tracking |
| N8 | Email delivery for notices | Celery task sending notice to targeted audience |
| N9 | Document folder structure | Folder/category model; folder-based frontend UI |
| N10 | Bulk employee import | CSV/Excel upload with validation + preview step |
| N11 | Onboarding task checklists | `OnboardingTask` model with templates, assignment, completion tracking |
| N12 | API keys for integrations | `APIKey` model with scoped permissions; HMAC authentication |
| N13 | DPDP/GDPR readiness | Consent tracking, data export, right-to-erasure workflow |
| N14 | LoginPage deduplication | Extract shared `AuthForm` component between LoginPage and ControlTowerLoginPage |
| N15 | Frontend unit tests | Add Vitest + React Testing Library for hooks and components |

---

## Appendix A: Dead Code & TODO Catalogue

### Intentional No-Ops

- `backend/apps/organisations/signals.py` — file exists with a comment declaring that audit logging is handled in services.py; no active signal handlers. Can be removed or retained as documentation.

### `# noqa: BLE001` Sites (Acknowledged Bare-Except Locations)

| File | Line | Context |
|------|------|---------|
| `accounts/views.py` | 206 | Password reset validation — `# noqa: BLE001 - keep response shape compact` |
| `accounts/views.py` | 231 | Password reset confirm — same pattern |
| `employees/services.py` | 621 | Dashboard data aggregation — followed by bare `pass` |
| `timeoff/views.py` | 78 | Holiday calendar list |
| `timeoff/views.py` | 93 | Holiday calendar detail |

### Duplicate Code

- `auth/LoginPage.tsx` and `auth/ControlTowerLoginPage.tsx` share identical form state management, submission logic, and field structure. Only the `variant` prop to `AuthShell` differs.

### Full TODO / FIXME Scan

Run the following to generate a complete catalogue before sprint planning:
```bash
grep -rn "TODO\|FIXME\|HACK\|noqa: BLE001" backend/ frontend/src/
```

---

## Appendix B: Security Configuration Checklist

| Item | Status | Notes |
|------|--------|-------|
| CSRF protection | Enabled | X-CSRFToken header wired in Axios interceptor (`lib/api.ts`) |
| Session cookie HttpOnly | Enabled | `SESSION_COOKIE_HTTPONLY=True` |
| Session cookie SameSite | Lax | Consider upgrading to `Strict` for HRMS data sensitivity |
| SQL injection | Safe | ORM throughout; no raw SQL found |
| XSS | Safe | No `dangerouslySetInnerHTML`, no code execution functions found |
| CORS | Whitelist | Origin-based whitelist from env; not open to wildcard |
| Rate limiting | Configured | Per-endpoint throttle scopes (login: 5/min, invites: 30/hr) |
| SECRET_KEY | Risk | Verify not in git history; has safe dev-default string |
| FIELD_ENCRYPTION_KEY | **Critical** | Defaults to `''` → silently falls back to SECRET_KEY |
| AWS keys | Risk | Verify not in git history |
| HTTPS redirect | Unknown | `SECURE_SSL_REDIRECT` not in settings — assume reverse proxy handles |
| HSTS | Unknown | `SECURE_HSTS_SECONDS` not configured |
| JWT in localStorage | N/A | Session-based auth; no JWT stored in localStorage |
| Audit logging | Partial | Auth events + service mutations logged; missing access logs and field-level diffs |
| Password reset token expiry | Implemented | `PasswordResetToken` model with expiry field |
| Invite token throttling | Adequate | 30/hr validate, 10/hr accept |
| Encryption key fallback | **Critical** | Falls back to `SECRET_KEY`; key rotation destroys all encrypted data silently |

---

*End of Report — Clarisal HRMS Audit, April 1, 2026*
