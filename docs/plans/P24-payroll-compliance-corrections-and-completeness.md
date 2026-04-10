# P24 — Payroll Compliance Corrections & Completeness

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the three critical/high statutory bugs discovered in the v3 audit (87A rebate threshold for FY25-26, FnF leave encashment hardcoded to zero, TDS monthly allocation ignoring remaining months), and close the compliance completeness gaps left open after `P14` and `P15` (missing PT states, missing LWF states, surcharge tiers not DB-configurable, Form 24Q not FVU-validated, Form 12BB absent, ESI branch code missing, PT/LWF performance).

**Architecture:** All changes are in `backend/apps/payroll/`. Statutory parameter changes go into `statutory.py` and `statutory_seed.py`. Service-layer fixes go into `services.py`. New filing artifacts go into `filings/`. Every fix must be covered by an exact-value regression test before shipping.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · Celery · pytest · decimal.Decimal · WeasyPrint (Form 12BB)

---

## Audit Findings Addressed

- 87A rebate threshold/max hardcoded to FY24-25 values (₹7L / ₹25K) — wrong for FY25-26 new regime (₹12L / ₹60K)
- FnF leave encashment passes `leave_days=ZERO` — every settlement underpays
- TDS monthly allocation divides annual tax by 12 regardless of joining month or FY position
- Professional Tax rules missing for GJ, HR, PB, OR, RJ, HP, CG, JH
- Labour Welfare Fund not seeded for AP, TG, MP, HR, OR
- Surcharge tiers hardcoded in `statutory.py` — cannot be updated without deployment
- Form 24Q XML not validated against NSDL FVU schema
- Form 12BB not generated from `InvestmentDeclaration` records
- ESI branch code absent from Organisation model and challan export
- PF opt-out does not verify new joiner / never-been-EPF-member status
- PT/LWF rules queried per-employee per payroll run — no request-scoped cache

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/payroll/statutory.py` | Modify | Per-FY rebate parameters, surcharge tier lookup |
| `backend/apps/payroll/statutory_seed.py` | Modify | PT seed for 8 more states; LWF seed for 5 more states; surcharge tier seed |
| `backend/apps/payroll/models.py` | Modify | `SurchargeRule` model; `PayrollTaxSlabSet` linkage; ESI branch code on Organisation proxy |
| `backend/apps/payroll/services.py` | Modify | FnF leave encashment fix; TDS remaining-months fix; PT/LWF cache; PF opt-out guard |
| `backend/apps/payroll/filings/form12bb.py` | Create | Form 12BB PDF generator |
| `backend/apps/payroll/views.py` | Modify | Form 12BB download endpoint |
| `backend/apps/payroll/org_urls.py` | Modify | Register Form 12BB route |
| `backend/apps/organisations/models.py` | Modify | Add `esi_branch_code` to Organisation |
| `backend/apps/organisations/serializers.py` | Modify | Expose `esi_branch_code` in org settings |
| `backend/apps/payroll/filings/esi.py` | Modify | Include branch code in challan export |
| `backend/apps/payroll/management/commands/seed_statutory_masters.py` | Modify | Seed new states and surcharge rules |
| `backend/apps/payroll/migrations/0015_*.py` | Create | Schema for SurchargeRule; ESI branch code |
| `backend/apps/payroll/tests/test_statutory_calculations.py` | Modify | 87A FY25-26 test; surcharge FY-specific test |
| `backend/apps/payroll/tests/test_services.py` | Modify | TDS remaining-months test (Oct joiner); PT/LWF cache test |
| `backend/apps/payroll/tests/test_full_and_final.py` | Modify | FnF leave encashment test |
| `backend/apps/payroll/tests/test_statutory_seed.py` | Modify | New state coverage tests |
| `backend/apps/payroll/tests/test_filings.py` | Modify | Form 12BB test; ESI branch code test |

---

## Task 1: Fix 87A Rebate for FY25-26

> **Audit finding (§7.5, Gap #1 — Critical):** `INDIA_REBATE_87A_THRESHOLD = Decimal('700000.00')` and `INDIA_REBATE_87A_MAX = Decimal('25000.00')` in `statutory.py` are correct for FY24-25 but wrong for FY25-26 new regime (Finance Act 2025 raised threshold to ₹12,00,000 and max rebate to ₹60,000). Any employee earning ₹8L–₹12L on new regime is currently over-deducted TDS.

- [x] Replace the single `INDIA_REBATE_87A_THRESHOLD` and `INDIA_REBATE_87A_MAX` constants with a per-fiscal-year, per-regime lookup dict in `statutory.py`:

```python
# statutory.py
REBATE_87A_PARAMS: dict[tuple[str, str], tuple[Decimal, Decimal]] = {
    # (fiscal_year, regime): (threshold, max_rebate)
    ("2024-2025", "NEW"): (Decimal("700000.00"), Decimal("25000.00")),
    ("2024-2025", "OLD"): (Decimal("500000.00"), Decimal("12500.00")),
    ("2025-2026", "NEW"): (Decimal("1200000.00"), Decimal("60000.00")),
    ("2025-2026", "OLD"): (Decimal("500000.00"), Decimal("12500.00")),
}

