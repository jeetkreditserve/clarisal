# P13 — Audit Remediation Program

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `docs/HRMS_AUDIT_REPORT_20260403_195607.md` into a dependency-safe execution program that combines existing plans `P01` to `P12` with new plans `P14` to `P23` until the next audit should not repeat any current finding.

**Architecture:** `P13` is the orchestration plan. It does not introduce product code directly. It defines ownership, ordering, global test and cleanup gates, and the exact sequence Claude Code should follow when executing audit remediation work across backend, frontend, Celery, and infra.

**Tech Stack:** Markdown planning docs · Django 4.2 · DRF · Celery · React 19 · TypeScript · pytest · Vitest · Playwright

---

## Existing Plan Coverage to Reuse

| Audit Area | Existing Plan |
|---|---|
| Secrets, key validation, serializer validation, security hooks, JWT, base code-quality tooling | `P01`, `P12` |
| Payroll foundations: 87A, old/new regime scaffolding, investment declarations backend, F&F, arrears, Form 16 data | `P02` |
| Leave service bugs and leave encashment | `P03` |
| Async payroll, API versioning, repository cleanups, probation tracking | `P04` |
| Business-logic coverage harness and frontend/E2E testing foundation | `P05` |
| Existing frontend accessibility and UX baseline fixes | `P06` |
| Notifications and approval outcome messaging | `P07` |
| Reports and payroll register reporting foundation | `P08` |
| Core biometric protocol support already planned and largely present in code | `P09` |
| Performance management module | `P10` |
| Recruitment / ATS module | `P11` |

---

## New Plan Set Introduced Here

| Plan | Scope |
|---|---|
| `P14` | Payroll statutory compliance hardening not covered by `P02` |
| `P15` | Statutory filing export layer: ECR, ESI challan, Form 24Q, PT returns, Form 16 documents |
| `P16` | Communications automation and approval-governance gaps |
| `P17` | Control Tower impersonation, feature flags, onboarding, analytics, billing automation |
| `P18` | Attendance workforce policies: OT pay, comp-off, WFH, shift rotation, lapse jobs, calendars |
| `P19` | Biometric market-coverage expansion and live attendance feed |
| `P20` | HR core extensibility and ESS/admin UX completeness |
| `P21` | Remaining security and platform hardening gaps |
| `P22` | Expense management module |
| `P23` | Asset lifecycle module |

---

## Global Execution Rules

- [ ] **Rule 1: Treat audit closure as code + tests + cleanup**
  Every plan execution must include production code, tests, removal of stale helpers/components/routes, and doc updates. Do not defer cleanup into a later pass.

- [ ] **Rule 2: Enforce full coverage on touched modules**
  For every app touched by a task, add or extend unit, integration, and UI tests until the changed files are fully exercised. Use `P05` and `P12` as the shared coverage/lint/typecheck baseline.

- [x] **Rule 3: Reconcile stale audit statements against current code before editing**
  The repository has already moved ahead of parts of the audit. Before implementing any plan, compare the current app state against the audit text and narrow the delta to real remaining work.

- [ ] **Rule 4: Prefer decomposition over growing monolith files**
  If a task would enlarge `backend/apps/payroll/services.py`, `frontend/src/pages/org/EmployeeDetailPage.tsx`, or similar large files, split logic into focused modules first, then implement the feature.

- [ ] **Rule 5: Keep migrations ordered by dependency**
  Finish schema and seed-data work in `P14` before `P15`. Finish approval and notification model changes in `P16` before `P20` bulk operations. Finish attendance domain changes in `P18` before live device/event work in `P19`.

- [x] **Rule 6: Preserve audit evidence**
  Keep a running evidence log under `docs/` or in PR notes with test commands, screenshots, export samples, and before/after behavior so the next audit can verify closure quickly.

---

## Execution Order

### Task 1: Re-baseline Existing Plans Against Current Code

- [x] Verify that current code matches the implemented portions of `P01` to `P12`, especially `payroll`, `notifications`, `reports`, `biometrics`, `performance`, and `recruitment`.
- [x] Record each existing plan as one of: `implemented`, `partially implemented`, `stale`, or `still pending`.
- [x] Convert any audit item already fixed in code into a verification-only checklist instead of re-implementing it.

### Task 2: Execute the Dependency Chain

- [-] Run `P01` to `P12` in dependency order, but skip only items that are already verifiably present in code and fully tested.
- [ ] Start new work with `P14`, then continue in exact numeric order through `P23`.
- [ ] Do not pull filing exports (`P15`) forward ahead of the payroll compliance master-data work in `P14`.
- [ ] Do not start biometric live-feed work in `P19` until `P18` attendance-domain event semantics are stable.

### Task 3: Shared Verification Gates After Each Plan

- [ ] Run targeted backend tests for touched apps.
- [ ] Run targeted Vitest suites for touched screens and hooks.
- [ ] Run Playwright flows for user-visible workflows affected by the plan.
- [ ] Run lint, typecheck, and coverage enforcement from `P12`.
- [ ] Remove dead imports, unused components, stale migrations/tests, and obsolete plan assumptions introduced by the change.

### Task 4: Final Audit-Closure Sweep

- [ ] Re-open `docs/HRMS_AUDIT_REPORT_20260403_195607.md` and walk every unresolved row area-by-area.
- [ ] For each prior finding, attach its owning implementation plan and the proof artifact that closes it.
- [ ] Re-run a fresh audit only after `P01` to `P23` verification evidence is complete.

---

## Final Ordered Plan Queue

1. `P01` — Critical Security Fixes
2. `P02` — Payroll Engine Fixes
3. `P03` — Leave Service Fixes
4. `P04` — Backend Architecture Improvements
5. `P05` — Test Coverage: 100% Business Logic
6. `P06` — Frontend UX Fixes
7. `P07` — Notifications System
8. `P08` — Reports & Analytics
9. `P09` — Biometric Device Integration
10. `P10` — Performance Management Module
11. `P11` — Recruitment Module
12. `P12` — Code Quality & Cleanup
13. `P14` — Payroll Statutory Compliance Hardening
14. `P15` — Statutory Filing Export Layer
15. `P16` — Communications Automation & Approval Governance
16. `P17` — Control Tower Governance & Billing Automation
17. `P18` — Attendance Workforce Policies & ESS Calendar Flows
18. `P19` — Biometric Market Coverage & Live Attendance Feed
19. `P20` — HR Core Extensibility & ESS/Admin UX Completion
20. `P21` — Security & Platform Hardening Sweep
21. `P22` — Expense Management Module
22. `P23` — Asset Lifecycle Module
23. Final re-audit and residual cleanup pass

---

## 2026-04-03 Re-baseline Result

- `implemented`: `P01`, `P02`, `P03`, `P06`, `P07`, `P08`, `P09`, `P10`, `P11`
- `partially implemented`: `P04`, `P05`, `P12`
- `still pending`: `P14` to `P23`
- `stale audit claims now superseded by code`: Performance Management absent, Recruitment absent, JWT unused, Leave Encashment missing, In-app notifications missing, reports limited to attendance-only

See `docs/AUDIT_REMEDIATION_BASELINE_20260403.md` for the per-plan breakdown, residual blockers, and the next executable queue after `P13`.
