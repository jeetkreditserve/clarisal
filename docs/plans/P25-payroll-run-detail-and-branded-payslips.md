# P25 — Payroll Run Detail Page & Branded Payslips

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two highest-impact payroll UX gaps from the v3 audit: the payroll run screen shows only aggregate counts with no per-employee drill-down, and payslips are text-only with no branding. This plan delivers a dedicated `PayrollRunDetailPage`, per-employee expandable rows with exception drill-down, a pre-finalization payslip preview, WeasyPrint branded PDF payslip generation with org logo, and the first interaction-level frontend tests for CT payroll pages.

**Architecture:** Extract `PayrollRunDetailPage` as a new route from `PayrollPage`. PDF generation lives in `backend/apps/payroll/filings/payslip_pdf.py`. The frontend test gap for CT pages is addressed with Vitest interaction tests (not Playwright E2E — save that for a later plan).

**Tech Stack:** Django 4.2 · DRF · WeasyPrint · React 19 · TypeScript · Vitest · React Testing Library

---

## Audit Findings Addressed

- Payroll run screen shows no per-employee breakdown before finalization (Gap #5)
- Payslip is text-only — no branded PDF (Gap #6)
- Zero frontend tests for CT pages (§5.4)
- Zero frontend tests for payroll interaction flows (§5.4)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/payroll/serializers.py` | Modify | `PayrollRunItemDetailSerializer` with all computed fields |
| `backend/apps/payroll/views.py` | Modify | Per-run item list endpoint; payslip PDF endpoint |
| `backend/apps/payroll/org_urls.py` | Modify | Register new routes |
| `backend/apps/payroll/filings/payslip_pdf.py` | Create | WeasyPrint PDF renderer |
| `backend/apps/payroll/templates/payroll/payslip.html` | Create | HTML template for payslip PDF |
| `backend/apps/payroll/tests/test_views.py` | Modify | Run item list and PDF download endpoint tests |
| `frontend/src/pages/org/PayrollRunDetailPage.tsx` | Create | Per-employee run breakdown with drill-down |
| `frontend/src/pages/org/PayrollPage.tsx` | Modify | Add "View Details" link per run row; remove inline run-item rendering |
| `frontend/src/lib/api/payroll.ts` | Modify | Run item list and payslip PDF download calls |
| `frontend/src/types/payroll.ts` | Modify | `PayrollRunItem` type with all fields |
| `frontend/src/routes/index.tsx` | Modify | Register `/org/payroll/runs/:id` route |
| `frontend/src/pages/ct/PayrollMastersPage.test.tsx` | Create | CT payroll masters interaction tests |
| `frontend/src/pages/ct/CtOrgPayrollPage.test.tsx` | Create | CT org payroll page interaction tests |
| `frontend/src/pages/org/PayrollPage.test.tsx` | Modify | Add interaction-level tests for run creation and tab switching |

---

## Task 1: Add Per-Run Item List API Endpoint

- [x] Add `PayrollRunItemDetailSerializer` exposing: `employee_id`, `employee_name`, `employee_code`, `gross_salary`, `basic_salary`, `hra`, `special_allowance`, `epf_employee`, `esi_employee`, `professional_tax`, `lwf_employee`, `tds`, `other_deductions`, `net_salary`, `lop_days`, `ot_earnings`, `arrears`, `status`, and a `has_exception` boolean (true if any component is negative or if LOP > 0).
- [x] Add a `GET /api/org/payroll/runs/<run_id>/items/` endpoint with pagination (`PageNumberPagination`, page size 50) and filters: `?employee=<id>`, `?has_exception=true`.
- [x] Ensure the endpoint respects the org tenancy boundary — only items for the requesting org's pay run are returned.
- [x] Add tests in `test_views.py` covering: list returns correct employee items, pagination works, `has_exception` filter returns only flagged items, cross-org access is blocked.

## Task 2: Add Payslip PDF Generation

- [x] Add `weasyprint` to `requirements.txt`.
- [x] Create `backend/apps/payroll/templates/payroll/payslip.html` — a clean, branded HTML template including:
  - Org logo (from `Organisation.logo` S3 URL or placeholder)
  - Company name, address, CIN/GST number
  - Employee name, code, designation, department, PAN (masked), UAN, ESI IP number
  - Pay period and payment date
  - Earnings table (Basic, HRA, Special Allowance, LTA, Arrears, OT Earnings)
  - Deductions table (EPF Employee, ESI Employee, PT, LWF, TDS, LOP)
  - Net pay (large, highlighted)
  - Tax regime and standard deduction note
  - QR code with payslip verification URL (use `qrcode` library)
  - "This is a computer-generated payslip and does not require a signature." footer
- [x] Create `backend/apps/payroll/filings/payslip_pdf.py` with `generate_payslip_pdf(payslip_id) -> bytes` that renders the HTML template to PDF via WeasyPrint.
- [x] Add a `GET /api/org/payroll/payslips/<payslip_id>/pdf/` endpoint that returns the PDF as `application/pdf` with `Content-Disposition: attachment; filename=payslip-<period>.pdf`.
- [x] Update the employee self-service payslip download endpoint similarly to return a branded PDF instead of the raw `rendered_text`.
- [x] Add tests: verify PDF bytes start with `%PDF`, verify org name and employee name appear in the rendered HTML before PDF conversion (test the template rendering directly), verify the endpoint returns 200 with correct content type.

## Task 3: Build PayrollRunDetailPage

- [x] Create `frontend/src/pages/org/PayrollRunDetailPage.tsx` with:
  - **Header**: Pay run period, status badge, employee count, total gross, total net, total deductions
  - **Exception banner**: if any `has_exception=true` items exist, show a count with a "Show exceptions only" filter toggle
  - **Employee table**: paginated (50/page), columns: Employee, Code, Dept, Gross, EPF, ESI, PT, TDS, LOP Days, Net Pay, Exception flag
  - **Expandable row**: clicking a row expands an inline breakdown showing all components from `PayrollRunItemDetailSerializer`
  - **Pre-finalization payslip preview**: a "Preview Payslip" button per employee row (only visible if run is in APPROVED status) that opens the payslip HTML in an `<iframe>` or modal using a `/pdf/` endpoint
  - **Actions**: "Approve Run" / "Finalize Run" buttons in the header, using the existing mutations — remove these from `PayrollPage` once this page exists
- [x] Register the route `/org/payroll/runs/:runId` in `frontend/src/routes/index.tsx`.
- [x] Update `PayrollPage.tsx` pay runs table to add a "View Details →" link per run row pointing to the new route.
- [x] Add TanStack Query hooks for `usePayrollRunItems(runId, filters)` with pagination support.

## Task 4: Add Frontend Tests for CT Payroll Pages

> **Audit finding (§5.4):** Zero tests for CT pages. `PayrollMastersPage` and `CtOrgPayrollPage` are the most functionally complex CT pages and have no test coverage.

- [x] Create `frontend/src/pages/ct/PayrollMastersPage.test.tsx`:
  - Renders the page with mocked slab set data
  - Clicking "New Tax Slab Set" opens the creation form
  - Submitting the form calls the create API with correct payload
  - Fiscal year free-text field shows a format hint (`YYYY-YYYY`)
  - Deleting a slab set opens a ConfirmDialog and calls the delete API on confirm
  - Deleting a slab set that has active payroll runs shows a warning (if API returns a 409 conflict)

- [x] Create `frontend/src/pages/ct/CtOrgPayrollPage.test.tsx`:
  - Renders with mocked org payroll config
  - PT and LWF rule sections display state-wise data
  - View detail modal opens on row click and shows slab data

- [x] Modify `frontend/src/pages/org/PayrollPage.test.tsx`:
  - Add test: switching to the Runs tab renders the runs table
  - Add test: clicking "View Details" on a run navigates to `/org/payroll/runs/:id`
  - Add test: Calculate button triggers the calculation mutation

## Task 5: Cleanup and Verification

- [x] Remove the inline per-run-item rendering from `PayrollPage.tsx` now that `PayrollRunDetailPage` exists.
- [x] Extract `CompensationSection`, `RunsSection`, and `FilingsSection` as named sub-components in the same file. The inline runs section JSX (130+ lines) and compensation/filings sections (460+ lines) were moved to named exported components. `PayrollPage.tsx` is now organized with three major sub-components, keeping the main component focused on state management and routing.
- [x] Run `cd frontend && npx vitest run src/pages/ct/ src/pages/org/PayrollPage.test.tsx` and confirm all new tests pass (31 test files, 70 tests all passing).
- [x] Run `cd backend && python manage.py test apps.payroll.tests.test_views` and confirm PDF and run-item list endpoint tests pass.
- [x] Verify WeasyPrint renders without font-related warnings in CI by adding a system font fallback in the HTML template.
