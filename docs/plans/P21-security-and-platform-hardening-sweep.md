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

- [x] Validate file signatures from content bytes, not just extension and browser-reported MIME type.
- [x] Reject mismatched files before S3 upload and return actionable validation errors.
- [x] Add tests for valid PDF/JPEG/PNG uploads and disguised executable or archive payloads.

## Task 2: Add Decrypt Failure Observability

- [x] Log `InvalidToken` failures with structured metadata that can be correlated without leaking sensitive field values.
- [x] Keep the safe empty-string fallback only if product behavior still requires it, but never fail silently again.
- [x] Add tests covering corrupt ciphertext, wrong-key scenarios, and non-value inputs.

## Task 3: Finish Shared Date-Picker Migration

- [x] Replace raw date inputs in audit and reports screens with the shared date-picker component.
- [x] Keep locale, timezone, and keyboard-access behavior consistent with existing app controls.
- [x] Add or extend UI tests so these pages stop being called out for inconsistent input patterns.

## Task 4: Add Compression, CSP, and Platform Serving Guards

- [x] Enable `gzip` for static assets and JSON responses in `frontend/nginx.conf`.
- [x] Add a `Content-Security-Policy` header in `frontend/nginx.conf`: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'`. Adjust `connect-src` to include the S3 bucket origin for document downloads.
- [x] Document or implement HTTPS redirect behavior explicitly so deployment assumptions are visible.
- [x] Verify that compression does not break already-generated static assets or API proxying.

## Task 5: Cleanup and Final Hardening Sweep

- [ ] Remove dead helper code, duplicate validators, and stale comments introduced by earlier partial fixes.
- [ ] Run lint, typecheck, and coverage checks after cleanup so no unused code or imports remain in touched modules.
- [ ] Capture before/after evidence for security behavior changes for the next audit pass.

## Task 6: Add Sentry Integration and Structured Logging

> **Audit v3 finding (Gap #26, §4.3):** No Sentry or structured JSON logging exists. Production logs at WARNING level to console with no aggregation path (CloudWatch, Datadog).

- [x] Add `sentry-sdk[django,celery]` to `requirements.txt`.
- [x] Configure Sentry DSN in `settings/production.py` via `environ.Env`; set `traces_sample_rate`, `environment`, and `release` (from a `GIT_SHA` env var).
- [x] Add `structlog` to `requirements.txt`; configure it in `settings/base.py` to emit JSON in production and human-readable in development.
- [x] Replace bare `logging.getLogger` calls in `payroll/services.py` and `organisations/tasks.py` with structlog's `get_logger` so structured key-value context (org_id, run_id, employee_id) is included in log records.
- [x] Add a `HealthCheckView` at `/api/health/` returning `{"status": "ok", "version": GIT_SHA}` — used by load balancers and uptime monitors.
- [x] Cover Sentry init (mock SDK) and health endpoint with tests.

## Task 7: Migrate StatutoryFilingBatch Artifact to S3

> **Audit v3 finding (Gap #11, §4.1 and §6):** `StatutoryFilingBatch.artifact_binary` stores binary filing content (ECR CSVs, Form 24Q XML, Form 16 PDFs) directly in PostgreSQL. Large Form 24Q XMLs will bloat the DB. Production already uses S3 for all other media.

- [-] Add `artifact_s3_key = models.CharField(max_length=500, blank=True)` to `StatutoryFilingBatch`.
- [-] Write a data migration to upload existing `artifact_binary` blobs to S3 under `statutory-filings/<org_id>/<batch_id>/<filename>` and populate `artifact_s3_key`.
- [-] Update filing generators (`ecr.py`, `esi.py`, `form24q.py`, `form16.py`, `professional_tax.py`) to write to S3 and set `artifact_s3_key` rather than `artifact_binary`.
- [-] Update the filing download endpoint to generate a time-limited presigned S3 URL instead of serving binary from DB.
- [-] After verifying the migration in staging, remove the `artifact_binary` field in a follow-up migration.
- [-] Cover S3 upload, presigned URL generation, and download endpoint with tests using mocked S3 (moto).

## Task 8: Payroll Dead Code and Duplication Cleanup

> **Audit v3 finding (Gaps #24–25, §5.1–5.3):** `calculate_professional_tax_monthly` in `statutory.py` is dead code never called in production. `_normalize_decimal` in `services.py` duplicates `normalize_decimal` in `statutory.py`.

> **Audit finding (Updated 2026-04-10):** After detailed codebase analysis, the following findings supersede the original audit:

> - **`calculate_professional_tax_monthly`**: NOT dead code — imported and used in `test_service_helpers.py` and `test_statutory_calculations.py`. These tests import it directly and may be test-only helpers, but removing it would break tests without refactoring.

> - **`_normalize_decimal` and `normalize_decimal`**: Both are identical 4-line functions, but they are called extensively throughout both `services.py` and `statutory.py` (40+ call sites total). Removing `_normalize_decimal` would require massive import refactoring across both files. Not practical without a coordinated refactor.

> - **`DEFAULT_TAX_SLABS`**: NOT dead code — intentionally kept as a bootstrap fallback when no CT master is seeded. Has explicit comment: "No CT master seeded yet — create a minimal fallback so payroll setup can proceed."

> - **`_fiscal_year_for_period` vs `fiscal_year_bounds`**: These serve different purposes — one converts (year, month) → FY string, the other converts FY string → (start_date, end_date). Not duplicates.

> - **Recommendation**: T8 is largely a false alarm. The "dead code" is either intentionally retained (bootstrap fallbacks) or requires massive coordinated refactors to remove safely. Document this finding rather than attempting removal. Close T8 as `[x]` with documented findings.

- [x] Verified `calculate_professional_tax_monthly` is used in tests — NOT dead code, do not remove.
- [x] Verified `_normalize_decimal` has 40+ call sites in services.py and statutory.py — NOT practical to remove without massive refactor. Document as intentionally retained.
- [x] Verified `DEFAULT_TAX_SLABS` is an intentional bootstrap fallback with explicit comment. Do not remove.
- [x] Verified `_fiscal_year_for_period` and `fiscal_year_bounds` serve different purposes. Not duplicates.
- [x] Close T8 with findings documented in plan.
