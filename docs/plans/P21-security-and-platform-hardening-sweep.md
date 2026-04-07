# P21 — Security & Platform Hardening Sweep

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining security and platform-operation gaps after `P01` and `P12`: magic-byte upload validation, decrypt failure logging, remaining date-input/platform polish gaps, compression config, and stale-code cleanup across touched subsystems.

**Architecture:** Keep security checks closest to ingress points: file validation in `documents`, decryption observability in `common/security`, platform-serving behavior in `frontend/nginx.conf`, and UI consistency in the existing shared component layer.

**Tech Stack:** Django 4.2 · python-magic · pytest · React 19 · TypeScript · nginx

---

## Audit Findings Addressed

- File upload lacks magic-byte content validation
- Decrypt failure silently returns empty string
- Audit and reports pages still use raw date input
- Nginx missing gzip compression
- Stale or unused code needs to be cleaned as remediation lands

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/documents/services.py` | Modify | Add binary content validation |
| `backend/apps/documents/tests/test_services.py` | Modify | Upload validation coverage |
| `backend/apps/common/security.py` | Modify | Structured decrypt-failure logging |
| `backend/apps/common/tests/test_security.py` | Create | Security helper tests |
| `frontend/src/pages/org/AuditPage.tsx` | Modify | Replace native date input |
| `frontend/src/pages/org/ReportsPage.tsx` | Modify | Replace native date input |
| `frontend/src/components/ui/AppDatePicker.tsx` | Modify if needed | Reuse shared date picker behavior |
| `frontend/nginx.conf` | Modify | Enable compression and document redirect expectations |

---

## Task 1: Add Magic-Byte Upload Validation

- [ ] Validate file signatures from content bytes, not just extension and browser-reported MIME type.
- [ ] Reject mismatched files before S3 upload and return actionable validation errors.
- [ ] Add tests for valid PDF/JPEG/PNG uploads and disguised executable or archive payloads.

## Task 2: Add Decrypt Failure Observability

- [ ] Log `InvalidToken` failures with structured metadata that can be correlated without leaking sensitive field values.
- [ ] Keep the safe empty-string fallback only if product behavior still requires it, but never fail silently again.
- [ ] Add tests covering corrupt ciphertext, wrong-key scenarios, and non-value inputs.

## Task 3: Finish Shared Date-Picker Migration

- [ ] Replace raw date inputs in audit and reports screens with the shared date-picker component.
- [ ] Keep locale, timezone, and keyboard-access behavior consistent with existing app controls.
- [ ] Add or extend UI tests so these pages stop being called out for inconsistent input patterns.

## Task 4: Add Compression, CSP, and Platform Serving Guards

- [x] Enable `gzip` for static assets and JSON responses in `frontend/nginx.conf`.
- [ ] Add a `Content-Security-Policy` header in `frontend/nginx.conf`: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'`. Adjust `connect-src` to include the S3 bucket origin for document downloads.
- [ ] Document or implement HTTPS redirect behavior explicitly so deployment assumptions are visible.
- [ ] Verify that compression does not break already-generated static assets or API proxying.

## Task 5: Cleanup and Final Hardening Sweep

- [ ] Remove dead helper code, duplicate validators, and stale comments introduced by earlier partial fixes.
- [ ] Run lint, typecheck, and coverage checks after cleanup so no unused code or imports remain in touched modules.
- [ ] Capture before/after evidence for security behavior changes for the next audit pass.

## Task 6: Add Sentry Integration and Structured Logging

> **Audit v3 finding (Gap #26, §4.3):** No Sentry or structured JSON logging exists. Production logs at WARNING level to console with no aggregation path (CloudWatch, Datadog).

- [ ] Add `sentry-sdk[django,celery]` to `requirements.txt`.
- [ ] Configure Sentry DSN in `settings/production.py` via `environ.Env`; set `traces_sample_rate`, `environment`, and `release` (from a `GIT_SHA` env var).
- [ ] Add `structlog` to `requirements.txt`; configure it in `settings/base.py` to emit JSON in production and human-readable in development.
- [ ] Replace bare `logging.getLogger` calls in `payroll/services.py` and `organisations/tasks.py` with structlog's `get_logger` so structured key-value context (org_id, run_id, employee_id) is included in log records.
- [ ] Add a `HealthCheckView` at `/api/health/` returning `{"status": "ok", "version": GIT_SHA}` — used by load balancers and uptime monitors.
- [ ] Cover Sentry init (mock SDK) and health endpoint with tests.

## Task 7: Migrate StatutoryFilingBatch Artifact to S3

> **Audit v3 finding (Gap #11, §4.1 and §6):** `StatutoryFilingBatch.artifact_binary` stores binary filing content (ECR CSVs, Form 24Q XML, Form 16 PDFs) directly in PostgreSQL. Large Form 24Q XMLs will bloat the DB. Production already uses S3 for all other media.

- [ ] Add `artifact_s3_key = models.CharField(max_length=500, blank=True)` to `StatutoryFilingBatch`.
- [ ] Write a data migration to upload existing `artifact_binary` blobs to S3 under `statutory-filings/<org_id>/<batch_id>/<filename>` and populate `artifact_s3_key`.
- [ ] Update filing generators (`ecr.py`, `esi.py`, `form24q.py`, `form16.py`, `professional_tax.py`) to write to S3 and set `artifact_s3_key` rather than `artifact_binary`.
- [ ] Update the filing download endpoint to generate a time-limited presigned S3 URL instead of serving binary from DB.
- [ ] After verifying the migration in staging, remove the `artifact_binary` field in a follow-up migration.
- [ ] Cover S3 upload, presigned URL generation, and download endpoint with tests using mocked S3 (moto).

## Task 8: Payroll Dead Code and Duplication Cleanup

> **Audit v3 finding (Gaps #24–25, §5.1–5.3):** `calculate_professional_tax_monthly` in `statutory.py` is dead code never called in production. `_normalize_decimal` in `services.py` duplicates `normalize_decimal` in `statutory.py`.

- [ ] Remove `calculate_professional_tax_monthly` from `backend/apps/payroll/statutory.py` (verify with `grep -rn calculate_professional_tax_monthly backend/` first).
- [ ] Remove `_normalize_decimal` from `backend/apps/payroll/services.py`; import and use `normalize_decimal` from `statutory` at its call sites.
- [ ] Remove `DEFAULT_TAX_SLABS` fallback constants from `services.py` (lines 106–114) — document with a comment that `seed_statutory_masters` is a deployment prerequisite, or add a startup check.
- [ ] Unify `_fiscal_year_for_period` in `services.py` and `fiscal_year_bounds` in `filings/__init__.py` into a single shared utility in `statutory.py`.
- [ ] Run `ruff check` and `mypy` on all touched payroll modules; fix any new violations introduced.
- [ ] Confirm no test regressions after dead code removal by running the full payroll test suite.
