# P22 — Expense Management Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the audit’s “Expense Management: ABSENT” gap by adding a production-grade expense claims workflow with policies, receipts, approval routing, reimbursement tracking, and payroll handoff.

**Architecture:** Build a dedicated `expenses` Django app. Keep receipt storage and document validation aligned with the existing `documents` patterns, approvals aligned with `approvals`, and reimbursement outputs aligned with payroll or finance export services instead of embedding expense logic into employee or payroll models directly.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · React 19 · TypeScript · pytest · Playwright

---

## Audit Findings Addressed

- Expense Management module absent
- Bulk operational workflows need stronger admin tooling

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/expenses/__init__.py` | Create | App package |
| `backend/apps/expenses/apps.py` | Create | App config |
| `backend/apps/expenses/models.py` | Create | Policies, claims, lines, receipts, reimbursements |
| `backend/apps/expenses/services.py` | Create | Claim submission and reimbursement orchestration |
| `backend/apps/expenses/serializers.py` | Create | API serializers |
| `backend/apps/expenses/views.py` | Create | Org/self-service APIs |
| `backend/apps/expenses/org_urls.py` | Create | Org routes |
| `backend/apps/expenses/self_urls.py` | Create | Employee routes |
| `backend/apps/expenses/tests/test_services.py` | Create | Service coverage |
| `backend/apps/expenses/tests/test_views.py` | Create | API coverage |
| `backend/clarisal/settings/base.py` | Modify | Register app |
| `backend/clarisal/urls.py` | Modify | Register namespaces |
| `frontend/src/lib/api/expenses.ts` | Create | API client |
| `frontend/src/pages/employee/ExpensesPage.tsx` | Create | ESS claim flow |
| `frontend/src/pages/org/ExpenseClaimsPage.tsx` | Create | Admin approval and reimbursement flow |
| `frontend/src/pages/org/ExpensePoliciesPage.tsx` | Create | Policy management |

---

## Task 1: Create the Expense Domain Models

- [ ] Add models for expense policies, categories, claims, claim lines, receipt attachments, and reimbursement batches.
- [ ] Support per-category limits, currency, mandatory receipt rules, and policy assignment per organisation.
- [ ] Keep reimbursement state separate from approval state so the system can represent approved-but-unpaid claims cleanly.

## Task 2: Build Service-Layer Workflows

- [ ] Add claim draft, submit, approve, reject, return-for-edit, and reimburse flows.
- [ ] Integrate with `approvals` for configurable multi-level approval where needed.
- [ ] Add payroll/export handoff hooks for reimbursements without tightly coupling claim storage to payroll runs.

## Task 3: Build APIs and UI

- [ ] Add employee claim creation, line editing, receipt upload, and status tracking.
- [ ] Add org-admin policy management, review queue, bulk approval, and reimbursement marking.
- [ ] Reuse shared upload, status badge, and confirmation components from the existing frontend.

## Task 4: Add Cleanup, Tests, and Reporting Hooks

- [ ] Add tests for policy validation, approval workflow transitions, reimbursement states, and receipt handling.
- [ ] Remove any duplicate ad-hoc reimbursement logic found elsewhere in the codebase once the module exists.
- [ ] Add a reporting/export hook so expense totals can be summarized alongside payroll and finance operations later.
