# Audit Remediation Baseline

Date: `2026-04-03`
Owner plan: `P13`
Source audit: `docs/HRMS_AUDIT_REPORT_20260403_195607.md`

## Purpose

This document re-baselines the audit against the current repository state so execution work starts from the real delta, not from stale audit claims. It covers `P01` to `P12` only. `P14` to `P23` remain the next execution queue after residual work from partially completed earlier plans is closed.

## Plan Status Matrix

| Plan | Status | Current baseline |
|---|---|---|
| `P01` | `implemented` | Security guards, serializer validation, secrets scanning artifacts, and PR automation are in repo; residual local hook installation is environment-only, not product-code debt. |
| `P02` | `implemented` | Payroll fixes landed, including 87A, old/new regime routing, investment declarations, F&F, arrears, and Form 16 data/export scaffolding. |
| `P03` | `implemented` | Leave carry-forward and max-balance enforcement landed, plus leave encashment model/service/API. |
| `P04` | `partially implemented` | Probation tracking, repository extraction, and payroll indexes are done; remaining async/API-versioning cleanup and residual checklist items still need closure. |
| `P05` | `partially implemented` | Attendance and key frontend test additions landed, but the plan's broader coverage harness, factories, E2E matrix, and coverage gate closure are not finished. |
| `P06` | `implemented` | UX/accessibility fixes, route boundary wiring, and payslip download flow are complete. |
| `P07` | `implemented` | Notification models, triggers, APIs, and bell/panel UI are in place. |
| `P08` | `implemented` | Reports app, org reports UI, and export flows are in place. |
| `P09` | `implemented` | Device CRUD, ADMS routes, Suprema integration, and eSSL eBioserver webhook support are in place. |
| `P10` | `implemented` | Performance module backend/frontend landed and is tested. |
| `P11` | `implemented` | Recruitment/ATS backend/frontend landed and is tested. |
| `P12` | `partially implemented` | JWT path, tooling config, E2E cleanup, and contributor docs landed; coverage enforcement, stable mypy verification, and full pre-commit execution are still open. |

## Audit Statements Now Considered Stale

These audit findings should be treated as verification-only items if they appear again in downstream plans:

| Audit statement | Baseline result |
|---|---|
| Performance Management is absent | Stale. Implemented by `P10`. |
| Recruitment / ATS is absent | Stale. Implemented by `P11`. |
| `djangorestframework-simplejwt` is installed but unused | Stale. JWT endpoints and auth config landed in `P12`. |
| Leave encashment is missing | Stale. Implemented by `P03`. |
| In-app notifications are missing | Stale. Implemented by `P07`. |
| Reports are attendance-only | Stale. `P08` added payroll register, headcount, leave utilization, attendance summary, and tax summary reporting. |

One audit statement remains current:

| Audit statement | Baseline result |
|---|---|
| Statutory filing export layer is absent | Still true. This is planned work in `P15`. |

## Residual Blockers Before Starting New Audit Work

`P13` requires `P01` to `P12` to be executed in dependency order before moving into `P14`. The remaining real pre-`P14` work is:

1. Close `P04` residuals.
   Async payroll/API versioning/repository cleanup checklist items remain open in the plan tracker.
2. Close `P05` residuals.
   The repo still lacks the full business-logic coverage harness and broad frontend/E2E expansion promised by the plan.
3. Close `P12` residuals.
   Coverage enforcement is configured but not met, `mypy` verification is not stable in the current container, and `pre-commit` has not been run end to end from repo root.

## Known `P12` Evidence And Gaps

- `docker compose exec backend python -m pytest apps/accounts/tests/test_jwt.py apps/recruitment/tests/test_services.py apps/recruitment/tests/test_views.py -q --tb=short` passed with `14 passed`.
- `docker compose exec frontend npx playwright test e2e/employee/leave.spec.ts` passed with `9 passed`.
- `docker compose exec frontend npm run build` passed.
- `rg -n "test.skip\\(" frontend/e2e` returned no matches.
- The coverage gate is not closed yet: `apps.accounts` measured `33%` against the target `80%`.
- `mypy` configuration exists, but clean verification is still blocked by runtime/tool instability in the backend container.

## Evidence Snapshots From Earlier Plan Execution

| Area | Verification snapshot |
|---|---|
| Payroll + leave integration | Backend suite reached `185 passed` after `P02` and `P03` execution. |
| Notifications | Targeted backend notification/approval/payroll tests passed (`24 passed`). |
| Reports | Targeted reports tests passed (`3 passed`) and frontend build passed. |
| Biometrics | Targeted biometric protocol/view/task tests passed and migrations applied. |
| Performance | Targeted backend performance tests passed (`12 passed`) and frontend tests/build passed. |
| Recruitment | Targeted backend recruitment tests passed and frontend tests/build passed. |

## Next Executable Queue

1. Finish residual checklist items in `P04`.
2. Finish residual checklist items in `P05`.
3. Finish residual checklist items in `P12`.
4. Start `P14`.
5. Continue `P15` through `P23` in strict numeric order.

## External References Used In This Re-baseline

- EPF wage ceiling context: <https://www.epfindia.gov.in/>
- ESI contribution period context: <https://www.esic.gov.in/>
- Coverage gate behavior: <https://pytest-cov.readthedocs.io/en/latest/config.html>
