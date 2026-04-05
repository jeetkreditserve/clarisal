# P20 — HR Core Extensibility & ESS/Admin UX Completion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining HR-core and UX gaps not already covered by `P06`, `P10`, and `P11`: custom employee fields, structured exit interviews, org chart visualization, IT declaration UI, bulk operations, and remaining ESS/admin flow gaps.

**Architecture:** Keep employee profile extensibility in `employees`, compensation declarations in `payroll`, and UX-only projections in the frontend. Prefer dynamic schema and configuration models over adding more fixed columns to `Employee`.

**Tech Stack:** Django 4.2 · DRF · React 19 · TypeScript · pytest · Vitest · Playwright

---

## Audit Findings Addressed

- Custom employee fields missing
- Exit interview structured form missing
- Org chart visualization missing
- IT declaration employee UI missing
- Bulk operations missing
- Dashboard/leave/OD/payslip UX gaps still open

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/employees/models.py` | Modify | Add custom field and exit interview entities |
| `backend/apps/employees/services.py` | Modify | Dynamic profile and offboarding orchestration |
| `backend/apps/employees/serializers.py` | Modify | Dynamic-field and org-chart serializers |
| `backend/apps/employees/views.py` | Modify | Admin/self-service endpoints |
| `backend/apps/employees/tests/test_services.py` | Modify | Dynamic employee-data coverage |
| `backend/apps/payroll/views.py` | Modify | IT declaration review paths |
| `backend/apps/payroll/serializers.py` | Modify | ESS declaration payloads |
| `frontend/src/pages/org/EmployeesPage.tsx` | Modify | Bulk actions and dynamic-field filters |
| `frontend/src/pages/org/EmployeeDetailPage.tsx` | Modify | Dynamic fields and exit interview UI |
| `frontend/src/pages/employee/DashboardPage.tsx` | Modify | Attendance summary and approval badges |
| `frontend/src/pages/employee/LeavePage.tsx` | Modify | Calendar withdrawal UX |
| `frontend/src/pages/employee/OnDutyPage.tsx` | Modify | Request history |
| `frontend/src/pages/employee/PayslipsPage.tsx` | Modify | Search, year filters, bulk FY actions |
| `frontend/src/pages/org/OrgChartPage.tsx` | Create | Org chart visualization |
| `frontend/src/lib/api/self-service.ts` | Modify | IT declaration and ESS operations |

---

## Task 1: Add Custom Employee Fields

- [ ] Add configurable field definitions scoped per organisation, with field types, validation rules, required flags, and display placement.
- [ ] Add employee-value storage separate from the core `Employee` table to avoid schema churn per tenant.
- [ ] Expose custom fields in employee detail APIs, list filters, and create/update flows.

## Task 2: Add Structured Exit Interview Support

- [ ] Add exit interview templates, responses, and completion status tied to offboarding processes.
- [ ] Support scored and free-text questions so the audit no longer sees exit interview as a bare task type only.
- [ ] Surface the structured interview in org-admin offboarding flows and employee self-service where appropriate.

## Task 3: Add Org Chart Visualization

- [ ] Add a dedicated org-chart query or serializer projection based on `reporting_to` relationships.
- [ ] Build a navigable React tree view rather than forcing users to infer hierarchy from employee-detail links.
- [ ] Handle missing managers, cycles, and inactive employees cleanly in the tree projection.

## Task 4: Add IT Declaration UI

- [ ] Build employee-side CRUD for `InvestmentDeclaration` records with section-aware validation and fiscal-year grouping.
- [ ] Add payroll/admin review visibility so declarations are actionable and not model-only data.
- [ ] Keep business-rule validation aligned with `P02` and `P14` deduction logic.

## Task 5: Add Bulk Operations

- [ ] Add bulk employee invite, bulk leave approval, and bulk payslip send/export flows first.
- [ ] Ensure bulk actions are permission-aware, confirmable, and individually audited.
- [ ] Reuse shared selection and confirmation components instead of one-off page-local implementations.

## Task 6: Close Remaining ESS/Admin UX Gaps

- [ ] Add a real attendance summary card and pending approval badges to the employee dashboard.
- [ ] Add leave-calendar withdrawal affordances, OD history, and payslip year/search/filter UX.
- [ ] Add email-to-self or bulk FY download actions for payslips where operationally valid.

## Task 7: Cleanup and Verification

- [ ] Remove stale fixed-field assumptions from serializers, forms, and employee detail screens once dynamic fields are introduced.
- [ ] Add full coverage for dynamic-field validation, org-chart projections, exit interviews, bulk actions, and ESS flows.
- [ ] Run UI interaction tests for the new employee-detail, org-chart, dashboard, and payslip behaviors.
