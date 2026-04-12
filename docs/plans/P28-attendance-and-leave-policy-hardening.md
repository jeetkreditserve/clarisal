# P28 — Attendance & Leave Policy Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Close the two medium-severity attendance and leave gaps found in the v4 audit: unify the two coexisting geo-fence systems so web and mobile punch enforce the same rules, and add CAPPED carry-forward enforcement that was missing from the leave lapse task.

**Architecture:** Geo-fence unification is a service-layer change — `record_employee_punch` in `attendance/services.py` currently reads from `AttendancePolicy.allowed_geo_sites` (a legacy JSON field). The fix migrates it to read from `GeoFencePolicy` table introduced in P20. No new models are required; a migration adds a deprecation comment on the old field. Leave lapse CAPPED enforcement is covered in P27 T4 — this plan handles the geo-fence work only. The LWP deduction base (Gap #22) is documented as a design decision with no code change.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · React 19 · TypeScript · pytest

---

## Audit Findings Addressed

- Two geo-fence systems coexist: web punch uses legacy `AttendancePolicy.allowed_geo_sites` JSON field; mobile punch uses `GeoFencePolicy` table — same office can block mobile but not web browser (Gap #4 — Medium)
- LWP deduction uses gross pay base, not basic salary — document as design choice (Gap #22 — Info)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/attendance/services.py` | Modify | `record_employee_punch` reads from `GeoFencePolicy` table instead of `allowed_geo_sites` JSON |
| `backend/apps/attendance/models.py` | Modify | Deprecate `allowed_geo_sites` field (add deprecation comment; do not remove yet — data migration needed first) |
| `backend/apps/attendance/migrations/XXXX_deprecate_allowed_geo_sites.py` | Create | Mark `allowed_geo_sites` nullable and blank; add db_comment |
| `backend/apps/attendance/tests/test_services.py` | Modify | Geo-fence enforcement test for web punch via `GeoFencePolicy` |
| `backend/apps/attendance/tests/test_views.py` | Modify | Web punch geo-block API test |
| `docs/decisions/ADR-001-lwp-deduction-base.md` | Create | Architecture Decision Record documenting gross-pay LWP deduction as an explicit choice |

---

## Task 1: Audit the Two Geo-Fence Systems

> **Context (Gap #4 — Medium):** `MyAttendancePunchInView` (attendance/views.py) calls `record_employee_punch()` which currently checks `attendance_policy.allowed_geo_sites` (a JSON list of `{lat, lng, radius}` dicts). `MyMobilePunchView` calls `record_mobile_punch()` which checks `GeoFencePolicy` objects tied to the employee's office location. The enforcement logic (haversine, WARN vs BLOCK) lives in `GeoFencePolicy` but is absent from the web punch path.

- [x] Read `attendance/services.py` — locate `record_employee_punch` and identify the geo-fence check block.
- [x] Read `attendance/models.py` — confirm `GeoFencePolicy` model fields: `office_location`, `lat`, `lng`, `radius_meters`, `enforcement_mode` (WARN/BLOCK).
- [x] Read `AttendancePolicy.allowed_geo_sites` field definition — confirm it is a `JSONField` with no FK relationship.
- [x] Confirm that `record_mobile_punch()` already uses `GeoFencePolicy` correctly (it should per P20).
- [x] Document any data currently stored in `allowed_geo_sites` — determine if a data migration is needed to populate `GeoFencePolicy` records from it.

## Task 2: Unify Web Punch to Use GeoFencePolicy

- [x] In `attendance/services.py`, replace the `allowed_geo_sites` geo-fence check in `record_employee_punch` with the same `GeoFencePolicy` lookup used by `record_mobile_punch`:

```python
# BEFORE (web punch path):
geo_sites = getattr(attendance_policy, 'allowed_geo_sites', None) or []
if geo_sites:
    # haversine check against list of dicts
    ...

# AFTER:
from apps.locations.models import GeoFencePolicy
geo_policies = GeoFencePolicy.objects.filter(
    office_location=employee.office_location,
    is_active=True,
)
for policy in geo_policies:
    distance = haversine(lat, lng, policy.lat, policy.lng)
    if distance > policy.radius_meters:
        if policy.enforcement_mode == GeoFencePolicyMode.BLOCK:
            raise GeoFenceViolationError(
                f"Punch location is {distance:.0f}m from office; required within {policy.radius_meters}m"
            )
        elif policy.enforcement_mode == GeoFencePolicyMode.WARN:
            # Still allow; flag on punch record
            punch_flags.append('GEO_FENCE_WARNING')
```

- [x] If `haversine` is already a shared utility (used by `record_mobile_punch`), import from the existing location. Do not duplicate.
- [x] Add a `geo_fence_warning` boolean field (or use an existing `flags` JSON field if present) on the punch record model to persist the WARN state.
- [x] Ensure that when `employee.office_location` is `None` (remote employees), geo-fence check is skipped entirely — no `GeoFencePolicy` lookup should run for locationless employees.

## Task 3: Data Migration from allowed_geo_sites → GeoFencePolicy

- [x] Write a management command `migrate_geo_sites_to_policies` that reads all `AttendancePolicy` records with non-empty `allowed_geo_sites` and creates corresponding `GeoFencePolicy` objects:

```python
for policy in AttendancePolicy.objects.exclude(allowed_geo_sites=[]):
    for site in (policy.allowed_geo_sites or []):
        GeoFencePolicy.objects.get_or_create(
            office_location=policy.location,  # or the related location FK
            lat=site['lat'],
            lng=site['lng'],
            defaults={
                'radius_meters': site.get('radius', 200),
                'enforcement_mode': GeoFencePolicyMode.BLOCK,
                'is_active': True,
            }
        )
```

- [x] Only run this command if `allowed_geo_sites` data exists. Log how many policies were created / already existed.
- [x] After migration, set `allowed_geo_sites = []` (empty) on all `AttendancePolicy` records to avoid dual-enforcement.
- [x] Create a Django migration that makes `allowed_geo_sites` nullable with `blank=True, default=list` and adds a `db_comment` explaining it is deprecated.

## Task 4: Deprecate allowed_geo_sites Field

- [x] In `attendance/models.py`, add a deprecation comment above `allowed_geo_sites`:

```python
# DEPRECATED (P28): Use GeoFencePolicy table (locations app) instead.
# This field is kept for historical reference only. Do not write to it.
# Migration: management command `migrate_geo_sites_to_policies` copies data.
# Planned removal: after 2 sprints of monitoring.
allowed_geo_sites = models.JSONField(
    default=list,
    blank=True,
    null=True,
    help_text='DEPRECATED: Use GeoFencePolicy table via office_location FK.',
)
```

- [x] Do NOT remove the field yet — removal requires a separate migration after verifying no active read paths remain.
- [x] Add a `DeprecationWarning` log call in `record_employee_punch` if `allowed_geo_sites` is non-empty (means someone is still writing to it):

```python
if getattr(attendance_policy, 'allowed_geo_sites', None):
    logger.warning("deprecated_geo_fence_field_still_populated",
                   policy_id=attendance_policy.pk)
```

## Task 5: Tests

- [x] Add tests in `attendance/tests/test_services.py`:
  - Web punch from inside geo-fence → punch created, no warning flag
  - Web punch from outside geo-fence with BLOCK policy → `GeoFenceViolationError` raised
  - Web punch from outside geo-fence with WARN policy → punch created with `geo_fence_warning=True`
  - Employee with `office_location=None` → geo-fence check skipped, punch created
  - Employee with no `GeoFencePolicy` records for their office → punch created (no policies = no enforcement)
- [x] Add tests in `attendance/tests/test_views.py`:
  - `POST /api/v1/self/attendance/punch-in/` with coordinates outside BLOCK fence → HTTP 400
  - `POST /api/v1/self/attendance/punch-in/` with coordinates outside WARN fence → HTTP 200, `geo_fence_warning: true` in response
  - Confirm that mobile punch and web punch now produce identical outcomes for the same location violation scenario

## Task 6: Document LWP Deduction Base as Architecture Decision

> **Gap #22 (Info):** The current implementation deducts LWP from gross pay (not basic salary). Most Indian payroll systems (Keka, Greythr) use basic salary as the LWP deduction base. This is a legitimate design choice but should be explicit.

- [x] Create `docs/decisions/ADR-001-lwp-deduction-base.md`:

```markdown
# ADR-001: LWP Deduction Base — Gross Pay vs Basic Salary

**Status**: Accepted
**Date**: [implementation date]

## Context
When an employee has unpaid leave, the LWP deduction can be calculated as:
(a) `(gross_monthly / working_days_in_month) × lwp_days` — gross-pay basis
(b) `(basic_monthly / working_days_in_month) × lwp_days` — basic-salary basis

Clarisal currently uses (a). Keka, Greythr, and most statutory guidance default to (b).

## Decision
Retain gross-pay basis as the default. Add a per-organisation flag
`lwp_deduction_basis` (GROSS / BASIC) with default GROSS so that orgs
requiring basic-salary basis can configure it without code changes.

## Consequences
- No immediate code change required.
- `lwp_deduction_basis` flag to be added when org settings are extended (future sprint).
- Document this in the payroll configuration guide.
```

- [x] Add `lwp_deduction_basis` as a commented-out field in `Organisation` settings model for future implementation — do NOT implement the full feature in this plan; just leave the ADR and the migration hook.
