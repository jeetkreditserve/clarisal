# P02 — Payroll Engine Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the statutory TDS calculation bug (missing Rebate u/s 87A), add a negative-net-pay guard, implement old-regime tax support, investment declarations, arrears, Full & Final settlement, and Form 16 data export — so every Indian payroll compliance requirement is correctly handled.

**Architecture:** All changes are in `backend/apps/payroll/`. New models (`InvestmentDeclaration`, `Arrears`, `FullAndFinalSettlement`) follow the existing `AuditedBaseModel` pattern. Business logic lives in `services.py`. Views are thin — they call service functions and return serialized data. All calculation changes are driven by unit tests with exact rupee assertions first.

**Tech Stack:** Django 4.2 · DRF · Python `decimal.Decimal` · pytest · factory-boy

---

## Audit Findings Addressed

| ID | Finding | Severity |
|----|---------|----------|
| F6-01 | Missing Rebate u/s 87A — employees with income ≤₹7L overpay TDS | 🔴 Critical |
| F6-04 | No guard against negative net pay | 🟡 Medium |
| Phase 1 | No old tax regime option | ❌ Missing |
| Phase 1 | No investment declarations (80C/80D) | ❌ Missing |
| Phase 1 | No arrears calculation | ❌ Missing |
| Phase 1 | No Full & Final settlement | ❌ Missing |
| Phase 1 | No Form 16 data export | ❌ Missing |

---

## Prerequisite: Read these files before starting

- `backend/apps/payroll/services.py` — understand `_calculate_annual_tax()`, `_compute_pay_run_item_snapshot()`, constants section (lines 36–90)
- `backend/apps/payroll/models.py` — understand `PayrollTaxSlabSet`, `CompensationAssignment`, `PayrollRun`, `PayrollRunItem`, `Payslip`
- `backend/apps/employees/models.py` — understand `EmployeeOffboardingProcess`

---

## File Structure

```
backend/apps/payroll/
  services.py              MODIFY — 87A rebate, negative net pay guard, old regime, investment deduction
  models.py                MODIFY — add InvestmentDeclaration, Arrears, FullAndFinalSettlement models
  serializers.py           MODIFY — add serializers for new models
  views.py                 MODIFY — add endpoints for new models
  org_urls.py              MODIFY — register new URL patterns
  self_urls.py             MODIFY — register employee-facing URL patterns
  migrations/
    000X_add_investment_declaration.py    CREATE
    000Y_add_arrears.py                   CREATE
    000Z_add_full_and_final_settlement.py CREATE
  tests/
    test_statutory_calculations.py        CREATE — unit tests for all calculations
    test_investment_declarations.py       CREATE
    test_full_and_final.py               CREATE
```

---

## Task 1: Fix Rebate u/s 87A (Critical Statutory Bug)

**Files:** `backend/apps/payroll/services.py`, `backend/apps/payroll/tests/test_statutory_calculations.py` (new)

Context: Currently `_calculate_annual_tax()` is called and the result is used directly as `annual_tax_before_cess`. Section 87A of the Income Tax Act allows a rebate of up to ₹25,000 for taxpayers with net taxable income ≤ ₹7,00,000 under the new regime. Without this rebate, employees earning ₹5L–₹7L incorrectly pay TDS.