def get_rebate_87a_params(fiscal_year: str, regime: str) -> tuple[Decimal, Decimal]:
    return REBATE_87A_PARAMS.get(
        (fiscal_year, regime.upper()),
        (Decimal("500000.00"), Decimal("12500.00")),  # safe fallback for old regime
    )
```

- [x] Update `calculate_income_tax_with_rebate` in `statutory.py` to accept `rebate_threshold` and `rebate_max` parameters instead of reading the module-level constants.
- [x] Update every call site in `services.py` to derive `rebate_threshold` and `rebate_max` via `get_rebate_87a_params(fiscal_year, regime)` before calling `calculate_income_tax_with_rebate`.
- [x] Add exact-value tests in `test_statutory_calculations.py`:
  - FY25-26 new regime, income ₹10L → rebate = min(computed_tax, ₹60,000); net tax = 0
  - FY25-26 new regime, income ₹12L → rebate = min(computed_tax, ₹60,000); net tax = 0
  - FY25-26 new regime, income ₹12.01L → no rebate; tax > 0
  - FY24-25 new regime, income ₹7L → rebate applies; FY24-25 new regime, income ₹7.01L → no rebate
  - Old regime both FYs: threshold ₹5L unchanged

## Task 2: Fix FnF Leave Encashment

> **Audit finding (§5.5, Gap #2 — Critical):** `_calculate_fnf_totals` in `services.py` line 413 calls `calculate_leave_encashment_amount(leave_days=ZERO, ...)`. The employee's actual encashable leave balance is never fetched. Every FnF settlement underpays by the full encashable balance.

- [x] In `_calculate_fnf_totals`, before computing `leave_encashment`, call `timeoff.services.get_employee_leave_balances(employee)` (or the equivalent query) to retrieve balances grouped by leave type.
- [x] Filter for leave types where `is_encashable=True` and sum the available units as `encashable_days`.
- [x] Pass `encashable_days` as `leave_days` to `calculate_leave_encashment_amount`.
- [x] Ensure that the encashment amount is capped by the organisation's encashment policy if one exists (e.g., max encashable days per policy).
- [x] Add tests in `test_full_and_final.py`:
  - Employee with 10 PL days at ₹500/day basic → FnF leave encashment = ₹500 * 10 / 26 * 15 (or direct basic/26 * days per policy)
  - Employee with 0 encashable leave → encashment = 0 (regression guard)
  - Employee with mixed encashable/non-encashable leave types → only encashable types counted

## Task 3: Fix TDS Monthly Allocation for Mid-Year Joiners

> **Audit finding (§7.9, Gap #3 — High):** `income_tax = annual_tax_total / Decimal('12.00')` in `services.py` line 1497 divides by 12 for all employees. An employee joining in October should have annual TDS divided by remaining months in the FY (6), not 12.

- [x] In the TDS calculation section of `calculate_payroll_run_item`, derive `months_remaining_in_fy` from `period_month`:

```python
# FY runs April (4) to March (3)
def months_remaining_in_fy(period_month: int) -> int:
    """Number of months remaining including the current period month."""
    if period_month <= 3:          # Jan, Feb, Mar — still current FY
        return 3 - period_month + 1
    else:                          # Apr–Dec
        return 12 - period_month + 3 + 1  # = 16 - period_month
