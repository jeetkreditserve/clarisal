# P14 — Payroll Statutory Compliance Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining Indian payroll compliance gaps left open after `P02`: EPF wage ceiling, PF opt-out and VPF, ESI contribution periods, multi-state Professional Tax, Labour Welfare Fund, gratuity automation, surcharge handling, and regression-safe statutory tests.

**Architecture:** Move hard-coded statutory math out of `backend/apps/payroll/services.py` into focused payroll statutory modules backed by database seed data for state-wise rules. Keep API and serializer changes thin. Every statutory rule must be covered by exact-value tests and seeded master data.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · pytest · decimal.Decimal

---

## Audit Findings Addressed

- EPF wage ceiling not enforced
- EPF opt-out for eligible new joiners missing
- VPF contribution missing
- ESI half-year contribution period missing
- Professional Tax hardcoded to Maharashtra
- Labour Welfare Fund not implemented
- Gratuity formula not automated
- Surcharge slabs for high earners missing
- Payroll statutory boundary coverage still incomplete

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/payroll/models.py` | Modify | Add statutory master models and assignment flags |
| `backend/apps/payroll/services.py` | Modify | Remove inlined statutory branches and delegate to focused modules |
| `backend/apps/payroll/statutory.py` | Create | EPF, ESI, PT, LWF, surcharge, gratuity calculators |
| `backend/apps/payroll/statutory_seed.py` | Create | Seed payloads for PT and LWF rules |
| `backend/apps/payroll/management/commands/seed_statutory_masters.py` | Create | Repeatable seed-data command |
| `backend/apps/payroll/serializers.py` | Modify | Expose assignment flags and statutory master data where needed |
| `backend/apps/payroll/views.py` | Modify | Admin endpoints for statutory masters if missing |
| `backend/apps/payroll/migrations/0009_*.py` | Create | New schema for compliance fields and master tables |
| `backend/apps/payroll/tests/test_statutory_calculations.py` | Modify | Exact-value unit coverage |
| `backend/apps/payroll/tests/test_full_and_final.py` | Modify | Gratuity and F&F regression tests |
| `backend/apps/payroll/tests/test_services.py` | Modify | Payroll run integration coverage |

---

## Task 1: Decompose Statutory Logic Before Adding Rules

- [x] Create `backend/apps/payroll/statutory.py` and move EPF, ESI, PT, cess, rebate, surcharge, gratuity, and LWF helpers into pure functions.
- [x] Keep `backend/apps/payroll/services.py` responsible only for orchestration and persistence.
- [x] Delete or inline stale helper branches in `services.py` after the move so no duplicate rule paths remain.
- [x] Add focused unit tests for each extracted function before wiring it back into payroll-run orchestration.

## Task 2: Add Payroll Master Data for PT and LWF

- [x] Add DB models for `ProfessionalTaxRule`, `ProfessionalTaxSlab`, `LabourWelfareFundRule`, and `LabourWelfareFundContribution`.
- [x] Seed at minimum Maharashtra, Karnataka, Tamil Nadu, West Bengal, Andhra Pradesh, Telangana, and Madhya Pradesh PT rules.
- [x] Seed LWF rules for states explicitly called out by the audit and structure the model so future state additions are data-only.
- [x] Add admin and API read paths for validating seeded rules in tests and operational screens.

## Task 3: Fix EPF Wage Ceiling, Opt-Out, and VPF

- [x] Add `is_pf_opted_out` and `vpf_rate_percent` to `CompensationAssignment`.
- [x] Enforce `pf_eligible_basic = min(basic_pay, 15000)` unless a compliant override path is explicitly configured.
- [x] Apply PF opt-out only to employees who meet the statutory eligibility rule for higher-wage new joiners.
- [x] Calculate VPF as an additional employee-side PF deduction without changing employer contribution splits unless explicitly required.
- [x] Cover edge cases: ₹15,000 exactly, ₹15,000.01, opt-out employees, and VPF percentages above the default 12%.

## Task 4: Add ESI Contribution-Period Persistence

- [x] Add contribution-period fields to `Payslip` or a focused payroll-period model so ESI eligibility survives a mid-period salary increase.
- [x] Implement April-September and October-March contribution windows exactly once in the statutory module.
- [x] Update payroll-run calculations to continue ESI deductions through the active contribution window even after gross exceeds ₹21,000.
- [x] Add regression tests for employees crossing the threshold mid-period, exactly on the threshold, and re-entering eligibility in the next period.

## Task 5: Replace Hardcoded Maharashtra PT With Data-Driven State Logic

- [x] Resolve organisation state through address metadata instead of defaulting silently to Maharashtra.
- [x] Query PT master data from `ProfessionalTaxRule` and `ProfessionalTaxSlab` rather than using hard-coded constants.
- [x] Fail loudly with a payroll exception if an organisation’s state requires PT but no active rule set exists.
- [x] Add boundary tests for each seeded state and snapshot tests for payroll-run deductions.

## Task 6: Implement LWF and Gratuity Automation

- [x] Add employee and employer LWF components and attach them only in applicable state and frequency windows.
- [x] Automate gratuity in F&F using the 15/26 formula, service-length eligibility rules, and statutory ceiling caps.
- [x] Reconcile gratuity calculations with offboarding dates and the final effective compensation assignment.
- [x] Update rendered payslip/F&F views to show new deduction and settlement lines clearly.

## Task 7: Add Surcharge and Regression Guards

- [x] Implement surcharge tiers for high earners in the new regime and ensure cess is applied in the correct order.
- [x] Add tests for incomes around every surcharge threshold boundary.
- [x] Cross-check that `P02` old-regime and investment-declaration work still composes correctly with the new statutory engine.

## Task 8: Cleanup and 100% Statutory Coverage

- [x] Remove stale constants, dead comments, and obsolete branches left from hard-coded MH-only PT and one-month ESI assumptions.
- [x] Raise coverage on changed payroll modules to full exercised coverage with exact rupee assertions.
- [x] Run payroll integration tests, API tests, and at least one end-to-end payroll run covering PT, EPF, ESI, and LWF in combination.
