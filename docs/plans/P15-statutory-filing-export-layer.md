# P15 — Statutory Filing Export Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the statutory filing export layer missing from the audit: PF ECR, ESI challan/export, Form 24Q quarterly return data, PT state-return export scaffolding, and Form 16 document outputs beyond raw JSON.

**Architecture:** Build filing exports as versioned, testable generators under `backend/apps/payroll/filings/` rather than embedding format logic in views. Persist every generated filing as an auditable batch with metadata, source payroll runs, and downloadable artifacts.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · pytest · CSV/text export · PDF generation

---

## Audit Findings Addressed

- ECR export missing
- ESI challan generation missing
- Form 24Q / TDS return export missing
- PT state-wise return export missing
- Form 16 PDF/XML missing

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/payroll/models.py` | Modify | Add filing batch metadata |
| `backend/apps/payroll/filings/__init__.py` | Create | Filing package |
| `backend/apps/payroll/filings/ecr.py` | Create | PF ECR generator |
| `backend/apps/payroll/filings/esi.py` | Create | ESI challan/export generator |
| `backend/apps/payroll/filings/form24q.py` | Create | Quarterly TDS return dataset generator |
| `backend/apps/payroll/filings/professional_tax.py` | Create | PT return generator scaffold |
| `backend/apps/payroll/filings/form16.py` | Create | PDF/XML output from existing Form 16 data |
| `backend/apps/payroll/services.py` | Modify | Filing orchestration entry points |
| `backend/apps/payroll/views.py` | Modify | Filing export endpoints |
| `backend/apps/payroll/org_urls.py` | Modify | Register export routes |
| `backend/apps/payroll/tests/test_filings.py` | Create | Generator coverage |
| `backend/apps/payroll/tests/test_views.py` | Modify | Endpoint coverage |
| `frontend/src/lib/api/org-admin.ts` | Modify | Export actions |
| `frontend/src/pages/org/PayrollPage.tsx` | Modify | Filing export controls |
| `frontend/src/pages/org/ReportsPage.tsx` | Modify | Report/download UX |

---

## Task 1: Create the Filing Batch Domain

- [x] Add a `StatutoryFilingBatch` model with filing type, period, organisation, source payroll runs, generation status, checksum, and file storage metadata.
- [x] Ensure every export path is reproducible: same inputs must generate identical serialized rows unless configuration changes.
- [x] Add audit-log hooks for generate, regenerate, download, and cancel operations.

## Task 2: Implement PF ECR Export

- [x] Convert finalized payroll run data into ECR-ready row structures with UAN, wage, EPS, EPF, and admin-charge columns.
- [x] Validate mandatory employee identifiers and surface actionable exceptions instead of producing partial files silently.
- [x] Add golden-file tests using representative employee fixtures and exact text/CSV assertions.

## Task 3: Implement ESI Challan / Monthly Export

- [x] Generate ESI monthly contribution export rows from persisted ESI contribution-period logic introduced in `P14`.
- [x] Include employee and employer contribution totals, insured-person identifiers, and period metadata.
- [x] Add tests for threshold edges and mid-period eligibility continuation.

## Task 4: Implement Form 24Q Quarterly Export

- [x] Aggregate finalized payslip and TDS data into quarter-level return rows.
- [x] Add validation for PAN completeness, challan grouping, and quarter cutoffs.
- [x] Produce a stable, machine-readable export format first; add any human-readable summary sheet only after the structured dataset is correct.

## Task 5: Implement PT Return and Form 16 Document Outputs

- [x] Add a PT-return generator that uses the state master data from `P14` and fails fast for states without a defined export template.
- [x] Upgrade Form 16 from JSON-only output to downloadable PDF and structured machine-readable export.
- [x] Keep template/rendering code separate from tax calculation code so statutory math stays testable.

## Task 6: Wire APIs, UI, and Operational Guardrails

- [x] Add org-admin export endpoints grouped by filing type and period.
- [x] Show validation blockers before download when mandatory employee or organisation metadata is missing.
- [x] Provide clear UI status for `ready`, `blocked`, `generated`, and `superseded` filing batches.

## Task 7: Cleanup and Full Export Verification

- [x] Remove any duplicate export formatting helpers left in report or payroll views.
- [x] Add API, service, and generator tests to fully exercise changed filing modules.
- [x] Store fixture samples under tests so future audits can compare generated files against expected statutory shapes.