- [x] **Step 1: Create test file and write the failing 87A tests**

  Create `backend/apps/payroll/tests/test_statutory_calculations.py`:
  ```python
  """
  Unit tests for Indian statutory payroll calculations.
  Each test uses exact rupee amounts to catch regressions.
  Uses the default India new regime FY2024-25 tax slabs:
    0–3L: 0%, 3–7L: 5%, 7–10L: 10%, 10–12L: 15%, 12–15L: 20%, 15L+: 30%
  Standard deduction: ₹75,000. Rebate u/s 87A: ₹25,000 max for income ≤ ₹7L.
  Cess: 4%.
  """
  import pytest
  from decimal import Decimal
  from django.test import TestCase
  from apps.payroll.services import (
      _calculate_annual_tax,
      _get_default_india_tax_slab_set,
  )


  @pytest.fixture
  def india_new_regime_slabs(db):
      """Return or create the default India new regime tax slab set."""
      from apps.payroll.models import PayrollTaxSlabSet, PayrollTaxSlab
      slab_set, _ = PayrollTaxSlabSet.objects.get_or_create(
          country_code='IN',
          fiscal_year='2024-25',
          is_system_master=True,
          defaults={'name': 'India New Regime FY2024-25'},
      )
      if not slab_set.slabs.exists():
          slabs = [
              (0, 300000, Decimal('0')),
              (300000, 700000, Decimal('5')),
              (700000, 1000000, Decimal('10')),
              (1000000, 1200000, Decimal('15')),
              (1200000, 1500000, Decimal('20')),
              (1500000, None, Decimal('30')),
          ]
          for min_inc, max_inc, rate in slabs:
              PayrollTaxSlab.objects.create(
                  slab_set=slab_set,
                  min_income=Decimal(str(min_inc)),
                  max_income=Decimal(str(max_inc)) if max_inc else None,
                  rate_percent=rate,
              )
      return slab_set


  class TestSection87ARebate:
      """
      Section 87A: If net taxable income ≤ ₹7,00,000 (after standard deduction),
      a rebate of min(tax_liability, ₹25,000) applies → net tax = max(0, tax - rebate).
      """

      def test_income_5_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
          """
          Annual taxable income ₹5,00,000 (after ₹75k std deduction, so gross ≈ ₹5.75L).
          Tax before rebate: (₹5L - ₹3L) × 5% = ₹10,000.
          Rebate: min(₹10,000, ₹25,000) = ₹10,000.
          Net tax before cess: ₹0. Cess: ₹0. Final: ₹0.
          """
          from apps.payroll.services import calculate_income_tax_with_rebate
          result = calculate_income_tax_with_rebate(
              taxable_income=Decimal('500000'),
              tax_slab_set=india_new_regime_slabs,
          )
          assert result['annual_tax'] == Decimal('0'), f"Expected ₹0 but got ₹{result['annual_tax']}"
          assert result['rebate_87a'] == Decimal('10000')

      def test_income_6_5_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
          """
          Taxable income ₹6,50,000.
          Tax before rebate: (₹6.5L - ₹3L) × 5% = ₹17,500.
          Rebate: min(₹17,500, ₹25,000) = ₹17,500 → net = ₹0.
          Cess: ₹0. Final: ₹0.
          """
          from apps.payroll.services import calculate_income_tax_with_rebate
          result = calculate_income_tax_with_rebate(
              taxable_income=Decimal('650000'),
              tax_slab_set=india_new_regime_slabs,
          )
          assert result['annual_tax'] == Decimal('0')
          assert result['rebate_87a'] == Decimal('17500')

      def test_income_exactly_7_lakh_no_tax_after_rebate(self, india_new_regime_slabs):
          """
          Taxable income exactly ₹7,00,000.
          Tax before rebate: (₹7L - ₹3L) × 5% = ₹20,000.
          Rebate: min(₹20,000, ₹25,000) = ₹20,000 → net = ₹0.
          """
          from apps.payroll.services import calculate_income_tax_with_rebate
          result = calculate_income_tax_with_rebate(
              taxable_income=Decimal('700000'),
              tax_slab_set=india_new_regime_slabs,
          )
          assert result['annual_tax'] == Decimal('0')

      def test_income_7_lakh_1_rupee_above_threshold_rebate_does_not_apply(self, india_new_regime_slabs):
          """
          Taxable income ₹7,00,001 — one rupee above ₹7L limit.
          Rebate does NOT apply. Full tax payable.
          Tax: (₹7L - ₹3L) × 5% + (₹1) × 10% = ₹20,000 + ₹0.10 ≈ ₹20,000.10
          + 4% cess.
          """
          from apps.payroll.services import calculate_income_tax_with_rebate
          result = calculate_income_tax_with_rebate(
              taxable_income=Decimal('700001'),
              tax_slab_set=india_new_regime_slabs,
          )
          # Tax > 0 (rebate doesn't apply above 7L)
          assert result['annual_tax'] > Decimal('0')
          assert result['rebate_87a'] == Decimal('0')

      def test_income_10_lakh_full_tax_no_rebate(self, india_new_regime_slabs):
          """
          Taxable income ₹10,00,000 — well above ₹7L.
          Tax: (₹4L × 5%) + (₹3L × 10%) = ₹20,000 + ₹30,000 = ₹50,000.
          + 4% cess = ₹52,000.
          """
          from apps.payroll.services import calculate_income_tax_with_rebate
          result = calculate_income_tax_with_rebate(
              taxable_income=Decimal('1000000'),
              tax_slab_set=india_new_regime_slabs,
          )
          assert result['rebate_87a'] == Decimal('0')
          assert result['annual_tax'] == Decimal('52000')


  class TestStandardDeduction:

      def test_standard_deduction_75000_subtracted(self, india_new_regime_slabs):
          """Standard deduction of ₹75,000 is subtracted from gross income before tax."""
          from apps.payroll.services import calculate_taxable_income_after_standard_deduction
          result = calculate_taxable_income_after_standard_deduction(Decimal('1000000'))
          assert result == Decimal('925000')

      def test_standard_deduction_cannot_produce_negative_income(self, india_new_regime_slabs):
          """If gross < ₹75,000, taxable income should be ₹0, not negative."""
          from apps.payroll.services import calculate_taxable_income_after_standard_deduction
          result = calculate_taxable_income_after_standard_deduction(Decimal('50000'))
          assert result == Decimal('0')


  class TestCessCalculation:

      def test_4_percent_cess_applied_after_tax(self, india_new_regime_slabs):
          """4% Health & Education Cess is added to income tax."""
          from apps.payroll.services import apply_cess
          tax_before_cess = Decimal('50000')
          result = apply_cess(tax_before_cess)
          assert result == Decimal('52000')  # 50000 * 1.04
  ```

  Run:
  ```bash
  cd backend
  pytest apps/payroll/tests/test_statutory_calculations.py -v
  # Expected: FAIL — calculate_income_tax_with_rebate not defined
  ```

