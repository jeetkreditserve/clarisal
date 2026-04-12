# P27 — Statutory Compliance Hotfixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Close the five statutory compliance bugs and two data-completeness gaps discovered in the v4 audit. Every item here affects real money (gratuity underpayment, TDS over-deduction) or causes silent payroll errors (leave lapse not reaching payroll, CAPPED carry-forward never enforced, Telangana PT silently failing). All fixes are small and surgical — no architectural changes required.

**Architecture:** All changes are in `backend/apps/payroll/` and `backend/apps/timeoff/`. No model migrations needed except for the optional LWP deduction base configuration. Every fix must have an exact-value regression test before the task is marked complete.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · pytest · decimal.Decimal

---

## Audit Findings Addressed

- Gratuity eligibility gate uses `_completed_service_years()` (truncates); employees with 4y7m+ incorrectly denied gratuity (Gap #1 — High)
- Annual TDS income projection uses `taxable_monthly × 12` regardless of joining month — over-deducts for mid-year joiners (Gap #2 — Medium)
- Leave lapse does not create `LeaveWithoutPayEntry`; lapsed leave never reaches payroll LWP deduction (Gap #3 — Medium)
- `CAPPED` carry-forward mode has no enforcement task; only `NONE` mode is lapsed (Gap #5 — Medium)
- Telangana ISO alias 'TS' not mapped to seeded state code 'TG' in `PAYROLL_STATE_CODE_ALIASES` (Gap #10 — Low)
- Surcharge seed missing OLD regime 37% tier for FY2024-25 and FY2025-26 (Gap #9 — Low)
- West Bengal Labour Welfare Fund not seeded (Gap #26 — Low)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/payroll/services.py` | Modify | Gratuity gate fix; TDS projection fix; TS alias |
| `backend/apps/payroll/statutory_seed.py` | Modify | Surcharge 37% OLD regime seed; WB LWF seed |
| `backend/apps/timeoff/services.py` | Modify | Leave lapse → `LeaveWithoutPayEntry` cascade; CAPPED carry-forward logic |
| `backend/apps/timeoff/tasks.py` | Modify | Add CAPPED carry-forward enforcement path |
| `backend/apps/payroll/tests/test_services.py` | Modify | TDS projection test (Oct joiner, Jan joiner) |
| `backend/apps/payroll/tests/test_full_and_final.py` | Modify | Gratuity gate 4y7m test |
| `backend/apps/payroll/tests/test_statutory_calculations.py` | Modify | Surcharge 37% OLD regime seed test |
| `backend/apps/payroll/tests/test_statutory_seed.py` | Modify | WB LWF seed test; TS alias test |
| `backend/apps/timeoff/tests/test_services.py` | Modify | Leave lapse → LWP entry test; CAPPED carry-forward test |

---

## Task 1: Fix Gratuity Eligibility Gate

> **Audit finding (Gap #1 — High):** `_completed_service_years()` at `services.py:441–447` uses plain calendar year subtraction (`hiring_year = joining_date.year; exit_year = last_working_day.year; return exit_year - hiring_year`). This truncates — it returns 4 for an employee with 4 years and 7 months of service. The FnF code uses this as the eligibility gate at line 505–509: `if _completed_service_years(employee, last_working_day) >= eligibility_years`. The amount calculation uses `calculate_gratuity_service_years()` which correctly rounds up for >6-month partial years. An employee with 4y7m passes the amount function (→ 5 years eligible) but fails the gate function (→ 4 years, denied). Gratuity is computed as ₹0.

- [x] In `_calculate_fnf_totals` (`services.py:505–513`), replace the eligibility gate:

```python
# BEFORE (services.py:505–509):
service_years = _completed_service_years(employee, last_working_day)
if service_years >= (getattr(settings, 'GRATUITY_ELIGIBILITY_YEARS', 5)):
    gratuity_service_years = calculate_gratuity_service_years(...)
    gratuity = calculate_gratuity_amount(...)

# AFTER:
gratuity_service_years = calculate_gratuity_service_years(
    date_of_joining=employee.date_of_joining,
    last_working_day=last_working_day,
)
eligibility_threshold = getattr(settings, 'GRATUITY_ELIGIBILITY_YEARS', 5)
if gratuity_service_years >= eligibility_threshold:
    gratuity = calculate_gratuity_amount(
        last_basic_salary=monthly_basic_salary,
        years_of_service=gratuity_service_years,
    )
```

- [x] Do NOT remove `_completed_service_years()` — it may be used elsewhere. Remove its use from the gratuity gate only.
- [x] Add exact-value tests in `test_full_and_final.py`:
  - Employee with 4 years 7 months service → `gratuity_service_years = 5` → gratuity > 0
  - Employee with 4 years 5 months service → `gratuity_service_years = 4` → gratuity = 0
  - Employee with exactly 5 years service (to the day) → gratuity > 0
  - Employee with 4 years 6 months 1 day service → gratuity > 0 (crosses the >6-month rounding threshold)
  - Regression: employee with 3 years → gratuity = 0 (gate still blocks)

## Task 2: Fix TDS Annual Income Projection for Mid-Year Joiners

> **Audit finding (Gap #2 — Medium):** `services.py:1710` computes `annual_taxable_gross = (taxable_monthly * Decimal('12.00')).quantize(...)`. This projects a full 12-month income regardless of the month in the fiscal year. The divisor fix (P24 T3) spread the over-projected tax over fewer months, which means a joiner in October is taxed as if earning ₹18L/year (12 × ₹1.5L) but only having 6 months to pay it. The correct approach is to project income over remaining months: `projected_annual = taxable_monthly × months_remaining`.

- [x] Replace the annual taxable gross projection at `services.py:1710`:

```python
# BEFORE:
annual_taxable_gross = (taxable_monthly * Decimal('12.00')).quantize(Decimal('0.01'))

# AFTER:
months_remaining = _months_remaining_in_fiscal_year(pay_run.period_month)
annual_taxable_gross = (taxable_monthly * Decimal(str(months_remaining))).quantize(Decimal('0.01'))
```

- [x] Verify that `_months_remaining_in_fiscal_year` is already defined at `services.py:170–175` and is importable from the same scope. It is — no import change needed.
- [x] Verify the downstream calculation chain: `annual_taxable_gross` flows into `calculate_taxable_income_with_investments()` (which applies investment deductions and standard deduction) and then into `calculate_income_tax_with_rebate()`. These functions take a raw income figure and apply their own logic — the change is purely in the input value.
- [x] Add tests in `test_services.py`:
  - April joiner (month 4): `months_remaining = 12`; `annual_taxable_gross = monthly × 12`; verify this matches the existing baseline
  - October joiner (month 10): `months_remaining = 6`; `annual_taxable_gross = monthly × 6`; verify `income_tax_monthly = tax(gross × 6) / 6`
  - February payroll (month 2): `months_remaining = 2`; `annual_taxable_gross = monthly × 2`
  - March payroll (month 3): `months_remaining = 1`; full annual tax paid in final month
  - Verify that a ₹1,50,000/month October joiner (new regime, FY25-26) has monthly TDS ≈ `tax(₹9,00,000) / 6`, not `tax(₹18,00,000) / 6`

## Task 3: Fix Leave Lapse → LWP Cascade

> **Audit finding (Gap #3 — Medium):** `process_cycle_end_lapse` (`timeoff/services.py:491–526`) creates a `LeaveBalanceLedgerEntry` with `entry_type=EXPIRY` but does not create a `LeaveWithoutPayEntry`. The `LEAVE_LAPSE` source value exists in `LeaveWithoutPayEntrySource` (timeoff/models.py:76) but is never written. Leave lapse therefore never feeds into payroll LWP deduction.

- [x] In `process_cycle_end_lapse` (`timeoff/services.py`), after the ledger EXPIRY entry is created, check whether the lapse should generate a `LeaveWithoutPayEntry`:

```python
# After the LeaveBalanceLedgerEntry creation:
# Determine if this leave type maps to LWP in payroll
if leave_type.is_loss_of_pay:
    # Lapsed LWP-type leave creates an LWP entry for the next payroll run
    LeaveWithoutPayEntry.objects.create(
        employee=employee,
        leave_type=leave_type,
        source=LeaveWithoutPayEntrySource.LEAVE_LAPSE,
        units=amount_to_expire,
        effective_date=balance.cycle_end,
        notes=f'Leave lapse at cycle end {balance.cycle_end}',
        status=LeaveWithoutPayEntryStatus.ACTIVE,
    )
```

- [x] Only create `LeaveWithoutPayEntry` when `leave_type.is_loss_of_pay` is `True`. Non-LWP leave types (PL, CL, SL etc.) should lapse without generating an LWP entry — lapsing accrued leave does not mean the employee worked unpaid.
- [x] Import `LeaveWithoutPayEntry`, `LeaveWithoutPayEntrySource`, `LeaveWithoutPayEntryStatus` at the top of the function or file scope.
- [x] Add tests in `test_services.py` (timeoff):
  - LWP-type leave lapses → `LeaveWithoutPayEntry` created with correct units and `source=LEAVE_LAPSE`
  - Non-LWP leave (PL) lapses → no `LeaveWithoutPayEntry` created
  - Idempotency: calling lapse twice does not create a second entry (the existing `EXPIRY` ledger check prevents double-run, but verify `LeaveWithoutPayEntry` also is not duplicated — add a `unique_together` guard or re-query before creating)

## Task 4: Add CAPPED Carry-Forward Enforcement

> **Audit finding (Gap #5 — Medium):** The leave lapse Celery task (`timeoff/tasks.py`) only targets `CarryForwardMode.NONE`. Balances with `CarryForwardMode.CAPPED` carry-forward must have their balance truncated to `max_carry_forward_days` at cycle end — excess days above the cap should lapse. No such logic exists.

- [x] In `timeoff/services.py`, add a new function `process_cycle_end_cap(employee, balance)`:

```python
def process_cycle_end_cap(employee, balance):
    """
    At cycle end for CAPPED carry-forward leave types, reduce balance to the cap.
    Days above the cap are lapsed (expired) and credited to the next cycle up to the cap only.
    """
    leave_type = balance.leave_type
    cap = leave_type.max_carry_forward_days  # Decimal; must not be None for CAPPED mode

    if cap is None:
        # CAPPED mode with no cap value — treat as UNLIMITED, skip
        return

    # Compute current available balance
    available = (
        balance.opening_balance
        + balance.carried_forward_amount
        + balance.credited_amount
        - balance.used_amount
        - balance.pending_amount
    ).quantize(Decimal('0.01'))

    if available <= cap:
        # Within cap — no action needed
        return

    excess = (available - cap).quantize(Decimal('0.01'))

    # Create an EXPIRY ledger entry for the excess
    LeaveBalanceLedgerEntry.objects.create(
        balance=balance,
        entry_type=LeaveBalanceLedgerEntryType.EXPIRY,
        units=-excess,
        effective_date=balance.cycle_end,
        notes=f'Carry-forward cap: {cap} days allowed, {excess} days lapsed',
    )
    balance.credited_amount = max(ZERO, balance.credited_amount - excess)
    balance.save(update_fields=['credited_amount', 'modified_at'])
```

- [x] In `timeoff/tasks.py`, extend `run_leave_lapse_for_all_active_cycles` to handle CAPPED mode:

```python
# After processing CarryForwardMode.NONE balances:
capped_balances = LeaveBalance.objects.filter(
    leave_type__carry_forward_mode=CarryForwardMode.CAPPED,
    employee__status=EmployeeStatus.ACTIVE,
    cycle_end__lt=today,
    cycle_end__isnull=False,
).select_related('leave_type', 'employee')

for balance in capped_balances.iterator():
    process_cycle_end_cap(balance.employee, balance)
```

- [x] Add tests in `test_services.py` (timeoff):
  - Employee has 15 PL days, cap is 10 → 5 days lapsed; balance after = 10
  - Employee has 8 PL days, cap is 10 → no lapse; balance unchanged
  - Employee has exactly 10 days, cap is 10 → no lapse
  - Idempotency: running cap enforcement twice produces the same result

## Task 5: Fix Telangana 'TS' State Code Alias

> **Audit finding (Gap #10 — Low):** `PAYROLL_STATE_CODE_ALIASES` in `services.py:93–98` maps `'OR': 'OD'` and `'CG': 'CT'` but does not map `'TS': 'TG'`. The ISO 3166-2 code for Telangana is 'TS'; the seed uses 'TG' (an older informal code). Any office location with `state_code = 'TS'` will fail PT and LWF lookups with a `ValueError: No active professional tax rule is configured for state TS`.

- [x] In `services.py`, add the alias in `PAYROLL_STATE_CODE_ALIASES`:

```python
PAYROLL_STATE_CODE_ALIASES: dict[str, str] = {
    'OR': 'OD',   # Odisha — ISO uses OD, some address databases use OR
    'CG': 'CT',   # Chhattisgarh — ISO uses CT, some use CG
    'TS': 'TG',   # Telangana — ISO uses TS, seed uses TG
}
```

- [x] Verify `_canonicalize_payroll_state_code` (which uses this dict) is called before all PT/LWF lookups.
- [x] Add a test in `test_statutory_seed.py`:
  - `_canonicalize_payroll_state_code('TS')` returns `'TG'`
  - A payroll run for an employee in a Telangana office (`state_code='TS'`) correctly applies TG PT rule without raising `ValueError`

## Task 6: Fix Surcharge Seed — Add OLD Regime 37% Tier

> **Audit finding (Gap #9 — Low):** `seed_surcharge_rules()` in `statutory_seed.py:715–760` seeds surcharge tiers for both fiscal years and both regimes, but omits the 37% tier for the OLD regime. The OLD regime retains 37% above ₹5 crore (Finance Act 2023 only abolished it for the NEW regime). If the codebase ever switches the payroll calculation to use the DB-backed `get_surcharge_tiers_from_db()` instead of the hardcoded constants, OLD regime high-income employees will be silently under-charged surcharge.

- [x] In `statutory_seed.py`, extend the `surcharge_data` list inside `seed_surcharge_rules()` to include the 37% tier for OLD regime:

```python
# For FY2024-2025 and FY2025-2026, OLD regime:
{
    'fiscal_year': '2024-2025',
    'tax_regime': 'OLD',
    'income_threshold': Decimal('50000000.00'),  # ₹5 crore
    'surcharge_rate_percent': Decimal('37.00'),
    'effective_from': date(2023, 4, 1),
},
{
    'fiscal_year': '2025-2026',
    'tax_regime': 'OLD',
    'income_threshold': Decimal('50000000.00'),
    'surcharge_rate_percent': Decimal('37.00'),
    'effective_from': date(2025, 4, 1),
},
```

- [x] Ensure `unique_together` constraint on `SurchargeRule` (`fiscal_year`, `tax_regime`, `income_threshold`) is respected — use `get_or_create` in the seed command.
- [x] Add a test in `test_statutory_seed.py`:
  - After running `seed_statutory_masters`, `SurchargeRule.objects.filter(fiscal_year='2025-2026', tax_regime='OLD', surcharge_rate_percent=37).exists()` returns `True`
  - `SurchargeRule.objects.filter(fiscal_year='2025-2026', tax_regime='NEW', surcharge_rate_percent=37).exists()` returns `False` (must not exist for NEW regime)

## Task 7: Seed West Bengal LWF

> **Audit finding (Gap #26 — Low):** West Bengal is a significant state for LWF coverage. WB LWF rates: Employee ₹3/month, Employer ₹6/month. This is a simple seed addition.

- [x] In `statutory_seed.py`, add a WB LWF entry to the `LABOUR_WELFARE_FUND_RULES` list:

```python
{
    'country_code': 'IN',
    'state_code': 'WB',
    'state_name': 'West Bengal',
    'wage_basis': StatutoryIncomeBasis.MONTHLY,
    'deduction_frequency': StatutoryDeductionFrequency.ANNUAL,
    'effective_from': date(2018, 1, 1),
    'source_label': 'West Bengal Labour Welfare Fund annual contribution',
    'source_url': 'https://labourwb.gov.in/',
    'notes': 'Annual contribution collected in December. Employee ₹3, Employer ₹6.',
    'contributions': [
        {
            'min_wage': None,
            'max_wage': None,
            'employee_contribution': Decimal('3.00'),
            'employer_contribution': Decimal('6.00'),
            'applicable_months': [12],
        },
    ],
},
```

- [x] Update the `seed_statutory_masters` management command to include WB in its output summary.
- [x] Add a test in `test_statutory_seed.py`:
  - After seeding, a `LabourWelfareFundRule` with `state_code='WB'` exists
  - A payroll run for an employee in a WB office in December produces `lwf_employee = 3.00`, `lwf_employer = 6.00`
  - A payroll run for a WB employee in a non-December month produces `lwf_employee = 0.00` (annual-only)
