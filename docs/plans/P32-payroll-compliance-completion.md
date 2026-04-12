# P32 — Payroll Compliance Completion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Close the two remaining payroll compliance gaps that require deeper calculation changes: (1) split EPF employer contributions into EPS and EPF sub-components so the ECR export is EPFO-compliant, and (2) compute correct FnF income tax by applying Section 10(10) gratuity exemption and Section 10(10AA) leave encashment exemption before calculating TDS on the settlement amount.

**Architecture:** Both changes are in `backend/apps/payroll/`. EPF split adds two fields to the EPF calculation return dict and updates the ECR export + run-item model. FnF TDS adds a new `_calculate_fnf_tds` function that applies statutory exemptions before passing to the existing `calculate_income_tax_with_rebate()` pipeline.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · React 19 · TypeScript · pytest · decimal.Decimal

---

## Audit Findings Addressed

- `calculate_epf_contributions()` returns a single `employer` figure without splitting EPS (8.33%, capped ₹1,250/month) and EPF (3.67%) sub-components; ECR export affected (Gap #11 — Low)
- FnF TDS on gratuity and leave encashment not computed — Section 10(10) and 10(10AA) exemptions not applied (Gap #27 — Low)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/payroll/statutory.py` | Modify | `calculate_epf_contributions()` returns split EPS/EPF employer figures |
| `backend/apps/payroll/models.py` | Modify | Add `eps_employer`, `epf_employer` to `PayrollRunItem` |
| `backend/apps/payroll/migrations/XXXX_payrollrunitem_eps_epf_split.py` | Create | Migration for split fields |
| `backend/apps/payroll/serializers.py` | Modify | Expose `eps_employer`, `epf_employer` in run item serializer |
| `backend/apps/payroll/filings/ecr.py` | Modify | Use split fields in ECR row generation |
| `backend/apps/payroll/services.py` | Modify | Add `_calculate_fnf_tds()` function; integrate into `_calculate_fnf_totals` |
| `backend/apps/payroll/tests/test_statutory_calculations.py` | Modify | EPF split tests |
| `backend/apps/payroll/tests/test_full_and_final.py` | Modify | FnF TDS exemption tests |
| `frontend/src/pages/org/PayrollRunDetailPage.tsx` | Modify | Show `eps_employer` + `epf_employer` in expandable row breakdown |

---

## Task 1: Split EPF Employer into EPS and EPF Components

> **Finding (Gap #11 — Low):** `calculate_epf_contributions()` in `statutory.py:213–227` returns a single `employer` figure (12% of PF wage, capped at ₹1,800). The EPFO ECR format requires the employer contribution split into:
> - **EPS (Employee Pension Scheme)**: 8.33% of PF wage, capped at ₹1,250/month
> - **EPF (Employer)**: Employer total minus EPS = 3.67% of PF wage (uncapped, but total capped at ₹1,800)
> If ECR uses the unsplit total, ECR submissions will be rejected by EPFO.

### statutory.py

- [x] Read `statutory.py:213–227` — understand the current return structure.
- [x] Modify `calculate_epf_contributions()` to return a dict that includes the split:

```python
def calculate_epf_contributions(pf_wage: Decimal, ...) -> dict:
    # Employee contribution
    employee_epf = min(pf_wage * Decimal('0.12'), Decimal('1800.00'))

    # Employer contributions
    # EPS: 8.33% of PF wage, capped at ₹1,250/month
    eps_employer = min(pf_wage * Decimal('0.0833'), Decimal('1250.00'))
    # EPF employer = total employer (12%) - EPS
    total_employer = min(pf_wage * Decimal('0.12'), Decimal('1800.00'))
    epf_employer = (total_employer - eps_employer).quantize(Decimal('0.01'))

    # EDLI: 0.5% of PF wage, capped at ₹75/month
    edli = min(pf_wage * Decimal('0.005'), Decimal('75.00')).quantize(Decimal('0.01'))

    # EPF admin charges: 0.5% of PF wage, min ₹500/month
    epf_admin = max(pf_wage * Decimal('0.005'), Decimal('500.00')).quantize(Decimal('0.01'))

    return {
        'employee': employee_epf.quantize(Decimal('0.01')),
        'employer': total_employer.quantize(Decimal('0.01')),  # Keep for backward compat
        'eps_employer': eps_employer.quantize(Decimal('0.01')),
        'epf_employer': epf_employer,
        'edli': edli,
        'epf_admin': epf_admin,
        'total_employer_cost': (total_employer + edli + epf_admin).quantize(Decimal('0.01')),
    }
```

- [x] The existing `employer` key is retained for backward compatibility with all callers that only use the total.

### models.py

- [x] Add two new fields to `PayrollRunItem`:

```python
eps_employer = models.DecimalField(
    max_digits=10, decimal_places=2, default=Decimal('0.00'),
    help_text='Employer EPS contribution (8.33% of PF wage, capped ₹1,250)',
)
epf_employer = models.DecimalField(
    max_digits=10, decimal_places=2, default=Decimal('0.00'),
    help_text='Employer EPF contribution (3.67% of PF wage = total employer - EPS)',
)
```

- [x] Create the migration with `default=Decimal('0.00')` for existing rows.

### services.py

- [x] In the payroll run calculation loop, after calling `calculate_epf_contributions()`, store the split values:

```python
epf = calculate_epf_contributions(pf_wage=pf_wage, ...)
run_item.epf_employee = epf['employee']
run_item.epf_employer = epf['epf_employer']
run_item.eps_employer = epf['eps_employer']
```

### ECR Export

- [x] Read `filings/ecr.py` — locate the ECR row generation.
- [x] The EPFO ECR format requires separate columns for employee EPF, employer EPF (3.67%), and EPS (8.33%).
- [x] Update ECR row generation to use `run_item.eps_employer` and `run_item.epf_employer` instead of computing from the total.
- [x] Verify ECR column ordering matches EPFO RPU specification (standard: UAN, member name, gross wages, EPF wages, EPS wages, EPF contrib employee, EPF contrib employer, EPS contrib employer, EPF admin charges, EDLI contrib, EDLI admin).

### Tests

- [x] Add tests in `test_statutory_calculations.py`:
  - PF wage ₹15,000 → EPS employer = ₹1,249.50 (≤ ₹1,250 cap), EPF employer = ₹550.50, employee EPF = ₹1,800
  - PF wage ₹6,500 → EPS employer = ₹541.45, EPF employer = ₹238.55
  - PF wage ₹30,000 → EPS employer = ₹1,250 (capped), EPF employer = ₹550, employee EPF = ₹1,800 (capped)
  - `eps_employer + epf_employer == employer` (split adds up to total) for all test cases

## Task 2: FnF TDS with Section 10(10) and 10(10AA) Exemptions

> **Finding (Gap #27 — Low):** `_calculate_fnf_totals()` in `services.py` computes gratuity and leave encashment amounts but does not calculate income tax on the FnF settlement. The FnF payslip shows gross amounts without TDS. Keka and Zoho Payroll auto-compute FnF tax including statutory exemptions.

### Exemption Rules

- **Section 10(10) — Gratuity Exemption:**
  - Government employees: fully exempt
  - Non-government employees: exempt up to the least of:
    1. Actual gratuity received
    2. `(15/26) × last_basic_salary × years_of_service` (same formula as gratuity amount)
    3. ₹20,00,000 (₹20 lakh ceiling — Finance Act 2023)
  - For salaried non-government employees the formula and amount are identical, so gratuity is always fully exempt up to ₹20L.

- **Section 10(10AA) — Leave Encashment Exemption:**
  - Government employees: fully exempt
  - Non-government employees: exempt up to the least of:
    1. Actual leave encashment received
    2. `(last_basic_salary / 30) × earned_leave_days` (capped at 30 days/year × years of service)
    3. ₹3,00,000 (₹3 lakh ceiling — old limit; raised to ₹25,00,000 by Finance Act 2023)
    4. Average salary (monthly) × 10 months

### Implementation

- [x] Add a new function `_calculate_fnf_tds(fnf_components, employee, pay_run)` in `services.py`:

```python
def _calculate_fnf_tds(
    *,
    gratuity: Decimal,
    leave_encashment: Decimal,
    other_taxable_income: Decimal,  # notice pay, NFNL encashment, etc.
    employee: Employee,
    last_working_day: date,
    tax_regime: str,  # 'OLD' or 'NEW'
    existing_ytd_tds: Decimal,  # TDS already deducted this fiscal year
) -> Decimal:
    """
    Calculate TDS on Full and Final settlement.
    Returns the incremental TDS amount to deduct on the FnF payslip.
    """
    fiscal_year = _get_fiscal_year(last_working_day)

    # Section 10(10) — Gratuity exemption
    gratuity_exempt = min(gratuity, Decimal('2000000.00'))  # ₹20L ceiling
    gratuity_taxable = max(ZERO, gratuity - gratuity_exempt)

    # Section 10(10AA) — Leave encashment exemption (₹25L ceiling post-FA-2023)
    leave_encashment_exempt = min(leave_encashment, Decimal('2500000.00'))
    leave_encashment_taxable = max(ZERO, leave_encashment - leave_encashment_exempt)

    # Total taxable FnF income
    total_taxable_fnf = gratuity_taxable + leave_encashment_taxable + other_taxable_income

    # Annual tax on FnF income (projected with existing YTD income)
    ytd_income = _get_ytd_taxable_income(employee, fiscal_year)
    total_annual_income = ytd_income + total_taxable_fnf

    # Calculate total tax liability for the year
    annual_tax = calculate_income_tax_with_rebate(
        taxable_income=total_annual_income,
        fiscal_year=fiscal_year,
        tax_regime=tax_regime,
        age_category=_get_age_category(employee),
    )

    # Incremental TDS = total liability - already deducted
    incremental_tds = max(ZERO, annual_tax - existing_ytd_tds)
    return incremental_tds.quantize(Decimal('0.01'))
```

- [x] In `_calculate_fnf_totals()`, call `_calculate_fnf_tds()` and add the result to the FnF payslip deductions:

```python
fnf_tds = _calculate_fnf_tds(
    gratuity=gratuity_amount,
    leave_encashment=leave_encashment_amount,
    other_taxable_income=notice_pay,
    employee=employee,
    last_working_day=last_working_day,
    tax_regime=get_employee_tax_regime(employee),
    existing_ytd_tds=_get_ytd_tds(employee, fiscal_year),
)
```

- [x] Add `fnf_tds` as a deduction line in the FnF payslip with label "TDS (Full & Final)".
- [x] Ensure the FnF payslip serializer exposes `fnf_tds` and the exemption breakdown.

### Tests

- [x] Add tests in `test_full_and_final.py`:
  - Employee with ₹5L gratuity → Section 10(10) fully exempt (< ₹20L ceiling) → `gratuity_taxable = 0`
  - Employee with ₹25L gratuity → `gratuity_taxable = 5,00,000` (₹25L - ₹20L)
  - Employee with ₹2L leave encashment → Section 10(10AA) fully exempt → `leave_encashment_taxable = 0`
  - Employee with ₹30L leave encashment → `leave_encashment_taxable = 5,00,000` (₹30L - ₹25L)
  - FnF with notice pay only (no gratuity/leave encashment) → notice pay is fully taxable → TDS computed normally
  - FnF TDS integrates with existing YTD TDS: employee with ₹50K YTD TDS, ₹5K more owed → `fnf_tds = ₹5K`
  - Government employee flag → both components fully exempt → `fnf_tds = 0`

## Task 3: Expose Split Fields in Frontend

- [x] Update `PayrollRunDetailPage.tsx` expandable row breakdown:
  - Under "Employer Contributions" section, show `EPF (Employer): ₹XXX` and `EPS: ₹XXX` as separate lines instead of a single "EPF Employer" total.
- [x] Update the FnF payslip template in `services.py` (WeasyPrint) to show:
  - The TDS line on the FnF payslip
  - A footnote: "Gratuity and leave encashment amounts are exempt under Section 10(10) and Section 10(10AA) of the Income Tax Act up to applicable limits."