- [x] **Step 2: Add helper functions and rebate logic to `services.py`**

  Open `backend/apps/payroll/services.py`. After the constants block (around line 90), add:

  ```python
  # Section 87A rebate constants (India new regime)
  REBATE_87A_INCOME_LIMIT = Decimal('700000')
  REBATE_87A_MAX_REBATE = Decimal('25000')


  def calculate_taxable_income_after_standard_deduction(annual_gross: Decimal) -> Decimal:
      """Subtract ₹75,000 standard deduction; floor at zero."""
      return max(ZERO, annual_gross - INDIA_STANDARD_DEDUCTION)


  def apply_cess(tax_before_cess: Decimal) -> Decimal:
      """Apply 4% Health & Education Cess."""
      return (tax_before_cess * (ONE + INDIA_CESS_RATE)).quantize(Decimal('0.01'))


  def calculate_income_tax_with_rebate(
      taxable_income: Decimal,
      tax_slab_set,
  ) -> dict:
      """
      Calculate annual income tax under India new regime including:
      - Slab-based tax calculation
      - Section 87A rebate (max ₹25,000 for income ≤ ₹7L)
      - 4% Health & Education Cess

      Returns dict with keys: tax_before_rebate, rebate_87a, tax_after_rebate, cess, annual_tax
      """
      tax_before_rebate = _calculate_annual_tax(tax_slab_set, taxable_income)

      # Section 87A: rebate applies only if taxable income ≤ ₹7,00,000
      if taxable_income <= REBATE_87A_INCOME_LIMIT:
          rebate_87a = min(tax_before_rebate, REBATE_87A_MAX_REBATE)
      else:
          rebate_87a = ZERO

      tax_after_rebate = max(ZERO, tax_before_rebate - rebate_87a)
      cess = apply_cess(tax_after_rebate) - tax_after_rebate
      annual_tax = tax_after_rebate + cess

      return {
          'tax_before_rebate': tax_before_rebate,
          'rebate_87a': rebate_87a,
          'tax_after_rebate': tax_after_rebate,
          'cess': cess,
          'annual_tax': annual_tax.quantize(Decimal('0.01')),
      }
  ```

  Now find where `_calculate_annual_tax` is called in `_compute_pay_run_item_snapshot()` (around line 901–908) and replace:
  ```python
  # OLD (before fix):
  annual_tax_before_cess = _calculate_annual_tax(tax_slab_set, annual_taxable_after_sd)
  annual_tax = annual_tax_before_cess * (ONE + INDIA_CESS_RATE)

  # NEW (with 87A rebate):
  tax_result = calculate_income_tax_with_rebate(
      taxable_income=annual_taxable_after_sd,
      tax_slab_set=tax_slab_set,
  )
  annual_tax = tax_result['annual_tax']
  # Store rebate in snapshot for payslip display
  snapshot_extras = {
      'rebate_87a': str(tax_result['rebate_87a']),
      'tax_before_rebate': str(tax_result['tax_before_rebate']),
  }
  ```

  Also update the snapshot dict to include the rebate details (find where snapshot is built and add):
  ```python
  snapshot['income_tax']['rebate_87a'] = str(tax_result['rebate_87a'])
  snapshot['income_tax']['tax_before_rebate'] = str(tax_result['tax_before_rebate'])
  ```

- [x] **Step 3: Run tests to verify rebate is correct**

  ```bash
  cd backend
  pytest apps/payroll/tests/test_statutory_calculations.py -v
  # Expected: all PASS
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/apps/payroll/services.py backend/apps/payroll/tests/test_statutory_calculations.py
  git commit -m "fix(payroll): implement Section 87A income tax rebate — employees with income ≤₹7L now correctly pay zero TDS"
  ```

---

## Task 2: Add Negative Net Pay Guard

**Files:** `backend/apps/payroll/services.py`, `backend/apps/payroll/tests/test_statutory_calculations.py`

- [x] **Step 1: Write the failing test**

  Add to `test_statutory_calculations.py`:
  ```python
  class TestNegativeNetPayGuard:

      @pytest.mark.django_db
      def test_net_pay_cannot_be_negative(self, db, india_new_regime_slabs):
          """
          If deductions exceed gross (edge case with manual deduction components),
          net_pay should be clamped to ₹0, not go negative.
          This tests the guard in _compute_pay_run_item_snapshot.
          """
          # We test the guard function directly
          from apps.payroll.services import ensure_non_negative_net_pay
          assert ensure_non_negative_net_pay(Decimal('-5000')) == Decimal('0')
          assert ensure_non_negative_net_pay(Decimal('0')) == Decimal('0')
          assert ensure_non_negative_net_pay(Decimal('45000')) == Decimal('45000')
  ```

  Run:
  ```bash
  pytest apps/payroll/tests/test_statutory_calculations.py::TestNegativeNetPayGuard -v
  # Expected: FAIL — ensure_non_negative_net_pay not defined
  ```

