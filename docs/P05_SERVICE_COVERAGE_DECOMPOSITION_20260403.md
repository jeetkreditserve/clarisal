# P05 Service Coverage Decomposition

Date: `2026-04-03`
Owner plan: `P05`

## Current State

The original `P05` target assumes business logic is concentrated in a few helper functions. That assumption is no longer true.

Current measured backend gate:

- `apps/payroll/services.py` -> `16%`
- `apps/timeoff/services.py` -> `23%`
- `apps/attendance/services.py` -> `15%`
- combined gate -> `17.18%`

These files are now orchestration modules spanning setup, CRUD, approvals, imports, reporting, notifications, and calculation paths. The coverage gap needs to be decomposed by behavior cluster, not attacked as one monolithic “add tests” item.

## Execution Progress

- [x] `P5-PAY-1` helper slice implemented in `backend/apps/payroll/tests/test_service_helpers.py`
- [x] `P5-PAY-2` setup/approval slice implemented in `backend/apps/payroll/tests/test_service_setup.py`
- [x] `P5-PAY-3` payroll run orchestration slice implemented in `backend/apps/payroll/tests/test_service_run_calculation.py`
- [x] `P5-PAY-4` finalization and rerun slice implemented in `backend/apps/payroll/tests/test_service_run_finalization.py`
- [x] `P5-TO-1` cycle and plan configuration implemented in `backend/apps/timeoff/tests/test_service_configuration.py`
- [x] `P5-TO-2` accrual and balances implemented in `backend/apps/timeoff/tests/test_service_balances.py`
- [x] `P5-TO-3` encashment and request lifecycle implemented in `backend/apps/timeoff/tests/test_service_requests.py`
- [x] `P5-TO-4` holiday and calendar rendering implemented in `backend/apps/timeoff/tests/test_service_calendar.py`
- [x] `P5-AT-1` workbook parsing and sample generation implemented in `backend/apps/attendance/tests/test_service_parsers.py`
- [x] `P5-AT-2` policy, source config, and shift management implemented in `backend/apps/attendance/tests/test_service_configuration.py`
- [x] `P5-AT-3` day summarization core implemented in `backend/apps/attendance/tests/test_service_day_summary.py`
- [ ] `P5-AT-4` employee punch and source ingestion
- [x] `P5-AT-5` regularization and org summaries implemented in `backend/apps/attendance/tests/test_service_regularization_and_reports.py`
- [ ] `P5-AT-6` attendance and punch imports

Latest payroll-only measurement after `P5-PAY-1` to `P5-PAY-4`:

- `apps/payroll/services.py` -> `85%`
- command:
  `docker compose exec backend /bin/sh -lc "export HOME=/tmp PYTHONPATH=/tmp/.local/lib/python3.11/site-packages PATH=/tmp/.local/bin:$PATH COVERAGE_FILE=/tmp/.coverage; python -m pytest apps/payroll/tests/test_service_helpers.py apps/payroll/tests/test_service_setup.py apps/payroll/tests/test_service_run_calculation.py apps/payroll/tests/test_service_run_finalization.py --cov=apps.payroll.services --cov-report=term-missing --cov-fail-under=80 -q --tb=short --reuse-db"`

Bug found and fixed during this slice:

- exit-month payroll proration in `calculate_pay_run()` was wrong when an employee joined on the first day of the month and exited mid-month. The service now computes paid days from both start and end bounds instead of treating join and exit as mutually exclusive.

Latest timeoff-only measurement after `P5-TO-1` to `P5-TO-4` plus the existing timeoff suites:

- `apps/timeoff/services.py` -> `89%`
- command:
  `docker compose exec backend /bin/sh -lc "export HOME=/tmp PYTHONPATH=/tmp/.local/lib/python3.11/site-packages PATH=/tmp/.local/bin:$PATH COVERAGE_FILE=/tmp/.coverage; python -m pytest apps/timeoff/tests/test_services.py apps/timeoff/tests/test_views.py apps/timeoff/tests/test_serializers.py apps/timeoff/tests/test_service_configuration.py apps/timeoff/tests/test_service_balances.py apps/timeoff/tests/test_service_requests.py apps/timeoff/tests/test_service_calendar.py --cov=apps.timeoff.services --cov-report=term-missing --cov-fail-under=80 -q --tb=short --reuse-db"`

Bugs found and fixed during this slice:

- leave-cycle, leave-plan, holiday-calendar, and on-duty-policy default switching saved the new default before clearing the old one, which violated the underlying unique constraints for default records.
- leave request, on-duty request, and attendance regularization withdrawal flows were setting `WITHDRAWN` and then immediately overwriting the subject back to `CANCELLED` when the linked approval run was cancelled.
- payroll run recalculation now cancels the linked approval run without mutating the payroll run subject status.

Latest attendance-only measurement after `P5-AT-1`, `P5-AT-2`, `P5-AT-3`, and `P5-AT-5` plus the existing attendance suites:

- `apps/attendance/services.py` -> `83%`
- command:
  `docker compose exec backend /bin/sh -lc "export HOME=/tmp PYTHONPATH=/tmp/.local/lib/python3.11/site-packages PATH=/tmp/.local/bin:$PATH COVERAGE_FILE=/tmp/.coverage; python -m pytest apps/attendance/tests/test_daily_calculation.py apps/attendance/tests/test_views.py apps/attendance/tests/test_service_parsers.py apps/attendance/tests/test_service_configuration.py apps/attendance/tests/test_service_day_summary.py apps/attendance/tests/test_service_regularization_and_reports.py --cov=apps.attendance.services --cov-report=term-missing --cov-fail-under=80 -q --tb=short --reuse-db"`

Bug found and fixed during this slice:

- attendance policy default switching saved the new default before clearing the old one, which violated the unique default-policy constraint for the organisation.

Combined backend gate after the verified payroll, timeoff, and attendance slices:

- `apps/payroll/services.py` -> `85%`
- `apps/timeoff/services.py` -> `89%`
- `apps/attendance/services.py` -> `83%`
- combined gate -> `85%`
- command:
  `docker compose exec backend /bin/sh -lc "export HOME=/tmp PYTHONPATH=/tmp/.local/lib/python3.11/site-packages PATH=/tmp/.local/bin:$PATH COVERAGE_FILE=/tmp/.coverage; python -m pytest apps/payroll/tests/test_service_helpers.py apps/payroll/tests/test_service_setup.py apps/payroll/tests/test_service_run_calculation.py apps/payroll/tests/test_service_run_finalization.py apps/timeoff/tests/test_services.py apps/timeoff/tests/test_views.py apps/timeoff/tests/test_serializers.py apps/timeoff/tests/test_service_configuration.py apps/timeoff/tests/test_service_balances.py apps/timeoff/tests/test_service_requests.py apps/timeoff/tests/test_service_calendar.py apps/attendance/tests/test_daily_calculation.py apps/attendance/tests/test_views.py apps/attendance/tests/test_service_parsers.py apps/attendance/tests/test_service_configuration.py apps/attendance/tests/test_service_day_summary.py apps/attendance/tests/test_service_regularization_and_reports.py --cov=apps.payroll.services --cov=apps.timeoff.services --cov=apps.attendance.services --cov-report=term-missing --cov-fail-under=80 -q --tb=short --reuse-db"`

## Existing Useful Coverage

Already covered enough to avoid redoing first:

- payroll:
  `test_statutory_calculations.py`, `test_services.py`, `test_full_and_final.py`, `test_investment_declarations.py`, `test_tasks.py`, `test_views.py`
- timeoff:
  `test_services.py`, `test_views.py`, `test_serializers.py`
- attendance:
  `test_daily_calculation.py`, `test_views.py`

This means the next work should fill untested clusters around orchestration, edge cases, and import / approval / summary behavior.

## Payroll Decomposition

File: `backend/apps/payroll/services.py`

### Cluster P5-PAY-1: Pure tax and formatting helpers

Lines and functions:

- `66-168`
- `_professional_tax_monthly`
- `_current_fiscal_year`
- `_normalize_decimal`
- `_fiscal_year_for_period`
- `_get_or_create_component`
- `_fmt_inr`
- `_build_rendered_payslip`

Existing coverage:

- tax math is partially covered
- component creation, fiscal-year helpers, INR formatting, and rendered payslip formatting are not directly covered

Recommended test file:

- `backend/apps/payroll/tests/test_service_helpers.py`

### Cluster P5-PAY-2: Setup and approval scaffolding

Lines and functions:

- `277-835`
- `_summarize_pay_run_exceptions`
- `_notify_employees_payroll_finalized`
- `get_total_80c_deduction`
- `calculate_taxable_income_with_investments`
- `calculate_fnf_salary_proration`
- `calculate_leave_encashment_amount`
- `_get_assignment_monthly_amounts`
- `get_employee_arrears_for_run`
- `_get_active_tax_slab_set`
- `_ensure_global_default_tax_master`
- `_resolve_payroll_requester_context`
- `_create_payroll_approval_run`
- `ensure_org_payroll_setup`
- `create_tax_slab_set`
- `update_tax_slab_set`
- `create_compensation_template`
- `update_compensation_template`
- `submit_compensation_template_for_approval`
- `assign_employee_compensation`
- `submit_compensation_assignment_for_approval`
- `get_effective_compensation_assignment`

Existing coverage:

- some compensation and declaration flows are touched indirectly
- tax master fallback, approval-run creation, and update edge cases remain mostly untested

Recommended test files:

- `backend/apps/payroll/tests/test_service_setup.py`
- `backend/apps/payroll/tests/test_service_compensation_lifecycle.py`

### Cluster P5-PAY-3: Payroll run orchestration

Lines and functions:

- `842-1293`
- `create_payroll_run`
- `_employee_payroll_snapshot`
- `calculate_pay_run`

Existing coverage:

- async dispatch and some happy-path service coverage exist
- exception-item creation, tax-regime routing failure, attendance-backed LOP, arrears inclusion, and payroll snapshot contents are still thin

Recommended test file:

- `backend/apps/payroll/tests/test_service_run_calculation.py`

### Cluster P5-PAY-4: Finalization and rerun

Lines and functions:

- `1296-1458`
- `generate_form16_data`
- `submit_pay_run_for_approval`
- `finalize_pay_run`
- `rerun_payroll_run`

Existing coverage:

- Form 16 and F&F are partially tested
- rerun creation, finalization side effects, and payslip snapshot rendering still need direct assertions

Recommended test file:

- `backend/apps/payroll/tests/test_service_run_finalization.py`

## Timeoff Decomposition

File: `backend/apps/timeoff/services.py`

### Cluster P5-TO-1: Cycle and plan configuration

Lines and functions:

- `82-204`
- `get_org_operations_guard`
- `get_default_leave_cycle`
- `upsert_leave_cycle`
- `_upsert_leave_plan_relations`
- `create_leave_plan`
- `update_leave_plan`
- `_rule_matches_employee`
- `resolve_employee_leave_plan`
- `get_cycle_window`

Existing coverage:

- current tests focus on balances, carry-forward, encashment
- leave cycle CRUD and employee-to-plan resolution are mostly uncovered

Recommended test file:

- `backend/apps/timeoff/tests/test_service_configuration.py`

### Cluster P5-TO-2: Accrual and balances

Lines and functions:

- `229-397`
- `_periods_elapsed`
- `_compute_credit_for_period`
- `_calculate_period_credit_amount`
- `_leave_request_units`
- `get_or_create_leave_balance`
- `credit_leave_for_period`
- `get_employee_leave_balances`

Existing coverage:

- carry-forward and max-balance are covered
- raw accrual cadence, cycle window edge cases, and leave balance snapshot assembly remain light

Recommended test file:

- `backend/apps/timeoff/tests/test_service_balances.py`

### Cluster P5-TO-3: Encashment and request lifecycle

Lines and functions:

- `420-710`
- `process_cycle_end_carry_forward`
- `validate_leave_balance`
- `create_leave_encashment_request`
- `finalize_leave_encashment`
- `create_leave_request`
- `withdraw_leave_request`
- `upsert_on_duty_policy`
- `create_on_duty_request`
- `withdraw_on_duty_request`

Existing coverage:

- carry-forward, validation, encashment have partial coverage
- leave request overlap rules and on-duty lifecycle are still thin

Recommended test files:

- `backend/apps/timeoff/tests/test_service_requests.py`
- `backend/apps/timeoff/tests/test_service_on_duty.py`

### Cluster P5-TO-4: Holiday and calendar rendering

Lines and functions:

- `728-810`
- `create_holiday_calendar`
- `update_holiday_calendar`
- `publish_holiday_calendar`
- `get_employee_holiday_entries`
- `get_employee_calendar_month`

Existing coverage:

- mostly view-level coverage only

Recommended test file:

- `backend/apps/timeoff/tests/test_service_calendars.py`

## Attendance Decomposition

File: `backend/apps/attendance/services.py`

### Cluster P5-AT-1: Workbook parsing and sample generation

Lines and functions:

- `64-308`
- `_parse_date`
- `_parse_time_value`
- `_parse_datetime_value`
- `_load_sheet_rows`
- `_resolve_employee`
- `_build_workbook_bytes`
- `build_attendance_sheet_sample`
- `build_punch_sheet_sample`
- `build_normalized_attendance_workbook`
- `_ensure_xlsx`

Existing coverage:

- import views exercise some of this indirectly
- parser-level error branches and workbook generation are not directly covered

Recommended test file:

- `backend/apps/attendance/tests/test_service_parsers.py`

### Cluster P5-AT-2: Policy, source config, and shift management

Lines and functions:

- `315-435`
- `get_default_attendance_policy`
- `upsert_attendance_policy`
- `create_source_config`
- `update_source_config`
- `get_source_api_key_preview`
- `create_shift`
- `update_shift`
- `assign_shift`

Existing coverage:

- little to no direct service coverage

Recommended test file:

- `backend/apps/attendance/tests/test_service_configuration.py`

### Cluster P5-AT-3: Day summarization core

Lines and functions:

- `444-708`
- `_get_shift_windows`
- `_get_threshold`
- `_weekday_week_off`
- `_get_holiday_for_date`
- `_request_day_fraction`
- `_get_leave_fraction`
- `_get_on_duty_fraction`
- `_get_day_bounds`
- `_pick_interval_from_punches`
- `_get_attendance_override`
- `_summarize_day`
- `recalculate_attendance_day`

Existing coverage:

- `calculate_attendance_day_status` is covered
- the real production summarization path is still mostly uncovered

Recommended test file:

- `backend/apps/attendance/tests/test_service_day_summary.py`

### Cluster P5-AT-4: Employee punch and source ingestion

Lines and functions:

- `783-1045`
- `_extract_remote_ip`
- `_validate_ip`
- `_haversine_distance_meters`
- `_validate_geo`
- `record_employee_punch`
- `ingest_source_punches`
- `create_punch_from_source`

Existing coverage:

- some device/webhook flows exist elsewhere
- direct geo/IP validation branches and source ingest result accounting still need focused assertions

Recommended test file:

- `backend/apps/attendance/tests/test_service_punch_ingestion.py`

### Cluster P5-AT-5: Regularization and org summaries

Lines and functions:

- `1047-1232`
- `upsert_attendance_override`
- `create_regularization_request`
- `withdraw_regularization_request`
- `apply_regularization_status_change`
- `get_org_attendance_dashboard`
- `get_org_attendance_report`
- `list_org_attendance_days`
- `list_attendance_regularizations_for_org`
- `get_payroll_attendance_summary`

Existing coverage:

- attendance import views exist
- regularization state changes and summary aggregations still need direct service coverage

Recommended test file:

- `backend/apps/attendance/tests/test_service_regularization_and_reports.py`

### Cluster P5-AT-6: Attendance and punch imports

Lines and functions:

- `1251-1397`
- `import_attendance_sheet`
- `import_punch_sheet`

Existing coverage:

- import view tests cover high-level API paths
- duplicate rows, invalid rows, incomplete punch normalization, and audit-oriented payload results should be covered at service level

Recommended test file:

- `backend/apps/attendance/tests/test_service_imports.py`

## Recommended Execution Order

Do not try to raise coverage with one giant test file. Use this order:

1. payroll helper/setup slices:
   `test_service_helpers.py`
   `test_service_setup.py`
2. payroll run lifecycle slices:
   `test_service_run_calculation.py`
   `test_service_run_finalization.py`
3. timeoff configuration and balance slices:
   `test_service_configuration.py`
   `test_service_balances.py`
4. timeoff request/on-duty/calendar slices:
   `test_service_requests.py`
   `test_service_on_duty.py`
   `test_service_calendars.py`
5. attendance parser/configuration/day-summary slices:
   `test_service_parsers.py`
   `test_service_configuration.py`
   `test_service_day_summary.py`
6. attendance ingest/regularization/report/import slices:
   `test_service_punch_ingestion.py`
   `test_service_regularization_and_reports.py`
   `test_service_imports.py`

After each slice:

- run the narrow test file
- rerun the per-app coverage command
- only then move to the next slice

## Refactor Trigger

If any one slice still feels too large to test without building huge fixtures, stop and extract pure helpers before adding more tests.

Most likely refactor triggers:

- `payroll.services.calculate_pay_run`
- `attendance.services._summarize_day`
- `attendance.services.import_attendance_sheet`
- `attendance.services.import_punch_sheet`

Those are the best candidates for moving into smaller domain modules if coverage work becomes fixture-heavy or brittle.
