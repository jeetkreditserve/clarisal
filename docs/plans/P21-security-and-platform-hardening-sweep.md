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

## Task 4: Add Compression and Platform Serving Guards

- [ ] Enable `gzip` for static assets and JSON responses in `frontend/nginx.conf`.
- [ ] Document or implement HTTPS redirect behavior explicitly so deployment assumptions are visible.
- [ ] Verify that compression does not break already-generated static assets or API proxying.

## Task 5: Cleanup and Final Hardening Sweep

- [ ] Remove dead helper code, duplicate validators, and stale comments introduced by earlier partial fixes.
- [ ] Run lint, typecheck, and coverage checks after cleanup so no unused code or imports remain in touched modules.
- [ ] Capture before/after evidence for security behavior changes for the next audit pass.