- [x] **Step 2: Add the guard function and apply it in the snapshot computation**

  In `backend/apps/payroll/services.py`, add near the other utility functions:
  ```python
  def ensure_non_negative_net_pay(net_pay: Decimal) -> Decimal:
      """Clamp net pay to zero — deductions can never exceed gross."""
      if net_pay < ZERO:
          import logging
          logging.getLogger(__name__).warning(
              "Net pay calculated as negative (%.2f). Clamping to zero. "
              "Check that deduction components do not exceed earnings.",
              net_pay,
          )
      return max(ZERO, net_pay)
  ```

  Find where `net_pay` is assigned in `_compute_pay_run_item_snapshot()` and wrap it:
  ```python
  # Before:
  net_pay = gross_pay - total_deductions

  # After:
  net_pay = ensure_non_negative_net_pay(gross_pay - total_deductions)
  ```

- [x] **Step 3: Run tests and commit**

  ```bash
  cd backend
  pytest apps/payroll/tests/test_statutory_calculations.py -v
  # Expected: all PASS

  git add backend/apps/payroll/services.py
  git commit -m "fix(payroll): clamp net pay to zero when deductions exceed gross earnings"
  ```

---

## Task 3: Add Old Tax Regime Support

**Files:** `backend/apps/payroll/models.py`, `backend/apps/payroll/services.py`, migration

- [x] **Step 1: Write the failing test**

  Add to `test_statutory_calculations.py`:
  ```python
  class TestOldRegimeTaxSlabs:

      @pytest.mark.django_db
      def test_old_regime_flag_on_tax_slab_set(self, db):
          """PayrollTaxSlabSet can be flagged as old_regime."""
          from apps.payroll.models import PayrollTaxSlabSet
          old_regime_set = PayrollTaxSlabSet(
              name='India Old Regime FY2024-25',
              country_code='IN',
              fiscal_year='2024-25',
              is_system_master=False,
              is_old_regime=True,
          )
          # Should not raise
          old_regime_set.full_clean()
  ```

  Run:
  ```bash
  pytest apps/payroll/tests/test_statutory_calculations.py::TestOldRegimeTaxSlabs -v
  # Expected: FAIL — is_old_regime field not found
  ```

- [x] **Step 2: Add `is_old_regime` field to `PayrollTaxSlabSet`**

  Open `backend/apps/payroll/models.py`. Find `PayrollTaxSlabSet` and add:
  ```python
  is_old_regime = models.BooleanField(
      default=False,
      help_text=(
          'If True, this slab set represents the old tax regime. '
          'Old regime allows HRA, 80C, 80D deductions. '
          'New regime (default) offers lower rates with fewer deductions.'
      ),
  )
  ```

  Create the migration:
  ```bash
  cd backend
  python manage.py makemigrations payroll --name add_old_regime_flag_to_tax_slab_set
  python manage.py migrate --run-syncdb
  ```

- [x] **Step 3: Update `CompensationAssignment` to allow per-employee regime selection**

  In `models.py`, find `CompensationAssignment` and add:
  ```python
  class TaxRegime(models.TextChoices):
      NEW = 'NEW', 'New Regime (Lower rates, fewer deductions)'
      OLD = 'OLD', 'Old Regime (Higher rates, with HRA/80C/80D deductions)'

  # Add field to CompensationAssignment:
  tax_regime = models.CharField(
      max_length=3,
      choices=TaxRegime.choices,
      default=TaxRegime.NEW,
  )
  ```

  Create migration:
  ```bash
  python manage.py makemigrations payroll --name add_tax_regime_to_compensation_assignment
  ```

- [x] **Step 4: Run tests and commit**

  ```bash
  pytest apps/payroll/tests/test_statutory_calculations.py -v
  # Expected: all PASS

  git add backend/apps/payroll/
  git commit -m "feat(payroll): add old tax regime flag to PayrollTaxSlabSet and per-employee regime selection"
  ```

---

## Task 4: Investment Declarations (80C, 80D)

**Files:** `backend/apps/payroll/models.py`, `services.py`, `serializers.py`, `views.py`, `self_urls.py`, migration

