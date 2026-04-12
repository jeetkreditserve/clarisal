# P29 — Security, Dependencies & Code Quality

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all security vulnerabilities (Pillow CVE, Django behind, missing security headers), fix the `ensure_default_document_types` hot-path write antipattern, add per-org error isolation to Celery tasks, and clean up the `__import__()` antipattern and `soft_delete()` bypass in services. All changes are surgical with no architectural impact.

**Architecture:** Dependency upgrades are `requirements.txt` changes with a test suite gate. Settings changes are in `base.py`. The document-types hot-path fix adds a cache guard. Celery task reliability fixes add try/except + retry decorators. Code quality fixes are direct replacements in existing files.

**Tech Stack:** Django 5.2 LTS · DRF · PostgreSQL · Celery · Redis · pytest

---

## Audit Findings Addressed

- Pillow 10.4.0 has CVE-2024-28219 (Gap #6 — Low–Medium)
- Django 4.2.16 behind 4.2.20 (Gap #7 — Low)
- Non-SSL security headers only in production.py, not base.py (Gap #8 — Low)
- `ensure_default_document_types()` issues 33 `update_or_create` on every document type list API call (Gap #17 — Medium)
- `aggregate_daily_usage_stats` no per-org error isolation (Gap #18 — Medium)
- `generate_tenant_data_export` task no retry policy (Gap #19 — Low)
- `__import__()` antipattern in serializers (7 locations) (Gap #20 — Low)
- `soft_delete()` method bypassed in 4 service functions (Gap #21 — Low)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/requirements.txt` | Modify | Upgrade Pillow to 12.2.x, Django to 5.2 LTS |
| `backend/clarisal/settings/base.py` | Modify | Move security headers from production.py |
| `backend/apps/documents/services.py` | Modify | Replace `ensure_default_document_types()` hot-path with cache guard |
| `backend/apps/organisations/tasks.py` | Modify | Per-org try/except in `aggregate_daily_usage_stats`; retry policy on `generate_tenant_data_export` |
| `backend/apps/employees/serializers.py` | Modify | Replace `__import__()` with top-level imports (7 locations) |
| `backend/apps/employees/services.py` | Modify | Replace manual `is_deleted/deleted_at` with `soft_delete()` in 4 functions |
| `backend/apps/documents/tests/test_services.py` | Modify | Cache guard test; hot-path regression test |
| `backend/apps/organisations/tests/test_tasks.py` | Create | Per-org isolation test; retry policy test |
| `backend/apps/common/tests/test_security.py` | Modify | Security header presence tests |

---

## Task 1: Upgrade Pillow and Django

> **Finding (Gap #6, #7):** `Pillow==10.4.0` has CVE-2024-28219 (buffer overflow). `Django==4.2.16` was behind the old LTS line. This branch moves to the current Django 5.2 LTS line and a current Pillow 12.2 patch after dependency-resolution verification.

- [x] In `backend/requirements.txt`, update:

```
# BEFORE:
Django==4.2.16
Pillow==10.4.0

# AFTER:
Django==5.2.13
Pillow==12.2.0
```

- [x] Run `pip install -r requirements.txt` and verify no dependency conflicts with DRF, WeasyPrint, or other packages.
- [x] Run the full backend test suite (`pytest backend/`) to confirm no regressions from the Django patch upgrade.
- [x] Check the Django 4.2.17–4.2.20 release notes for any deprecation warnings that appear in the test output.
- [x] Check the Pillow 11.x migration guide for any breaking API changes in the code base. The main change in Pillow 11 is removal of `ANTIALIAS` constant (renamed to `LANCZOS`) — grep for `ANTIALIAS` usage:

```bash
grep -r "ANTIALIAS" backend/
```

- [x] If `ANTIALIAS` appears, replace with `Image.LANCZOS` (Pillow 10+ alias) or `Image.Resampling.LANCZOS` (Pillow 10+ explicit form).

## Task 2: Move Security Headers to base.py

> **Finding (Gap #8):** `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, and `X_FRAME_OPTIONS = 'DENY'` are only in `settings/production.py`. A staging or CI environment that does not load `production.py` inherits none of these headers.

- [x] In `backend/clarisal/settings/base.py`, add the following settings (they apply in all environments — they do not require HTTPS):

```python
# Security headers — safe in all environments; not HTTPS-specific
SECURE_BROWSER_XSS_FILTER = True          # Adds X-XSS-Protection: 1; mode=block
SECURE_CONTENT_TYPE_NOSNIFF = True        # Adds X-Content-Type-Options: nosniff
X_FRAME_OPTIONS = 'DENY'                  # Adds X-Frame-Options: DENY
```

- [x] In `settings/production.py`, remove these three settings if they are duplicated there (to avoid confusion about where the canonical value lives). Leave the HTTPS-specific settings in `production.py` (`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, etc.).
- [x] Verify Django adds the headers by checking the Django security middleware chain — confirm `django.middleware.security.SecurityMiddleware` is in `MIDDLEWARE` in `base.py`.
- [x] Add tests in `backend/apps/common/tests/test_security.py`:
  - Make a GET request to the health check endpoint via the Django test client
  - Assert `response['X-Content-Type-Options'] == 'nosniff'`
  - Assert `response['X-Frame-Options'] == 'DENY'`

## Task 3: Fix ensure_default_document_types() Hot-Path Write

> **Finding (Gap #17 — Medium):** `documents/services.py:90` — `list_onboarding_document_types` calls `ensure_default_document_types()` which issues `update_or_create` for **all 33 default document types** on every API call. This is a hot-path write that runs on every document type list fetch, causing unnecessary DB writes and lock contention.

- [x] Read `documents/services.py` — locate `ensure_default_document_types()` and `list_onboarding_document_types`.
- [x] Replace the hot-path call with a `cache.get_or_set` guard:

```python
from django.core.cache import cache

def list_onboarding_document_types(organisation):
    # Ensure default types exist — use cache to avoid 33 update_or_create on every read
    cache_key = f"doc_types_seeded:{organisation.pk}"
    if not cache.get(cache_key):
        ensure_default_document_types(organisation)
        cache.set(cache_key, True, timeout=3600)  # Re-check once per hour
    return DocumentType.objects.filter(organisation=organisation, is_active=True)
```

- [x] The cache key is per-organisation so new orgs automatically get their defaults seeded on first access.
- [x] Add a `management/commands/seed_document_types.py` management command that calls `ensure_default_document_types()` for all organisations — this becomes the canonical seeding path for initial setup and org provisioning.
- [x] Update `organisations/services.py` (new org creation flow) to call `seed_document_types` management command or the service function directly after org creation, so new orgs don't rely on the hot-path fallback.
- [x] Add tests in `documents/tests/test_services.py`:
  - First call to `list_onboarding_document_types` → `ensure_default_document_types` called once
  - Second call (cache hit) → `ensure_default_document_types` NOT called again
  - After cache expiry (mock cache miss) → `ensure_default_document_types` called again
  - Performance regression guard: call `list_onboarding_document_types` 10 times; assert DB write count ≤ 33 (first call only)

## Task 4: Add Per-Org Error Isolation to aggregate_daily_usage_stats

> **Finding (Gap #18 — Medium):** `organisations/tasks.py:20–25` — `aggregate_daily_usage_stats` iterates all organisations in a loop with no per-org try/except. One organisation raising an exception (bad state, missing FK, etc.) silently halts all subsequent organisations for that day's aggregation.

- [x] Read `organisations/tasks.py` — locate `aggregate_daily_usage_stats`.
- [x] Wrap the per-org processing block in try/except:

```python
@app.task(bind=True, max_retries=3)
def aggregate_daily_usage_stats(self):
    logger = structlog.get_logger()
    orgs = Organisation.objects.filter(is_active=True)
    failed_orgs = []

    for org in orgs.iterator():
        try:
            _aggregate_org_stats(org)
        except Exception as exc:
            logger.error(
                "usage_stats_aggregation_failed",
                org_id=str(org.pk),
                org_name=org.name,
                error=str(exc),
                exc_info=True,
            )
            failed_orgs.append(str(org.pk))

    if failed_orgs:
        logger.warning(
            "usage_stats_partial_failure",
            failed_count=len(failed_orgs),
            failed_org_ids=failed_orgs,
        )
```

- [x] Extract the per-org logic into a private `_aggregate_org_stats(org)` function to keep the task body clean.
- [x] Add tests in `organisations/tests/test_tasks.py`:
  - One org raises `ValueError` mid-loop → remaining orgs still processed → error logged with org ID
  - All orgs succeed → no error logged
  - Task completes (returns None, does not re-raise) even when some orgs fail

## Task 5: Add Retry Policy to generate_tenant_data_export

> **Finding (Gap #19 — Low):** `generate_tenant_data_export` Celery task has no `bind=True`, no `max_retries`, no `autoretry_for`. A crash (S3 timeout, DB disconnect) is a silent permanent failure — the org admin gets no error and the export never appears.

- [x] Read `organisations/tasks.py` — locate `generate_tenant_data_export`.
- [x] Add retry decorator and failure notification:

```python
@app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def generate_tenant_data_export(self, organisation_id: str, requested_by_user_id: str):
    try:
        # ... existing export logic ...
    except Exception as exc:
        logger.error(
            "tenant_export_failed",
            org_id=organisation_id,
            attempt=self.request.retries,
            error=str(exc),
        )
        raise  # autoretry_for will handle retry
```

- [x] On final failure (after max_retries), update the export record status to `FAILED` so the CT user sees a failure state instead of a forever-pending spinner.
- [x] Add test: task that raises `Exception` on first 2 attempts → retried → succeeds on 3rd attempt → export record is `COMPLETED`.

## Task 6: Replace __import__() with Top-Level Imports in Serializers

> **Finding (Gap #20 — Low):** `employees/serializers.py` lines 550, 570, 588, 606, 647, 662, 690 use `__import__('apps.employees.models', fromlist=[...])` inside `class Meta: model = ...`. The models are already available at module load time — the dynamic import is unnecessary and hides import errors until serializer instantiation.

- [x] Read `employees/serializers.py` to find all 7 `__import__()` occurrences.
- [x] For each occurrence, replace with a reference to the already-imported model. Example:

```python
# BEFORE:
class Meta:
    model = __import__('apps.employees.models', fromlist=['EmergencyContact']).EmergencyContact
    fields = '__all__'

# AFTER:
from apps.employees.models import EmergencyContact  # add to top-level imports if not already there

class Meta:
    model = EmergencyContact
    fields = '__all__'
```

- [x] Verify all 7 models are already imported at the top of the file. If any are missing, add them.
- [x] Run `python manage.py check` to verify no import errors after the change.
- [x] Run the employees test suite (`pytest backend/apps/employees/`) to verify no serializer regressions.

## Task 7: Use soft_delete() in Service Functions

> **Finding (Gap #21 — Low):** Four service functions in `employees/services.py` manually set `record.is_deleted = True; record.deleted_at = now(); record.save()` instead of calling the `SoftDeleteModel.soft_delete()` method that exists on the model (`models.py:122`). This bypasses any signal or hook logic in `soft_delete()`.

- [x] Read `employees/services.py` — locate `delete_emergency_contact`, `delete_family_member`, `delete_education_record`, `delete_bank_account`.
- [x] Read `employees/models.py:122` — confirm `SoftDeleteModel.soft_delete()` signature.
- [x] In each of the four functions, replace manual deletion with:

```python
# BEFORE:
record.is_deleted = True
record.deleted_at = timezone.now()
record.save(update_fields=['is_deleted', 'deleted_at'])

# AFTER:
record.soft_delete()
```

- [x] Verify `soft_delete()` sets both `is_deleted` and `deleted_at` (read the model method before changing).
- [x] Add tests (or verify existing tests cover) that `soft_delete()` is called and the record is not permanently deleted.