```

- [x] Replace `/ Decimal('12.00')` with `/ Decimal(str(months_remaining_in_fy(period_month)))`.
- [x] Ensure `period_month` is derived from the `PayrollRun.period_start` date and is already available in the computation context; if not, pass it explicitly.
- [x] Add tests in `test_services.py`:
  - April joiner (month 1): divisor = 12
  - October joiner (month 7): divisor = 6; verify monthly TDS = annual_tax / 6
  - February payroll (month 11): divisor = 2
  - March payroll (month 12): divisor = 1 (full annual tax in final month)
  - Employee with salary revision mid-year: verify TDS recalculates using remaining months from revision month

## Task 4: Expand Professional Tax to 8 More States

> **Audit finding (§7.3, Gap #7 — High):** PT rules exist for MH, KA, TN, WB, AP, TG, MP. The following PT-applicable states are missing: Gujarat (GJ), Haryana (HR), Punjab (PB), Odisha (OR), Rajasthan (RJ), Himachal Pradesh (HP), Chhattisgarh (CG), Jharkhand (JH).

- [x] Research and add correct PT slab data for each state in `statutory_seed.py`. Cross-reference Simpliance / Greytip PT state list for current rates. Key slabs:
  - **GJ**: ₹200/month for salary ≥ ₹12,000; annual cap ₹2,400
  - **HR**: ₹200/month for salary ≥ ₹25,000 (Haryana PT levied at district level — note this)
  - **PB**: ₹200/month for salary > ₹20,833; waiver for females
  - **OR**: ₹200/month for salary ≥ ₹25,000
  - **RJ**: No PT (Rajasthan abolished PT in 2017 — add as explicit "no PT" entry to avoid lookup errors)
  - **HP**: ₹200/month for salary ≥ ₹10,000
  - **CG**: ₹200/month for salary ≥ ₹25,000
  - **JH**: ₹100/month for salary ₹25,000–₹41,666; ₹150 above
- [x] Update `seed_statutory_masters` management command to include the new states.
- [x] Add tests verifying PT amount at threshold boundaries for each new state.
- [x] Document Rajasthan's explicit "no PT" sentinel so payroll runs in RJ do not raise a "no PT rule found" exception.

## Task 5: Expand Labour Welfare Fund to 5 More States

> **Audit finding (§7.4, Gap #23 — Low/Medium):** LWF seeded only for MH and KA. States with LWF that are missing: AP, TG, MP, HR, OR.

- [x] Add LWF seed entries for:
  - **AP**: Employee ₹40, Employer ₹60, annual (December)
  - **TG**: Employee ₹40, Employer ₹60, annual (December)
  - **MP**: Employee ₹10, Employer ₹30, annual (December); applies to wages ≤ ₹10,000 (verify current slabs)
  - **HR**: Employee ₹0.25/day, Employer ₹0.75/day — or equivalent annual equivalent (verify current slabs)
  - **OR**: Employee ₹20, Employer ₹40, annual (December)
- [x] Update `seed_statutory_masters` to include new LWF entries.
- [x] Add tests verifying LWF contribution amounts and frequency for each new state.

## Task 6: Make Surcharge Tiers DB-Configurable Per Fiscal Year

> **Audit finding (§7.7, Gap #8 — High):** `OLD_REGIME_SURCHARGE_TIERS` and `NEW_REGIME_SURCHARGE_TIERS` are hardcoded tuples in `statutory.py`. If the government changes surcharge tiers in a future Finance Act, a code deployment is required.

- [x] Add a `SurchargeRule` model:

```python
class SurchargeRule(models.Model):
    fiscal_year = models.CharField(max_length=9)   # e.g., "2025-2026"
    tax_regime = models.CharField(max_length=10, choices=[("OLD", "Old"), ("NEW", "New")])
    income_threshold = models.DecimalField(max_digits=14, decimal_places=2)
    surcharge_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()

    class Meta:
        unique_together = [("fiscal_year", "tax_regime", "income_threshold")]
        ordering = ["fiscal_year", "tax_regime", "income_threshold"]
