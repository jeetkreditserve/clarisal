# P23 — Asset Lifecycle Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the audit’s “Asset Lifecycle: ABSENT” gap by adding asset cataloguing, issuance, acknowledgements, maintenance, recovery, and offboarding return tracking.

**Architecture:** Build a dedicated `assets` Django app with clear separation between master data (`AssetCategory`, `AssetItem`) and lifecycle records (`Assignment`, `Maintenance`, `Return`). Integrate with employees, documents, and offboarding without hiding asset state inside unrelated models.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · React 19 · TypeScript · pytest · Playwright

---

## Audit Findings Addressed

- Asset Lifecycle module absent
- Offboarding workflows need stronger structured completion evidence

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/assets/__init__.py` | Create | App package |
| `backend/apps/assets/apps.py` | Create | App config |
| `backend/apps/assets/models.py` | Create | Asset catalog and lifecycle models |
| `backend/apps/assets/services.py` | Create | Issue, acknowledge, maintain, recover workflows |
| `backend/apps/assets/serializers.py` | Create | API serializers |
| `backend/apps/assets/views.py` | Create | Org/self APIs |
| `backend/apps/assets/org_urls.py` | Create | Org routes |
| `backend/apps/assets/self_urls.py` | Create | Employee routes |
| `backend/apps/assets/tests/test_services.py` | Create | Lifecycle coverage |
| `backend/apps/assets/tests/test_views.py` | Create | API coverage |
| `backend/apps/employees/services.py` | Modify | Offboarding integration |
| `backend/clarisal/settings/base.py` | Modify | Register app |
| `backend/clarisal/urls.py` | Modify | Register namespaces |
| `frontend/src/lib/api/assets.ts` | Create | API client |
| `frontend/src/pages/employee/MyAssetsPage.tsx` | Create | Employee asset view and acknowledgement |
| `frontend/src/pages/org/AssetsInventoryPage.tsx` | Create | Inventory management |
| `frontend/src/pages/org/AssetAssignmentsPage.tsx` | Create | Assignment and return operations |

---

## Task 1: Create the Asset Domain Models

- [ ] Add master-data models for categories, vendors, and asset templates if needed.
- [ ] Add lifecycle models for asset items, employee assignments, acknowledgements, maintenance, incidents, and returns.
- [ ] Track serial number, condition, warranty metadata, current holder, and lifecycle status explicitly.

## Task 2: Build Lifecycle Services

- [ ] Add services for asset issuance, employee acknowledgement, reassignment, maintenance scheduling, damage/loss recording, and return confirmation.
- [ ] Integrate asset-return status into offboarding so HR can see unresolved recoveries before closing an employee exit.
- [ ] Add audit logging around every custody transfer and condition change.

## Task 3: Build APIs and UI

- [ ] Add inventory CRUD, assignment, return, and maintenance endpoints for org admins.
- [ ] Add employee self-service visibility for assigned assets, acknowledgement state, and return instructions.
- [ ] Reuse existing confirmation-dialog and status components rather than inventing another workflow pattern.

## Task 4: Cleanup and Verification

- [ ] Remove any scattered asset acknowledgement workarounds once the module exists as a first-class domain.
- [ ] Add tests for lifecycle state changes, offboarding blocking rules, and employee acknowledgements.
- [ ] Add at least one E2E flow covering issue → acknowledge → offboarding return.
