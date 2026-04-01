# Phase 3: Org Admin Module — Design Spec

**Date:** 2026-03-30
**Scope:** Locations, Departments, Employee Management, Document Upload + Verification, Org Dashboard
**Builds on:** Phase 2 (CT module, invitation flow, service-layer pattern)

---

## Goal

Give the Org Admin role a fully functional management interface: configure the org's structure (locations, departments), invite and manage employees, handle document uploads to S3 with a verification workflow, and see a rich dashboard.

---

## Architecture

Same service-layer pattern as Phase 2: `repositories → services → views`. All business logic in `services.py`, querysets in `repositories.py`, HTTP handling in `views.py`. Each app gets its own `serializers.py`, `repositories.py`, `services.py`, and `tests/`.

**Org-scoping rule:** Every repository query filters by `organisation`. Views extract the org from `request.user.organisation` — never from a URL param alone. This prevents cross-org data leakage at the query layer.

**New dependency:** `boto3` for S3 integration (no `django-storages` — direct boto3 client keeps the upload path explicit and testable).

**URL prefix:** All org admin API endpoints live under `/api/org/`.

**Permission classes:** `[IsOrgAdmin, BelongsToActiveOrg]` — both already defined in `apps/accounts/permissions.py`. `IsOrgAdmin` checks the role; `BelongsToActiveOrg` ensures the org is PAID or ACTIVE (prevents access from suspended orgs).

---

## S3 Key Structure

Files are stored with a deterministic path:

```
organisations/{org_slug}/employees/{employee_code}/{doc_type}/{uuid}-{original_filename}
```

**Example:**
```
organisations/acme-corp/employees/EMP001/PAN/a3f2c1d0-pan_card.pdf
```

This makes any document locatable by org, employee, and type without a database lookup.

**Upload:** Proxied through Django (`multipart/form-data` POST → Django → boto3 → S3). File data passes through the server.

**Download:** Presigned GET URL generated at read time (15-minute expiry). The `file_key` stored in the DB is never exposed directly to the client.