```

- [x] Add seed data in `statutory_seed.py` for FY24-25 and FY25-26 surcharge tiers (both regimes).
- [x] Update `calculate_income_tax_with_rebate` (and/or the surcharge resolution helper) to query `SurchargeRule` for the relevant `fiscal_year` and `tax_regime`, falling back to `statutory.py` hardcoded constants only if no DB rows exist (for bootstrapping safety).
- [x] Update `seed_statutory_masters` to seed `SurchargeRule` rows.
- [x] Add CT UI to view (read-only) seeded surcharge rules alongside the existing tax slab set viewer.
- [x] Cover DB-driven surcharge calculation at all threshold boundaries with exact-value tests. Added 6 tests in `test_statutory_calculations.py` covering DB tier retrieval, fallback behavior, exact value calculation, marginal relief, and old regime calculation.

## Task 7: Validate Form 24Q Against NSDL FVU Schema

> **Audit finding (§7.10, Gap #15 — Medium):** Form 24Q XML has not been validated against NSDL's official FVU (File Validation Utility) schema. The field names and nesting match common templates but are not verified against the current FVU version.

- [ ] Download NSDL FVU 7.x schema documentation and compare field names, order, and data types against `backend/apps/payroll/filings/form24q.py`.
- [ ] Fix any field name mismatches, missing mandatory fields, or incorrect data types found in the schema comparison.
- [ ] Add a golden-file test in `test_filings.py` that generates Form 24Q XML for a fixed fixture and compares it byte-for-byte against a known-good expected output file stored at `backend/apps/payroll/tests/fixtures/form24q_expected.xml`.
- [ ] Document any known deviations from the FVU schema (e.g., fields that require challan linkage data not yet available in the system) as explicit `TODO` comments with issue references.
- [ ] Note in the plan that physical FVU 7.x tool validation (running the Java JAR against generated output) should be performed manually before customer use — add this as a release checklist item.

## Task 8: Generate Form 12BB from Investment Declarations

> **Audit finding (Gap #16 — Medium):** No Form 12BB PDF is generated from `InvestmentDeclaration` records. Employees and HR need Form 12BB as a submission declaration to the employer. Zoho People and Keka both offer this.

- [x] Create `backend/apps/payroll/filings/form12bb.py` with `generate_form12bb_pdf(employee, fiscal_year)` function using WeasyPrint.
  - Section A: HRA with landlord details and PAN
  - Section B: LTA with travel details
  - Section C: Interest on home loan (Section 24)
  - Section D: Chapter VI-A deductions (80C, 80D, 80G, 80TTA, OTHER)
  - Declaration with date and employee signature block
  - Summary box with totals per section
- [x] Cover PDF generation (valid PDF bytes), section population from declaration records, empty-declaration blocking, and edge case with 4 tests in `test_filings.py`.
- [ ] Add an employee self-service endpoint `GET /api/me/payroll/form-12bb/<fiscal_year>/` that returns the PDF.
- [ ] Add an org-admin bulk download endpoint that generates Form 12BB PDFs for all employees in a fiscal year as a ZIP.

## Task 9: Add ESI Branch Code and PF Opt-Out Guard

> **Audit findings (Gaps #22 and #21 — Low):** ESI challan export lacks branch code (required for ESIC portal matching). PF opt-out does not verify new joiner / never-been-EPF-member status.

**ESI branch code:**
- [x] Add `esi_branch_code = models.CharField(max_length=20, blank=True)` to `Organisation` model.
- [x] Expose `esi_branch_code` in the org settings serializer and org-admin profile/settings page.
- [x] In `filings/esi.py`, include `esi_branch_code` in the challan header row. Add a validation warning (not a hard block) if `esi_branch_code` is blank when generating an ESI challan.
- [x] Add a test verifying the branch code appears in generated ESI challan output.

**PF opt-out new joiner guard:**
- [x] In the PF opt-out validation path in `services.py`, add a check that `is_pf_opted_out` is only accepted when the employee's `date_of_joining` is after the PF wage ceiling introduction OR when the org explicitly marks the employee as a "never EPF member" (add `is_epf_exempt` boolean to `CompensationAssignment`).
- [x] Raise a validation error if `is_pf_opted_out=True` is set for an employee who joined before ₹15,000 ceiling was introduced (pre-September 2014) without the explicit `is_epf_exempt` override.
- [x] Document the EPFO circular reference for opt-out eligibility in a code comment.

## Task 10: Add PT/LWF Rule Request-Scoped Cache

> **Audit finding (Gap #19 — Medium):** PT and LWF rules are queried once per employee per payroll run. For an org with 1,000 employees, each run issues 1,000+ identical PT/LWF DB queries.

- [x] In `calculate_pay_run` (the outer loop in `services.py`), pre-fetch all active `ProfessionalTaxRule` and `LabourWelfareFundRule` records for relevant state codes before the employee loop begins.
- [x] Pass the pre-fetched rules as a dict keyed by `state_code` into `calculate_payroll_run_item` or the PT/LWF resolution helpers.
- [x] Update `_resolve_professional_tax_amount` and `_resolve_lwf_contribution` to accept the pre-fetched cache dict as an optional parameter, falling back to a DB query only if the cache is absent (for direct/unit test use).
- [x] Add a test that runs a payroll run for 10 employees in the same state and verifies that `ProfessionalTaxRule.objects.filter` is called at most once (use `django.test.utils.CaptureQueriesContext` or `assertNumQueries`).