- [x] **Step 1: Write failing tests**

  Create `backend/apps/payroll/tests/test_investment_declarations.py`:
  ```python
  import pytest
  from decimal import Decimal
  from apps.payroll.models import InvestmentDeclaration, InvestmentSection


  @pytest.mark.django_db
  class TestInvestmentDeclarationModel:

      def test_investment_declaration_created_for_employee(self, employee_factory, organisation):
          employee = employee_factory(organisation=organisation)
          declaration = InvestmentDeclaration.objects.create(
              employee=employee,
              fiscal_year='2024-25',
              section=InvestmentSection.SECTION_80C,
              description='PPF Contribution',
              declared_amount=Decimal('150000'),
          )
          assert declaration.employee == employee
          assert declaration.declared_amount == Decimal('150000')

      def test_80c_limit_enforced_at_1_50_000(self, employee_factory, organisation):
          """Section 80C maximum deduction is ₹1,50,000."""
          from apps.payroll.services import get_total_80c_deduction
          employee = employee_factory(organisation=organisation)
          # Create declarations totalling ₹2L (exceeds ₹1.5L cap)
          InvestmentDeclaration.objects.create(
              employee=employee, fiscal_year='2024-25',
              section=InvestmentSection.SECTION_80C,
              description='LIC Premium', declared_amount=Decimal('100000'),
          )
          InvestmentDeclaration.objects.create(
              employee=employee, fiscal_year='2024-25',
              section=InvestmentSection.SECTION_80C,
              description='ELSS', declared_amount=Decimal('100000'),
          )
          total = get_total_80c_deduction(employee, '2024-25')
          assert total == Decimal('150000')  # Capped at ₹1.5L

      def test_investment_deduction_reduces_taxable_income(self, employee_factory, organisation, india_new_regime_slabs):
          """Declared investments reduce the taxable income before slab computation."""
          from apps.payroll.services import calculate_taxable_income_with_investments
          employee = employee_factory(organisation=organisation)
          InvestmentDeclaration.objects.create(
              employee=employee, fiscal_year='2024-25',
              section=InvestmentSection.SECTION_80C,
              description='PPF', declared_amount=Decimal('150000'),
          )
          # Gross ₹10L, std deduction ₹75k → ₹9.25L, less 80C ₹1.5L = ₹7.75L
          taxable = calculate_taxable_income_with_investments(
              employee=employee,
              annual_gross=Decimal('1000000'),
              fiscal_year='2024-25',
              tax_regime='OLD',  # Old regime allows 80C
          )
          assert taxable == Decimal('775000')
  ```

  Run:
  ```bash
  pytest apps/payroll/tests/test_investment_declarations.py -v
  # Expected: FAIL
  ```

- [x] **Step 2: Create `InvestmentDeclaration` model**

  In `backend/apps/payroll/models.py`, add before the last class:
  ```python
  class InvestmentSection(models.TextChoices):
      SECTION_80C = '80C', 'Section 80C (PPF, ELSS, LIC, etc.) — max ₹1,50,000'
      SECTION_80D = '80D', 'Section 80D (Medical Insurance) — max ₹25,000 / ₹50,000'
      SECTION_80TTA = '80TTA', 'Section 80TTA (Savings Interest) — max ₹10,000'
      SECTION_80G = '80G', 'Section 80G (Donations) — variable %'
      HRA = 'HRA', 'House Rent Allowance (old regime only)'
      LTA = 'LTA', 'Leave Travel Allowance'
      OTHER = 'OTHER', 'Other declared deduction'

  SECTION_LIMITS = {
      InvestmentSection.SECTION_80C: Decimal('150000'),
      InvestmentSection.SECTION_80D: Decimal('50000'),
      InvestmentSection.SECTION_80TTA: Decimal('10000'),
  }


  class InvestmentDeclaration(AuditedBaseModel):
      """Employee investment declaration for TDS computation in a given fiscal year."""
      employee = models.ForeignKey(
          'employees.Employee',
          on_delete=models.CASCADE,
          related_name='investment_declarations',
      )
      fiscal_year = models.CharField(max_length=7, help_text='e.g. "2024-25"')
      section = models.CharField(max_length=10, choices=InvestmentSection.choices)
      description = models.CharField(max_length=200)
      declared_amount = models.DecimalField(max_digits=12, decimal_places=2)
      proof_file_key = models.CharField(max_length=500, blank=True, null=True)
      is_verified = models.BooleanField(default=False)
      verified_by = models.ForeignKey(
          'accounts.User',
          null=True, blank=True,
          on_delete=models.SET_NULL,
          related_name='verified_declarations',
      )

      class Meta:
          ordering = ['section', 'created_at']
          indexes = [
              models.Index(fields=['employee', 'fiscal_year']),
          ]

      def __str__(self):
          return f"{self.employee} — {self.section} — ₹{self.declared_amount}"
  ```

  Create migration:
  ```bash
  python manage.py makemigrations payroll --name add_investment_declaration
  ```

