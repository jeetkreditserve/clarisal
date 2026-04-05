# P17 — Control Tower Governance & Billing Automation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the remaining Control Tower governance gaps from the audit: impersonation, per-org feature flags, guided onboarding, usage analytics, and licence billing automation.

**Architecture:** Keep organisation tenancy boundaries intact by implementing CT-only governance primitives in `organisations` and `accounts/workspaces`, with explicit audit logging for every privileged action. Add analytics and billing as additive services rather than hard-coding them into CT pages.

**Tech Stack:** Django 4.2 · DRF · Celery · PostgreSQL · React 19 · TypeScript

---

## Audit Findings Addressed

- No impersonation / act-as
- No per-org module feature flags
- Guided onboarding wizard incomplete
- Usage analytics missing
- Invoice / billing integration missing

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/organisations/models.py` | Modify | Add act-as session, feature flags, analytics, billing entities |
| `backend/apps/organisations/services.py` | Modify | CT orchestration services |
| `backend/apps/organisations/serializers.py` | Modify | CT-facing serializers |
| `backend/apps/organisations/views.py` | Modify | CT governance endpoints |
| `backend/apps/organisations/tasks.py` | Create | Usage aggregation and billing tasks |
| `backend/apps/organisations/tests/test_services.py` | Modify | Governance coverage |
| `backend/apps/organisations/tests/test_views.py` | Modify | CT API coverage |
| `backend/apps/accounts/workspaces.py` | Modify | Workspace context for act-as sessions |
| `backend/apps/audit/services.py` | Modify | Explicit impersonation start/end logging if required |
| `frontend/src/pages/ct/OrganisationDetailPage.tsx` | Modify | Feature flags, act-as, analytics panels |
| `frontend/src/pages/ct/NewOrganiCSRF Failed: CSRF token from the 'X-Csrftoken' HTTP header incorrect.sationPage.tsx` | Modify | Guided onboarding wizard |
| `frontend/src/pages/ct/OrganisationsPage.tsx` | Modify | CT operational visibility |
| `frontend/src/lib/api/organisations.ts` | Modify | Governance API client |

---

## Task 1: Implement CT Impersonation Safely

- [x] Add an `ActAsSession` model with CT actor, target organisation, target org-admin, reason, start time, end time, and revocation fields.
- [x] Update workspace-resolution logic so act-as sessions are explicit, reversible, and visible in request context.
- [x] Add clear UI banners and audit events for impersonation start, refresh, and stop actions.
- [x] Block destructive CT actions while impersonating unless explicitly allowed and logged.

## Task 2: Add Per-Organisation Feature Flags

- [x] Add an `OrganisationFeatureFlag` model keyed by organisation and feature code.
- [x] Resolve feature access centrally in permissions or workspace gating instead of sprinkling `if` statements across views.
- [x] Add CT UI to enable or disable modules and rollout flags per tenant.
- [x] Cover both backend authorization and frontend navigation hiding with tests.

## Task 3: Add Guided New-Organisation Onboarding

- [ ] Extend organisation setup into a step-driven checklist covering admins, departments, locations, leave, payroll, policies, holidays, and first employee invite.
- [ ] Persist onboarding progress server-side so CT can resume unfinished setups.
- [ ] Add validation that prevents marking onboarding complete while mandatory org configuration is missing.

## Task 4: Add Usage Analytics

- [ ] Add an `OrgUsageStat` aggregate model and a daily aggregation task.
- [ ] Track DAU plus core feature usage counts without leaking tenant data across organisations.
- [ ] Surface time-series cards and operational metrics in CT pages rather than one-off count summaries only.

## Task 5: Automate Licence Billing and Payment Status

- [ ] Add invoice metadata and payment-reference fields to licence batches or a dedicated billing model.
- [ ] Implement webhook ingestion for the selected payment-provider abstraction and update batch payment states automatically.
- [ ] Keep billing integration isolated so provider-specific details do not spread across CT service code.

## Task 6: Cleanup and Coverage

- [ ] Remove stale CT-only inline setup logic superseded by the new onboarding flow.
- [ ] Cover act-as, feature-flag enforcement, onboarding progression, analytics aggregation, and billing webhooks with tests.
- [ ] Verify impersonation and feature flags do not break existing org-admin or employee workspace behavior.
