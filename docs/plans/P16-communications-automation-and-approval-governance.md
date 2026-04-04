# P16 — Communications Automation & Approval Governance

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the unplanned workflow gaps around notices and approvals: scheduled notice publishing, precise expiry, communications tests, approval delegation, and SLA-based escalation.

**Architecture:** Keep `communications` responsible for notice lifecycle and `approvals` responsible for decision routing. Remove write side effects from read paths, move time-based transitions into Celery tasks, and add explicit delegation and escalation models instead of hidden fallback behavior.

**Tech Stack:** Django 4.2 · DRF · Celery 5.4 · pytest · React 19 · TypeScript

---

## Audit Findings Addressed

- Communications app has zero tests
- Notice auto-publish missing
- Notice auto-expiry happens lazily on read
- Delegation of approval authority missing
- SLA-based escalation missing

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/communications/services.py` | Modify | Make notice state transitions explicit and side-effect free on reads |
| `backend/apps/communications/tasks.py` | Create | Scheduled publish and expiry tasks |
| `backend/apps/communications/tests/test_services.py` | Create | Service and state-transition coverage |
| `backend/apps/communications/tests/test_tasks.py` | Create | Celery task coverage |
| `backend/apps/communications/views.py` | Modify | Surface automation state cleanly |
| `backend/apps/approvals/models.py` | Modify | Add delegation and escalation models/fields |
| `backend/apps/approvals/services.py` | Modify | Resolve approvers through delegation and SLA logic |
| `backend/apps/approvals/tasks.py` | Create | Reminder and escalation workers |
| `backend/apps/approvals/tests/test_services.py` | Modify | Delegation/escalation coverage |
| `backend/apps/approvals/tests/test_tasks.py` | Create | Time-based escalation coverage |
| `backend/apps/approvals/views.py` | Modify | Admin APIs for delegation/escalation |
| `frontend/src/pages/org/NoticesPage.tsx` | Modify | Show automation status and blocked notices |
| `frontend/src/pages/org/NoticeEditorPage.tsx` | Modify | Scheduling UX and validation |
| `frontend/src/pages/employee/ApprovalsPage.tsx` | Modify | Delegation/escalation visibility |

---

## Task 1: Add the Missing Communications Test Suite

- [x] Create `backend/apps/communications/tests/` and cover `create_notice()`, `update_notice()`, `publish_notice()`, and `get_visible_notices()`.
- [x] Add scenarios for audience targeting, scheduled visibility, expiry cutoffs, sticky ordering, and CT/org-admin authoring paths.
- [x] Freeze time in tests so publish and expiry boundaries are deterministic.

## Task 2: Refactor Notice Lifecycle Out of Read Paths

- [x] Remove implicit expiry writes from `get_visible_notices()`.
- [x] Add explicit service functions for `publish_scheduled_notices()` and `expire_stale_notices()`.
- [x] Keep `get_visible_notices()` as a pure visibility query plus ordering helper.

## Task 3: Add Notice Automation With Celery

- [x] Create `backend/apps/communications/tasks.py` with idempotent scheduled-publish and auto-expiry workers.
- [x] Register Celery beat entries in settings with safe frequencies and locking/overlap protection.
- [x] Add audit events for automatic publish and expiry so time-based state changes remain traceable.

## Task 4: Add Approval Delegation

- [x] Add delegation models capturing delegator, delegate, request kinds, start/end dates, and active status.
- [x] Update approver resolution so delegated approvers receive actions without losing the original approver identity.
- [x] Prevent invalid delegation loops and self-delegation.

## Task 5: Add SLA-Based Escalation

- [x] Add per-stage SLA fields or a separate escalation policy model to `approvals`.
- [x] Create reminder and escalation tasks that run against pending approval actions.
- [x] Reassign or notify escalation targets explicitly instead of relying on silent fallback rules.

## Task 6: Update Admin and Employee UI

- [x] Surface notice automation states in org notices pages and editors.
- [x] Add delegation and escalation management screens or panels for org admins.
- [x] Show employees who currently owns a delegated approval and which actions are overdue or escalated.

## Task 7: Cleanup and Verification

- [x] Delete stale notice-side-effect branches and any temporary fallback logic made obsolete by explicit delegation/escalation.
- [-] Raise changed communications and approvals modules to full exercised coverage.
- [x] Run backend task tests plus targeted UI tests around notice scheduling and delegated approvals.