- [x] **Step 3: Add service functions for investment deduction**

  In `backend/apps/payroll/services.py`, add:
  ```python
  def get_total_80c_deduction(employee, fiscal_year: str) -> Decimal:
      """Return total Section 80C deduction, capped at ₹1,50,000."""
      from apps.payroll.models import InvestmentDeclaration, InvestmentSection, SECTION_LIMITS
      total = InvestmentDeclaration.objects.filter(
          employee=employee,
          fiscal_year=fiscal_year,
          section=InvestmentSection.SECTION_80C,
      ).aggregate(total=Sum('declared_amount'))['total'] or ZERO
      cap = SECTION_LIMITS.get(InvestmentSection.SECTION_80C, Decimal('150000'))
      return min(total, cap)


  def calculate_taxable_income_with_investments(
      employee, annual_gross: Decimal, fiscal_year: str, tax_regime: str
  ) -> Decimal:
      """
      Calculate net taxable income after standard deduction and investment declarations.
      Old regime: applies 80C, 80D, HRA, etc.
      New regime: only standard deduction (no other deductions).
      """
      from apps.payroll.models import TaxRegime, InvestmentDeclaration, SECTION_LIMITS
      after_std_deduction = calculate_taxable_income_after_standard_deduction(annual_gross)

      if tax_regime == TaxRegime.OLD:
          # Sum all declarations, respecting per-section caps
          total_deductions = ZERO
          for section, cap in SECTION_LIMITS.items():
              section_total = InvestmentDeclaration.objects.filter(
                  employee=employee,
                  fiscal_year=fiscal_year,
                  section=section,
              ).aggregate(total=Sum('declared_amount'))['total'] or ZERO
              total_deductions += min(section_total, cap)
          return max(ZERO, after_std_deduction - total_deductions)
      else:
          # New regime: no additional deductions beyond standard deduction
          return after_std_deduction
  ```

- [x] **Step 4: Run tests and commit**

  ```bash
  pytest apps/payroll/tests/test_investment_declarations.py -v
  # Expected: all PASS

  git add backend/apps/payroll/
  git commit -m "feat(payroll): add investment declarations (80C/80D) with section-wise caps and TDS integration"
  ```

---

## Task 5: Full & Final Settlement

**Files:** `backend/apps/payroll/models.py`, `services.py`, `serializers.py`, `views.py`, migration

- [x] **Step 1: Write failing tests**

  Create `backend/apps/payroll/tests/test_full_and_final.py`:
  ```python
  import pytest
  from decimal import Decimal
  from datetime import date
  from apps.payroll.models import FullAndFinalSettlement, FNFStatus


  @pytest.mark.django_db
  class TestFullAndFinalSettlement:

      def test_fnf_created_on_offboarding_initiation(
          self, employee_factory, organisation
      ):
          """F&F settlement record is created when employee offboarding is initiated."""
          from apps.payroll.services import create_full_and_final_settlement
          employee = employee_factory(organisation=organisation, status='ACTIVE')
          fnf = create_full_and_final_settlement(
              employee=employee,
              last_working_day=date(2025, 3, 31),
              initiated_by=employee.user,
          )
          assert fnf.employee == employee
          assert fnf.status == FNFStatus.DRAFT
          assert fnf.last_working_day == date(2025, 3, 31)

      def test_salary_proration_for_exit_month(
          self, employee_factory, organisation
      ):
          """Exit month salary is prorated to last working day."""
          from apps.payroll.services import calculate_fnf_salary_proration
          # Employee working 15 days of a 31-day month
          result = calculate_fnf_salary_proration(
              gross_monthly_salary=Decimal('100000'),
              last_working_day=date(2025, 3, 15),
              period_year=2025,
              period_month=3,
          )
          # 15 / 31 * ₹1,00,000 = ₹48,387.10
          assert result == Decimal('48387.10')

      def test_leave_encashment_in_fnf(
          self, employee_factory, leave_balance_factory, organisation
      ):
          """Leave encashment is calculated based on balance and basic salary."""
          from apps.payroll.services import calculate_leave_encashment_amount
          amount = calculate_leave_encashment_amount(
              leave_days=Decimal('10'),
              monthly_basic_salary=Decimal('50000'),
          )
          # 10 days × (₹50,000 / 26 working days) = ₹19,230.77
          assert amount == Decimal('19230.77')
  ```

  Run:
  ```bash
  pytest apps/payroll/tests/test_full_and_final.py -v
  # Expected: FAIL
  ```