**S3 config env vars:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`, `AWS_S3_REGION`. Local dev uses real S3 or MinIO.

---

## Backend Service Layers

### Task 1: Locations Service (`apps/locations/`)

**Files:** `repositories.py`, `services.py`, `serializers.py`, `tests/test_services.py`

**Services:**
- `create_location(organisation, name, address, city, state, country, pincode)` → `OfficeLocation`
- `update_location(location, **fields)` → `OfficeLocation`
- `deactivate_location(location)` — sets `is_active=False`
- `list_locations(organisation)` → queryset (active only by default, `include_inactive` flag)

**Constraints:** `(organisation, name)` unique — raise `ValueError` on duplicate.

---

### Task 2: Departments Service (`apps/departments/`)

**Files:** `repositories.py`, `services.py`, `serializers.py`, `tests/test_services.py`

**Services:**
- `create_department(organisation, name, description)` → `Department`
- `update_department(department, **fields)` → `Department`
- `deactivate_department(department)` — sets `is_active=False`; raises `ValueError` if department has active employees
- `list_departments(organisation)` → queryset

**Constraints:** `(organisation, name)` unique.

---

### Task 3: Locations + Departments API

**Files:** `locations/views.py`, `locations/urls.py`, `departments/views.py`, `departments/urls.py`, `clarisal/urls.py` (add `/api/org/` include), `tests/test_views.py` for each

**Endpoints:**

| Method | URL | Action |
|--------|-----|--------|
| GET | `/api/org/locations/` | List active locations |
| POST | `/api/org/locations/` | Create location |
| PATCH | `/api/org/locations/{id}/` | Update location |
| POST | `/api/org/locations/{id}/deactivate/` | Deactivate |
| GET | `/api/org/departments/` | List active departments |
| POST | `/api/org/departments/` | Create department |
| PATCH | `/api/org/departments/{id}/` | Update department |
| POST | `/api/org/departments/{id}/deactivate/` | Deactivate |

All endpoints require `[IsOrgAdmin, BelongsToActiveOrg]`. Org is always inferred from `request.user.organisation`.

---

### Task 4: Employee Service (`apps/employees/`)

**Files:** `repositories.py`, `services.py`, `serializers.py`, `tests/test_services.py`

**Services:**

`invite_employee(organisation, email, first_name, last_name, designation, employment_type, date_of_joining, department=None, location=None, invited_by)`:
- Revokes any existing pending invitation for this email + org
- Creates `User` (role=EMPLOYEE, is_active=False) via `get_or_create`
- Auto-generates `employee_code` — format `EMP{n:03d}`, incrementing per org (e.g. EMP001, EMP002)
- Creates `Employee` record (status=INVITED) and `EmployeeProfile` stub
- Creates `Invitation` (role=EMPLOYEE) and queues email via Celery (reuses existing `send_invite_email` task)
- Returns `(employee, invitation)`

`update_employee(employee, **fields)` — updates designation, department, location, employment_type, date_of_joining

`terminate_employee(employee, terminated_by)` — sets status=TERMINATED; raises `ValueError` if already terminated

`list_employees(organisation, status=None, search=None)` → queryset with `select_related('user', 'department', 'office_location')`

`get_employee(organisation, pk)` → Employee with full related data

---

### Task 5: Employee API

**Files:** `employees/views.py`, `employees/urls.py`, `tests/test_views.py`

**Endpoints:**

| Method | URL | Action |
|--------|-----|--------|
| GET | `/api/org/employees/` | List employees (paginated, search + status filter) |
| POST | `/api/org/employees/invite/` | Invite new employee |
| GET | `/api/org/employees/{id}/` | Employee detail |
| PATCH | `/api/org/employees/{id}/` | Update employee |
| POST | `/api/org/employees/{id}/terminate/` | Terminate employee |

---

### Task 6: Documents Service (`apps/documents/`)

**Files:** `repositories.py`, `services.py`, `serializers.py`, `tests/test_services.py`, `s3.py` (boto3 client helper)

**`s3.py`** — thin wrapper:
```python
def upload_file(file_obj, key, content_type): ...
def generate_presigned_url(key, expiry=900): ...
def delete_file(key): ...
```

**Services:**

`upload_document(employee, file_obj, original_filename, doc_type, mime_type, file_size, uploaded_by)`:
- Builds S3 key: `organisations/{org_slug}/employees/{employee_code}/{doc_type}/{uuid}-{filename}`
- Uploads to S3 via `s3.upload_file`
- Only creates `Document` DB record after successful upload
- Returns `Document`

`generate_download_url(document)` → presigned GET URL (15 min expiry)

`verify_document(document, reviewed_by)` — sets status=VERIFIED; raises `ValueError` if already verified/rejected

`reject_document(document, reviewed_by, note='')` — sets status=REJECTED; stores note in `document.metadata['rejection_note']`

`list_documents(employee)` → queryset ordered by `-created_at`

**S3 mock in tests:** `@patch('apps.documents.s3.upload_file')` — no real S3 in CI.

---

### Task 7: Documents API

**Files:** `documents/views.py`, `documents/urls.py`, `tests/test_views.py`

**Endpoints:**

| Method | URL | Action |
|--------|-----|--------|
| GET | `/api/org/employees/{id}/documents/` | List employee documents |
| POST | `/api/org/employees/{id}/documents/` | Upload document (`multipart/form-data`) |
| GET | `/api/org/employees/{id}/documents/{doc_id}/download/` | Get presigned download URL |
| POST | `/api/org/employees/{id}/documents/{doc_id}/verify/` | Verify document |
| POST | `/api/org/employees/{id}/documents/{doc_id}/reject/` | Reject document |

Upload request fields: `file` (binary), `document_type` (choice), optional `metadata` (JSON).

---

### Task 8: Org Dashboard Stats Service

**Files:** `organisations/services.py` (add `get_org_dashboard_stats`), `organisations/tests/test_services.py` (extend)

`get_org_dashboard_stats(organisation)` → dict with:
- `total_employees` — all non-terminated employees
- `active_employees` — status=ACTIVE
- `invited_employees` — status=INVITED
- `terminated_employees` — status=TERMINATED
- `by_department` — list of `{department_name, count}` (active employees only)
- `by_location` — list of `{location_name, count}` (active employees only)
- `recent_joins` — employees with `date_of_joining` in last 30 days (up to 10)
- `licence_used` — count of active + invited employees
- `licence_total` — `organisation.licence_count`

Single query where possible using `annotate` + `values`. Dashboard endpoint added to org URLs: `GET /api/org/dashboard/`.

---

## Frontend

**Stack:** React 18, TanStack Query 5, TypeScript, Tailwind CSS v4, axios. Same patterns as Phase 2 CT frontend.

### Task 9: Types + API Layer + Hooks

**Files:**
- `src/types/org.ts` — `Location`, `Department`, `Employee`, `EmployeeProfile`, `Document`, `OrgDashboardStats`
- `src/lib/api/org.ts` — all fetch/mutate functions
- `src/hooks/useLocations.ts`, `usesDepartments.ts`, `useEmployees.ts`, `useOrgDashboard.ts`, `useDocuments.ts`

TypeScript build check (`tsc --noEmit`) confirms no type errors.

---

### Task 10: Org Dashboard (`pages/org/DashboardPage.tsx`)

Replaces placeholder. Layout:
- **Top row:** 4 stat cards — Total Employees, Active, Invited/Pending, Licence Usage (used/total with progress bar)
- **Middle row:** Location breakdown table + Department breakdown table (side by side)
- **Bottom:** Recent Joins list (last 30 days, up to 10 rows)

Skeleton loading states on all sections.

---

### Task 11: Locations + Departments Pages

**`pages/org/LocationsPage.tsx`** — table of locations + inline "Add Location" form at the top. Deactivate button per row. No separate detail page.

**`pages/org/DepartmentsPage.tsx`** — same pattern: table + inline create form, deactivate per row.

Both pages scoped to the logged-in org admin's org (data comes from API, no org ID in URL).

---

### Task 12: Employees List + Invite (`pages/org/EmployeesPage.tsx`)

- Paginated table: name, email, employee code, department, location, status badge, date of joining
- Search bar + status filter dropdown
- "Invite Employee" button opens modal with fields: email, first name, last name, designation, employment type, department (dropdown), location (dropdown), date of joining
- Status badge colours: INVITED=yellow, ACTIVE=green, INACTIVE=gray, TERMINATED=red

---

### Task 13: Employee Detail (`pages/org/EmployeeDetailPage.tsx`)

Two tabs:

**Info tab:**
- Employment card: code, designation, department, location, employment type, date of joining, status
- Profile card: DOB, gender, nationality, emergency contact (read-only; editable by employee in Phase 4)
- "Terminate" button (ACTIVE employees only, with confirm dialog)

**Documents tab:**
- Upload form: file picker + document type dropdown + upload button
- Document list: type, filename, size, status badge (PENDING/VERIFIED/REJECTED), uploaded date
- Per row: Download button (fetches presigned URL) + Verify / Reject action buttons (PENDING only)

---

### Task 14: Wire Org Routes (`routes/index.tsx` + `OrgLayout`)

New routes added to the `ORG_ADMIN` section:
```
/org/dashboard       → OrgDashboardPage
/org/locations       → LocationsPage
/org/departments     → DepartmentsPage
/org/employees       → EmployeesPage
/org/employees/:id   → EmployeeDetailPage
```

`OrgLayout` sidebar updated with nav links to all five routes.

---

## Error Handling

- **Org scoping:** All repository functions take `organisation` as a required argument. Views never trust URL params for org identity.
- **Upload failure:** `upload_document` uploads to S3 first; DB record only written on success. S3 errors surface as `500` with a generic message.
- **Duplicate names:** Location/department name conflicts return `400` with a field error.
- **State guards:** `terminate_employee` and document verify/reject raise `ValueError` on invalid state transitions — views catch and return `400`.
- **Licence cap:** `invite_employee` checks `licence_used < licence_total` before creating — returns `400` with a clear message if at capacity.

---

## Testing Strategy

**Backend:** Each service module has `tests/test_services.py`; each API module has `tests/test_views.py`. S3 calls mocked with `@patch('apps.documents.s3.upload_file')`. All tests run against SQLite in-memory (existing pytest config).

**Frontend:** TypeScript build check (`tsc --noEmit`) after each task as the type-safety gate. No JS unit tests — correctness validated through the typed API layer and backend tests.

---

## Task Summary

| # | Layer | Deliverable |
|---|-------|-------------|
| 1 | Backend | Locations service + tests |
| 2 | Backend | Departments service + tests |
| 3 | Backend | Locations + Departments API + tests |
| 4 | Backend | Employee service + tests |
| 5 | Backend | Employee API + tests |
| 6 | Backend | Documents service + S3 helper + tests |
| 7 | Backend | Documents API + tests |
| 8 | Backend | Org dashboard stats service + API endpoint |
| 9 | Frontend | Types + API layer + hooks |
| 10 | Frontend | Org Dashboard page |
| 11 | Frontend | Locations + Departments pages |
| 12 | Frontend | Employees list + invite modal |
| 13 | Frontend | Employee detail page (Info + Documents tabs) |
| 14 | Frontend | Wire org routes + update OrgLayout sidebar |