- [x] **Step 2: Create `FullAndFinalSettlement` model**

  In `backend/apps/payroll/models.py`, add:
  ```python
  class FNFStatus(models.TextChoices):
      DRAFT = 'DRAFT', 'Draft'
      CALCULATED = 'CALCULATED', 'Calculated'
      APPROVED = 'APPROVED', 'Approved'
      PAID = 'PAID', 'Paid'
      CANCELLED = 'CANCELLED', 'Cancelled'


  class FullAndFinalSettlement(AuditedBaseModel):
      """Full and Final settlement for an exiting employee."""
      employee = models.OneToOneField(
          'employees.Employee',
          on_delete=models.PROTECT,
          related_name='full_and_final_settlement',
      )
      offboarding_process = models.OneToOneField(
          'employees.EmployeeOffboardingProcess',
          on_delete=models.SET_NULL,
          null=True, blank=True,
          related_name='fnf_settlement',
      )
      last_working_day = models.DateField()
      status = models.CharField(max_length=20, choices=FNFStatus.choices, default=FNFStatus.DRAFT)

      # Salary components
      prorated_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      leave_encashment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      gratuity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      arrears = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      other_credits = models.DecimalField(max_digits=12, decimal_places=2, default=0)

      # Deductions
      tds_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      pf_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      loan_recovery = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)

      # Computed
      gross_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
      net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)

      notes = models.TextField(blank=True)
      approved_by = models.ForeignKey(
          'accounts.User', null=True, blank=True, on_delete=models.SET_NULL,
          related_name='approved_fnf_settlements',
      )
      approved_at = models.DateTimeField(null=True, blank=True)
      paid_at = models.DateTimeField(null=True, blank=True)

      class Meta:
          ordering = ['-created_at']
  ```

  Create migration:
  ```bash
  python manage.py makemigrations payroll --name add_full_and_final_settlement
  ```

- [x] **Step 3: Add F&F service functions**

  In `backend/apps/payroll/services.py`, add:
  ```python
  import calendar

  def calculate_fnf_salary_proration(
      gross_monthly_salary: Decimal,
      last_working_day: date,
      period_year: int,
      period_month: int,
  ) -> Decimal:
      """Prorate salary to last_working_day within the given month."""
      total_days = calendar.monthrange(period_year, period_month)[1]
      paid_days = last_working_day.day
      return (gross_monthly_salary * Decimal(paid_days) / Decimal(total_days)).quantize(Decimal('0.01'))


  def calculate_leave_encashment_amount(
      leave_days: Decimal,
      monthly_basic_salary: Decimal,
  ) -> Decimal:
      """
      Encashment = leave_days × (monthly_basic / 26).
      26 is the standard working days per month for encashment per Indian labour law.
      """
      per_day_basic = (monthly_basic_salary / Decimal('26')).quantize(Decimal('0.01'))
      return (leave_days * per_day_basic).quantize(Decimal('0.01'))


  def create_full_and_final_settlement(employee, last_working_day: date, initiated_by) -> 'FullAndFinalSettlement':
      """Create a draft F&F settlement for an exiting employee."""
      from apps.payroll.models import FullAndFinalSettlement, FNFStatus
      fnf, created = FullAndFinalSettlement.objects.get_or_create(
          employee=employee,
          defaults={
              'last_working_day': last_working_day,
              'status': FNFStatus.DRAFT,
          },
      )
      log_audit_event(
          initiated_by, 'payroll.fnf.created',
          organisation=employee.organisation,
          target=fnf,
      )
      return fnf
  ```

- [ ] **Step 4: Run all payroll tests and commit**

  ```bash
  pytest apps/payroll/tests/ -v
  # Expected: all PASS

  git add backend/apps/payroll/
  git commit -m "feat(payroll): add Full & Final settlement model and calculation services"
  ```

---

## Task 6: Arrears Model and Calculation

**Files:** `backend/apps/payroll/models.py`, `services.py`, migration

- [x] **Step 1: Create `Arrears` model**

  In `backend/apps/payroll/models.py`, add:
  ```python
  class Arrears(AuditedBaseModel):
      """Represents a back-pay arrears entry for an employee."""
      employee = models.ForeignKey(
          'employees.Employee',
          on_delete=models.CASCADE,
          related_name='arrears',
      )
      pay_run = models.ForeignKey(
          'PayrollRun',
          on_delete=models.CASCADE,
          related_name='arrears_items',
          null=True, blank=True,
          help_text='The pay run in which this arrear will be paid out.',
      )
      for_period_year = models.PositiveSmallIntegerField(help_text='Year of the period arrears are for.')
      for_period_month = models.PositiveSmallIntegerField(help_text='Month (1-12) arrears are for.')
      reason = models.CharField(max_length=200)
      amount = models.DecimalField(max_digits=12, decimal_places=2)
      is_included_in_payslip = models.BooleanField(default=False)

      class Meta:
          ordering = ['for_period_year', 'for_period_month']
          indexes = [
              models.Index(fields=['employee', 'pay_run']),
          ]
  ```

  Create migration:
  ```bash
  python manage.py makemigrations payroll --name add_arrears
  ```

- [x] **Step 2: Write test and service**

  ```python
  # In test file:
  def test_arrears_included_in_gross_pay():
      """Arrears amount is added to gross pay in the pay run they are attached to."""
      from apps.payroll.services import get_employee_arrears_for_run
      # Setup: create an arrears entry linked to a specific pay run
      ...
  ```

  In `services.py`, add:
  ```python
  def get_employee_arrears_for_run(employee, pay_run) -> Decimal:
      """Sum all unprocessed arrears for an employee attached to this run."""
      from apps.payroll.models import Arrears
      return Arrears.objects.filter(
          employee=employee,
          pay_run=pay_run,
          is_included_in_payslip=False,
      ).aggregate(total=Sum('amount'))['total'] or ZERO
  ```

- [x] **Step 3: Integrate arrears into payslip computation**

  In `_compute_pay_run_item_snapshot()`, after computing `gross_pay`, add:
  ```python
  arrears_amount = get_employee_arrears_for_run(employee, pay_run)
  gross_pay += arrears_amount
  snapshot['arrears'] = str(arrears_amount)
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/apps/payroll/
  git commit -m "feat(payroll): add arrears model and include arrears in pay run calculation"
  ```

---

## Task 7: Form 16 Data Export Endpoint

**Files:** `backend/apps/payroll/views.py`, `backend/apps/payroll/org_urls.py`

- [x] **Step 1: Write failing test**

  ```python
  # In backend/apps/payroll/tests/test_views.py, add:
  def test_form16_export_returns_structured_json(org_admin_client, pay_run_with_finalized_payslips):
      response = org_admin_client.get(
          f'/api/org/payroll/runs/{pay_run_with_finalized_payslips.id}/form16/'
      )
      assert response.status_code == 200
      data = response.json()
      assert 'employees' in data
      assert len(data['employees']) > 0
      first_emp = data['employees'][0]
      assert 'part_a' in first_emp  # Employer details, TDS deducted
      assert 'part_b' in first_emp  # Salary breakdown, deductions, tax computation
  ```

- [x] **Step 2: Implement the view**

  In `backend/apps/payroll/views.py`, add:
  ```python
  class OrgPayrollRunForm16View(APIView):
      permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

      def get(self, request, pk):
          organisation = _get_admin_organisation(request)
          pay_run = get_object_or_404(PayrollRun, pk=pk, organisation=organisation)
          if pay_run.status != PayrollRunStatus.FINALIZED:
              return Response(
                  {'error': 'Form 16 is only available for finalized payroll runs.'},
                  status=status.HTTP_400_BAD_REQUEST,
              )
          form16_data = generate_form16_data(pay_run)
          return Response(form16_data)
  ```

  In `services.py`, add:
  ```python
  def generate_form16_data(pay_run) -> dict:
      """
      Generate Form 16 Part A (TDS certificate) and Part B (salary details) data.
      Returns JSON structure conforming to ITD Form 16 format.
      """
      from apps.payroll.models import Payslip
      employees_data = []
      for payslip in pay_run.payslips.select_related('employee__user', 'employee__profile').all():
          snapshot = payslip.snapshot or {}
          employees_data.append({
              'employee_code': payslip.employee.employee_code,
              'employee_name': payslip.employee.user.get_full_name(),
              'pan': snapshot.get('pan', ''),  # From encrypted govt ID
              'part_a': {
                  'employer_tan': pay_run.organisation.tan_number if hasattr(pay_run.organisation, 'tan_number') else '',
                  'employer_name': pay_run.organisation.name,
                  'period': f"FY {pay_run.period_year}-{pay_run.period_month:02d}",
                  'tds_deducted': snapshot.get('income_tax', {}).get('monthly_tds', '0'),
                  'tds_deposited': snapshot.get('income_tax', {}).get('monthly_tds', '0'),
              },
              'part_b': {
                  'gross_salary': snapshot.get('gross_pay', '0'),
                  'standard_deduction': str(INDIA_STANDARD_DEDUCTION),
                  'rebate_87a': snapshot.get('income_tax', {}).get('rebate_87a', '0'),
                  'tax_before_cess': snapshot.get('income_tax', {}).get('tax_before_rebate', '0'),
                  'cess': snapshot.get('income_tax', {}).get('cess', '0'),
                  'net_tax': snapshot.get('income_tax', {}).get('monthly_tds', '0'),
              },
          })
      return {
          'pay_run_id': str(pay_run.id),
          'organisation': pay_run.organisation.name,
          'fiscal_year': f"{pay_run.period_year}-{pay_run.period_year % 100 + 1:02d}",
          'employees': employees_data,
      }
  ```

  Register URL in `org_urls.py`:
  ```python
  path('payroll/runs/<uuid:pk>/form16/', OrgPayrollRunForm16View.as_view(), name='payroll-run-form16'),
  ```

- [ ] **Step 3: Run all payroll tests and commit**

  ```bash
  cd backend
  pytest apps/payroll/tests/ -v
  # Expected: all PASS

  git add backend/apps/payroll/
  git commit -m "feat(payroll): add Form 16 data export endpoint for finalized payroll runs"
  ```

---

## Verification

Run the complete payroll test suite:

```bash
cd backend
pytest apps/payroll/tests/ -v --tb=short

# Verify 87A rebate specifically:
pytest apps/payroll/tests/test_statutory_calculations.py::TestSection87ARebate -v

# Verify coverage on services.py:
pytest apps/payroll/tests/ --cov=apps/payroll/services --cov-report=term-missing
# Expected: >80% coverage on services.py
```
