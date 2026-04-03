# P05 — Test Coverage: 100% Business Logic

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Achieve 100% test coverage on all business logic functions in payroll, timeoff, and attendance services, plus comprehensive E2E coverage of key user flows.

**Architecture:** TDD approach — every test file is written first. Backend tests use pytest + factory-boy. Frontend unit tests use Vitest + React Testing Library. E2E tests use Playwright.

**Tech Stack:** Django 4.2 · pytest · factory-boy · Vitest · React Testing Library · Playwright

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/payroll/tests/test_statutory_calculations.py` | Create | 18 unit tests for India statutory payroll math |
| `backend/apps/timeoff/tests/__init__.py` | Create | Make tests a package |
| `backend/apps/timeoff/tests/test_services.py` | Create | 9 unit tests for leave balance, carry-forward, max balance |
| `backend/apps/attendance/tests/test_daily_calculation.py` | Create | 9 unit tests for daily attendance status logic |
| `frontend/e2e/org/payroll.spec.ts` | Create | E2E: full payroll run lifecycle |
| `frontend/e2e/org/attendance-regularization.spec.ts` | Create | E2E: attendance regularization approval flow |
| `frontend/e2e/employee/leave-approval.spec.ts` | Create | E2E: employee submits leave, manager approves, balance updates |
| `frontend/e2e/employee/payslips.spec.ts` | Create | E2E: employee views and downloads payslip |
| `frontend/src/pages/org/PayrollPage.test.tsx` | Create | Vitest: payroll page renders and interaction |
| `frontend/src/pages/employee/LeavePage.test.tsx` | Create | Vitest: leave request form validation |
| `frontend/src/pages/employee/AttendancePage.test.tsx` | Create | Vitest: attendance page renders |

---

## Task 1 — India Statutory Payroll Unit Tests

**Files:**
- Create: `backend/apps/payroll/tests/test_statutory_calculations.py`

### Background

`backend/apps/payroll/services.py` contains `_calculate_pf()`, `_calculate_esi()`, `_calculate_professional_tax()`, `_calculate_annual_tax()`, and proration helpers. These need direct unit tests with exact rupee values.

These tests call service-layer helpers directly — they do not go through views, so no HTTP client or auth setup needed.

- [ ] **Step 1: Create test factory if not exists**

Check `backend/apps/payroll/tests/factories.py`. If it does not exist, create it:

```python
import factory
from decimal import Decimal
from apps.payroll.models import (
    PayrollRun, PayrollRunStatus, PayrollTaxSlabSet, PayrollTaxSlab,
    CompensationTemplate, CompensationTemplateLine, CompensationAssignment,
    PayrollComponent, PayrollComponentType,
)
from apps.employees.tests.factories import EmployeeFactory
from apps.accounts.tests.factories import OrganisationFactory


class PayrollComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PayrollComponent
    name = factory.Sequence(lambda n: f'Component {n}')
    code = factory.Sequence(lambda n: f'COMP{n}')
    component_type = PayrollComponentType.EARNING


class PayrollTaxSlabSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PayrollTaxSlabSet
    name = 'Test New Regime FY2024-25'
    fiscal_year = '2024-25'
    organisation = None  # global slab set


class PayrollTaxSlabFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PayrollTaxSlab
    slab_set = factory.SubFactory(PayrollTaxSlabSetFactory)
    min_income = Decimal('0.00')
    max_income = None
    rate = Decimal('0.00')


class PayrollRunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PayrollRun
    organisation = factory.SubFactory(OrganisationFactory)
    status = PayrollRunStatus.DRAFT
    month = 4
    year = 2024
```

- [ ] **Step 2: Write `test_statutory_calculations.py`**

```python
"""
Unit tests for India statutory payroll calculations.
All tests call service helpers directly (no HTTP, no auth).
Expected values are computed from official India statutory rules FY2024-25.
"""
from decimal import Decimal
import pytest
from apps.payroll.services import (
    _calculate_pf,
    _calculate_esi,
    _calculate_professional_tax,
    _calculate_annual_tax,
    calculate_income_tax_with_rebate,  # added in P02
    _prorate_amount,
    ZERO,
    PF_RATE,
    ESI_WAGE_CEILING,
)
from apps.payroll.tests.factories import PayrollTaxSlabSetFactory, PayrollTaxSlabFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_new_regime_slab_set():
    """
    New regime slabs FY2024-25:
    0 – 3,00,000      → 0%
    3,00,001 – 7,00,000  → 5%
    7,00,001 – 10,00,000 → 10%
    10,00,001 – 12,00,000 → 15%
    12,00,001 – 15,00,000 → 20%
    15,00,001+           → 30%
    """
    slab_set = PayrollTaxSlabSetFactory()
    PayrollTaxSlabFactory(slab_set=slab_set, min_income=Decimal('0'), max_income=Decimal('300000'), rate=Decimal('0.00'))
    PayrollTaxSlabFactory(slab_set=slab_set, min_income=Decimal('300001'), max_income=Decimal('700000'), rate=Decimal('0.05'))
    PayrollTaxSlabFactory(slab_set=slab_set, min_income=Decimal('700001'), max_income=Decimal('1000000'), rate=Decimal('0.10'))
    PayrollTaxSlabFactory(slab_set=slab_set, min_income=Decimal('1000001'), max_income=Decimal('1200000'), rate=Decimal('0.15'))
    PayrollTaxSlabFactory(slab_set=slab_set, min_income=Decimal('1200001'), max_income=Decimal('1500000'), rate=Decimal('0.20'))
    PayrollTaxSlabFactory(slab_set=slab_set, min_income=Decimal('1500001'), max_income=None, rate=Decimal('0.30'))
    return slab_set


# ---------------------------------------------------------------------------
# PF Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pf_12_percent_of_basic_salary():
    # PF = 12% of basic. Basic = ₹20,000 → PF = ₹2,400
    pf = _calculate_pf(basic_salary=Decimal('20000'))
    assert pf == Decimal('2400.00')


@pytest.mark.django_db
def test_pf_not_applied_when_basic_zero():
    pf = _calculate_pf(basic_salary=ZERO)
    assert pf == ZERO


# ---------------------------------------------------------------------------
# ESI Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_esi_employee_0_75_percent_of_gross():
    # Gross = ₹15,000, ESI employee = 0.75% = ₹112.50
    esi_emp = _calculate_esi(gross_salary=Decimal('15000'), party='employee')
    assert esi_emp == Decimal('112.50')


@pytest.mark.django_db
def test_esi_employer_3_25_percent_of_gross():
    # Gross = ₹15,000, ESI employer = 3.25% = ₹487.50
    esi_emp = _calculate_esi(gross_salary=Decimal('15000'), party='employer')
    assert esi_emp == Decimal('487.50')


@pytest.mark.django_db
def test_esi_skipped_when_gross_above_21000():
    # Gross = ₹25,000 → above ceiling → ESI = 0
    esi_emp = _calculate_esi(gross_salary=Decimal('25000'), party='employee')
    assert esi_emp == ZERO


@pytest.mark.django_db
def test_esi_applied_when_gross_exactly_21000():
    # Gross = ₹21,000 → at ceiling → ESI applies
    esi_emp = _calculate_esi(gross_salary=Decimal('21000'), party='employee')
    assert esi_emp == Decimal('157.50')  # 21000 * 0.0075


# ---------------------------------------------------------------------------
# Professional Tax — Maharashtra
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pt_maharashtra_below_10000_zero():
    pt = _calculate_professional_tax(monthly_gross=Decimal('9999'), state='MH')
    assert pt == ZERO


@pytest.mark.django_db
def test_pt_maharashtra_10000_to_14999_is_150():
    pt = _calculate_professional_tax(monthly_gross=Decimal('12000'), state='MH')
    assert pt == Decimal('150.00')


@pytest.mark.django_db
def test_pt_maharashtra_above_15000_is_200():
    pt = _calculate_professional_tax(monthly_gross=Decimal('20000'), state='MH')
    assert pt == Decimal('200.00')


# ---------------------------------------------------------------------------
# Income Tax / TDS Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_income_tax_standard_deduction_applied():
    # Annual CTC ₹8,00,000. After ₹75,000 standard deduction → taxable ₹7,25,000
    # Tax on ₹7,25,000 (new regime):
    #   0–3L = 0, 3L–7L = 4L×5% = ₹20,000, 7L–7.25L = 25,000×10% = ₹2,500 → total ₹22,500
    # Plus cess 4% = ₹900 → total ₹23,400
    slab_set = make_new_regime_slab_set()
    result = calculate_income_tax_with_rebate(
        taxable_income=Decimal('725000'),
        tax_slab_set=slab_set,
    )
    assert result['tax_after_rebate'] == Decimal('22500.00')  # rebate does not apply (>7L)
    assert result['cess'] == Decimal('900.00')


@pytest.mark.django_db
def test_income_tax_rebate_87a_income_5_lakh_zero_tax():
    # Taxable ₹5,00,000 → tax = ₹10,000 → rebate 87A = ₹10,000 → net TDS = ₹0
    slab_set = make_new_regime_slab_set()
    result = calculate_income_tax_with_rebate(
        taxable_income=Decimal('500000'),
        tax_slab_set=slab_set,
    )
    assert result['rebate_87a'] == Decimal('10000.00')
    assert result['tax_after_rebate'] == ZERO
    assert result['cess'] == ZERO


@pytest.mark.django_db
def test_income_tax_rebate_87a_income_exactly_7_lakh_zero_tax():
    # Taxable ₹7,00,000 → tax = ₹20,000 → rebate 87A = min(20000, 25000) = ₹20,000 → net = ₹0
    slab_set = make_new_regime_slab_set()
    result = calculate_income_tax_with_rebate(
        taxable_income=Decimal('700000'),
        tax_slab_set=slab_set,
    )
    assert result['rebate_87a'] == Decimal('20000.00')
    assert result['tax_after_rebate'] == ZERO


@pytest.mark.django_db
def test_income_tax_rebate_87a_income_7_lakh_1_rupee_tax_applies():
    # Taxable ₹7,00,001 → above 87A limit → rebate = 0 → tax > 0
    slab_set = make_new_regime_slab_set()
    result = calculate_income_tax_with_rebate(
        taxable_income=Decimal('700001'),
        tax_slab_set=slab_set,
    )
    assert result['rebate_87a'] == ZERO
    assert result['tax_after_rebate'] > ZERO


@pytest.mark.django_db
def test_income_tax_cess_4_percent():
    # ₹10,00,000 taxable → tax = 0+20000+30000 = ₹50,000 → cess 4% = ₹2,000
    slab_set = make_new_regime_slab_set()
    result = calculate_income_tax_with_rebate(
        taxable_income=Decimal('1000000'),
        tax_slab_set=slab_set,
    )
    assert result['tax_after_rebate'] == Decimal('50000.00')
    assert result['cess'] == Decimal('2000.00')
    assert result['total_tax'] == Decimal('52000.00')


# ---------------------------------------------------------------------------
# Proration Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_joining_month_proration_day_15():
    # Joined on 15th of 30-day month → 16 working days / 30 = 53.33%
    amount = _prorate_amount(
        monthly_amount=Decimal('30000'),
        paid_days=16,
        total_days=30,
    )
    assert amount == Decimal('16000.00')


@pytest.mark.django_db
def test_attendance_based_proration_20_of_30_days():
    # 20 present / 30 days → ₹30,000 × (20/30) = ₹20,000
    amount = _prorate_amount(
        monthly_amount=Decimal('30000'),
        paid_days=20,
        total_days=30,
    )
    assert amount == Decimal('20000.00')


@pytest.mark.django_db
def test_negative_net_pay_guarded_to_zero():
    from apps.payroll.services import ensure_non_negative_net_pay  # added in P02
    assert ensure_non_negative_net_pay(Decimal('-100')) == ZERO
    assert ensure_non_negative_net_pay(Decimal('500')) == Decimal('500')
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest apps/payroll/tests/test_statutory_calculations.py -v
```

Expected: All 18 tests PASS (after P02 is implemented).

- [ ] **Step 4: Check coverage**

```bash
cd backend && python -m pytest apps/payroll/services.py --cov=apps/payroll/services --cov-report=term-missing
```

Expected: ≥85% coverage on `services.py`.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/payroll/tests/test_statutory_calculations.py backend/apps/payroll/tests/factories.py
git commit -m "test(payroll): 18 statutory calculation unit tests with exact rupee assertions"
```

---

## Task 2 — Timeoff Service Unit Tests

**Files:**
- Create: `backend/apps/timeoff/tests/__init__.py`
- Create: `backend/apps/timeoff/tests/test_services.py`

- [ ] **Step 1: Create `__init__.py`**

```bash
touch backend/apps/timeoff/tests/__init__.py
```

- [ ] **Step 2: Create factory if not exists**

Create `backend/apps/timeoff/tests/factories.py`:

```python
import factory
from decimal import Decimal
from apps.timeoff.models import (
    LeaveType, LeavePlan, LeavePlanAssignment, LeaveLedgerEntry,
    LeaveLedgerEntryType, CarryForwardMode, LeaveRequest, LeaveRequestStatus,
)
from apps.employees.tests.factories import EmployeeFactory
from apps.accounts.tests.factories import OrganisationFactory


class LeaveTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeaveType
    organisation = factory.SubFactory(OrganisationFactory)
    name = factory.Sequence(lambda n: f'Leave Type {n}')
    code = factory.Sequence(lambda n: f'LT{n}')
    annual_allowance = Decimal('12.00')
    carry_forward_mode = CarryForwardMode.NONE
    carry_forward_cap = None
    max_balance = None
    is_lop = False


class LeaveLedgerEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeaveLedgerEntry
    employee = factory.SubFactory(EmployeeFactory)
    leave_type = factory.SubFactory(LeaveTypeFactory)
    entry_type = LeaveLedgerEntryType.ACCRUAL
    days = Decimal('1.00')
    note = ''
```

- [ ] **Step 3: Write `test_services.py`**

```python
"""
Unit tests for timeoff service functions:
- Monthly accrual
- Carry-forward cap enforcement
- Max balance enforcement
- Leave overdraw prevention
- Pending leave counted in balance
"""
from decimal import Decimal
import pytest
from datetime import date
from django.test import TestCase
from apps.timeoff.models import (
    CarryForwardMode, LeaveLedgerEntryType, LeaveRequestStatus,
)
from apps.timeoff.services import (
    credit_leave_accrual,
    process_cycle_end_carry_forward,
    validate_leave_balance,
)
from apps.timeoff.repositories import get_available_balance
from apps.timeoff.tests.factories import LeaveTypeFactory, LeaveLedgerEntryFactory
from apps.employees.tests.factories import EmployeeFactory


class TestMonthlyAccrual(TestCase):
    def test_monthly_accrual_annual_divided_by_12(self):
        """12 days annual → credit 1.00 day per month."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(annual_allowance=Decimal('12.00'))
        credit_leave_accrual(employee, leave_type, period_month=4, period_year=2024)
        balance = get_available_balance(employee.id, leave_type.id)
        self.assertEqual(balance, Decimal('1.00'))

    def test_proration_on_join_half_month(self):
        """Joining on the 16th of a 30-day month → credit 50% of monthly allowance."""
        employee = EmployeeFactory(date_of_joining=date(2024, 4, 16))
        leave_type = LeaveTypeFactory(annual_allowance=Decimal('12.00'))
        credit_leave_accrual(
            employee, leave_type,
            period_month=4, period_year=2024,
            prorate=True,
        )
        balance = get_available_balance(employee.id, leave_type.id)
        # 15 days / 30 days × 1.0 = 0.5
        self.assertEqual(balance, Decimal('0.50'))


class TestCarryForward(TestCase):
    def test_carry_forward_cap_enforced(self):
        """CAPPED mode with cap=5: employee has 8 days → only 5 carried forward."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(
            carry_forward_mode=CarryForwardMode.CAPPED,
            carry_forward_cap=Decimal('5.00'),
        )
        # Credit 8 days as current cycle accrual
        LeaveLedgerEntryFactory(employee=employee, leave_type=leave_type, days=Decimal('8.00'),
                                 entry_type=LeaveLedgerEntryType.ACCRUAL)
        process_cycle_end_carry_forward(employee, leave_type, old_cycle_year=2023, new_cycle_year=2024)
        balance = get_available_balance(employee.id, leave_type.id)
        self.assertEqual(balance, Decimal('5.00'))

    def test_carry_forward_none_zeros_balance(self):
        """NONE mode: all remaining balance is wiped at cycle end."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(carry_forward_mode=CarryForwardMode.NONE)
        LeaveLedgerEntryFactory(employee=employee, leave_type=leave_type, days=Decimal('6.00'),
                                 entry_type=LeaveLedgerEntryType.ACCRUAL)
        process_cycle_end_carry_forward(employee, leave_type, old_cycle_year=2023, new_cycle_year=2024)
        balance = get_available_balance(employee.id, leave_type.id)
        self.assertEqual(balance, Decimal('0.00'))

    def test_carry_forward_unlimited_preserves_full_balance(self):
        """UNLIMITED mode: all remaining balance carried forward."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(carry_forward_mode=CarryForwardMode.UNLIMITED)
        LeaveLedgerEntryFactory(employee=employee, leave_type=leave_type, days=Decimal('15.00'),
                                 entry_type=LeaveLedgerEntryType.ACCRUAL)
        process_cycle_end_carry_forward(employee, leave_type, old_cycle_year=2023, new_cycle_year=2024)
        balance = get_available_balance(employee.id, leave_type.id)
        self.assertEqual(balance, Decimal('15.00'))


class TestMaxBalance(TestCase):
    def test_max_balance_prevents_excess_credit(self):
        """max_balance=10: employee has 9 days, accrual of 3 should only credit 1."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(
            annual_allowance=Decimal('12.00'),
            max_balance=Decimal('10.00'),
        )
        LeaveLedgerEntryFactory(employee=employee, leave_type=leave_type, days=Decimal('9.00'),
                                 entry_type=LeaveLedgerEntryType.ACCRUAL)
        credit_leave_accrual(employee, leave_type, period_month=5, period_year=2024)
        balance = get_available_balance(employee.id, leave_type.id)
        self.assertEqual(balance, Decimal('10.00'))  # capped at max


class TestLeaveBalanceValidation(TestCase):
    def test_leave_overdraw_prevented_for_non_lop(self):
        """Non-LOP leave with 0 balance raises ValueError."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(is_lop=False)
        # No ledger entries → balance = 0
        with self.assertRaises(ValueError):
            validate_leave_balance(employee, leave_type, days_requested=Decimal('1.00'))

    def test_leave_overdraw_allowed_for_lop(self):
        """LOP leave type can always be applied regardless of balance."""
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(is_lop=True)
        # Should not raise
        validate_leave_balance(employee, leave_type, days_requested=Decimal('5.00'))

    def test_pending_leaves_included_in_available_balance(self):
        """Pending leave requests reduce available balance for new requests."""
        from apps.timeoff.tests.factories import LeaveRequestFactory
        employee = EmployeeFactory()
        leave_type = LeaveTypeFactory(is_lop=False, annual_allowance=Decimal('12.00'))
        # 5 days accrued
        LeaveLedgerEntryFactory(employee=employee, leave_type=leave_type, days=Decimal('5.00'),
                                 entry_type=LeaveLedgerEntryType.ACCRUAL)
        # 4 days pending
        LeaveRequestFactory(employee=employee, leave_type=leave_type,
                             total_days=Decimal('4.00'), status=LeaveRequestStatus.PENDING)
        # Try to apply 2 more days → only 1 available → should raise
        with self.assertRaises(ValueError):
            validate_leave_balance(employee, leave_type, days_requested=Decimal('2.00'))
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/timeoff/tests/test_services.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/timeoff/tests/
git commit -m "test(timeoff): 9 service unit tests for accrual, carry-forward, max balance, overdraw"
```

---

## Task 3 — Attendance Daily Calculation Unit Tests

**Files:**
- Create: `backend/apps/attendance/tests/test_daily_calculation.py`

- [ ] **Step 1: Write the tests**

```python
"""
Unit tests for daily attendance status calculation logic.
Tests call the service function that converts raw punch records
into a final AttendanceDayStatus for each employee-day.
"""
from decimal import Decimal
from datetime import datetime, date, time
import pytest
from django.test import TestCase
from apps.attendance.services import calculate_attendance_day_status
from apps.attendance.models import AttendanceDayStatus


# Assumed shift config (minutes):
FULL_DAY_MINUTES = 480   # 8 hours
HALF_DAY_MINUTES = 240   # 4 hours
GRACE_PERIOD_MINUTES = 15
SHIFT_START = time(9, 0)


def make_punches(checkin_dt, checkout_dt=None):
    """Helper: produce a list of punch dicts for testing."""
    punches = [{'punch_time': checkin_dt, 'direction': 'IN'}]
    if checkout_dt:
        punches.append({'punch_time': checkout_dt, 'direction': 'OUT'})
    return punches


class TestAttendanceDailyCalculation(TestCase):
    def test_present_when_worked_minutes_gte_full_day(self):
        punches = make_punches(
            checkin_dt=datetime(2024, 4, 1, 9, 0),
            checkout_dt=datetime(2024, 4, 1, 18, 0),  # 9 hours
        )
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START)
        self.assertEqual(result['status'], AttendanceDayStatus.PRESENT)

    def test_half_day_when_worked_between_half_and_full(self):
        punches = make_punches(
            checkin_dt=datetime(2024, 4, 1, 9, 0),
            checkout_dt=datetime(2024, 4, 1, 13, 0),  # 4 hours
        )
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START)
        self.assertEqual(result['status'], AttendanceDayStatus.HALF_DAY)

    def test_absent_when_worked_below_half_day(self):
        punches = make_punches(
            checkin_dt=datetime(2024, 4, 1, 9, 0),
            checkout_dt=datetime(2024, 4, 1, 11, 0),  # 2 hours < half day
        )
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START)
        self.assertEqual(result['status'], AttendanceDayStatus.ABSENT)

    def test_incomplete_when_checkin_no_checkout(self):
        punches = make_punches(checkin_dt=datetime(2024, 4, 1, 9, 0))
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START)
        self.assertEqual(result['status'], AttendanceDayStatus.INCOMPLETE)

    def test_late_mark_triggered_beyond_grace_period(self):
        # Check in at 9:20 → 20 min late, grace = 15 → late
        punches = make_punches(
            checkin_dt=datetime(2024, 4, 1, 9, 20),
            checkout_dt=datetime(2024, 4, 1, 18, 0),
        )
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START, grace_minutes=GRACE_PERIOD_MINUTES)
        self.assertTrue(result['is_late'])

    def test_not_late_within_grace_period(self):
        # Check in at 9:10 → 10 min late, grace = 15 → NOT late
        punches = make_punches(
            checkin_dt=datetime(2024, 4, 1, 9, 10),
            checkout_dt=datetime(2024, 4, 1, 18, 0),
        )
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START, grace_minutes=GRACE_PERIOD_MINUTES)
        self.assertFalse(result['is_late'])

    def test_no_punches_returns_absent(self):
        result = calculate_attendance_day_status([], shift_start=SHIFT_START)
        self.assertEqual(result['status'], AttendanceDayStatus.ABSENT)

    def test_overtime_minutes_calculated(self):
        # Work 10 hours = 600 min. Overtime = 600 - 480 = 120 min
        punches = make_punches(
            checkin_dt=datetime(2024, 4, 1, 9, 0),
            checkout_dt=datetime(2024, 4, 1, 19, 0),
        )
        result = calculate_attendance_day_status(punches, shift_start=SHIFT_START)
        self.assertEqual(result['overtime_minutes'], 120)

    def test_on_leave_overrides_absent(self):
        """If leave_override='ON_LEAVE' is passed, status should be ON_LEAVE regardless of punches."""
        result = calculate_attendance_day_status([], shift_start=SHIFT_START, leave_override='ON_LEAVE')
        self.assertEqual(result['status'], AttendanceDayStatus.ON_LEAVE)
```

- [ ] **Step 2: Run tests**

```bash
cd backend && python -m pytest apps/attendance/tests/test_daily_calculation.py -v
```

Expected: All 9 tests PASS (requires `calculate_attendance_day_status` to exist in `services.py` with the correct signature).

- [ ] **Step 3: If `calculate_attendance_day_status` does not exist, create it in `backend/apps/attendance/services.py`**

Add the function (does not replace existing functions):

```python
def calculate_attendance_day_status(
    punches: list,
    shift_start,
    full_day_minutes: int = 480,
    half_day_minutes: int = 240,
    grace_minutes: int = 15,
    leave_override: str = None,
) -> dict:
    """
    Given a list of punch dicts ({'punch_time': datetime, 'direction': 'IN'|'OUT'}),
    compute the final attendance status for that day.
    Returns dict: {status, is_late, overtime_minutes, worked_minutes}
    """
    from datetime import datetime, time as dt_time

    if leave_override == 'ON_LEAVE':
        return {
            'status': AttendanceDayStatus.ON_LEAVE,
            'is_late': False,
            'worked_minutes': 0,
            'overtime_minutes': 0,
        }

    if leave_override == 'ON_DUTY':
        return {
            'status': AttendanceDayStatus.ON_DUTY,
            'is_late': False,
            'worked_minutes': full_day_minutes,
            'overtime_minutes': 0,
        }

    ins = sorted(
        [p['punch_time'] for p in punches if p.get('direction', 'IN') == 'IN']
    )
    outs = sorted(
        [p['punch_time'] for p in punches if p.get('direction') == 'OUT']
    )

    if not ins:
        return {'status': AttendanceDayStatus.ABSENT, 'is_late': False, 'worked_minutes': 0, 'overtime_minutes': 0}

    first_in = ins[0]

    if not outs:
        return {'status': AttendanceDayStatus.INCOMPLETE, 'is_late': False, 'worked_minutes': 0, 'overtime_minutes': 0}

    last_out = outs[-1]
    worked_minutes = int((last_out - first_in).total_seconds() / 60)
    overtime_minutes = max(0, worked_minutes - full_day_minutes)

    # Late check: compare first_in time against shift_start + grace
    from datetime import datetime
    shift_start_dt = datetime.combine(first_in.date(), shift_start)
    grace_dt = shift_start_dt.replace(minute=shift_start.minute + grace_minutes) if (shift_start.minute + grace_minutes) < 60 else shift_start_dt.replace(hour=shift_start.hour + 1, minute=(shift_start.minute + grace_minutes) - 60)
    is_late = first_in > grace_dt

    if worked_minutes >= full_day_minutes:
        status = AttendanceDayStatus.PRESENT
    elif worked_minutes >= half_day_minutes:
        status = AttendanceDayStatus.HALF_DAY
    else:
        status = AttendanceDayStatus.ABSENT

    return {
        'status': status,
        'is_late': is_late,
        'worked_minutes': worked_minutes,
        'overtime_minutes': overtime_minutes,
    }
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/attendance/tests/test_daily_calculation.py backend/apps/attendance/services.py
git commit -m "test(attendance): 9 daily calculation unit tests + calculate_attendance_day_status helper"
```

---

## Task 4 — E2E: Full Payroll Run Lifecycle

**Files:**
- Create: `frontend/e2e/org/payroll.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/org/payroll.spec.ts
import { test, expect } from '@playwright/test';
import { loginAsOrgAdmin, selectOrgWorkspace } from '../helpers/auth';

test.describe('Org Admin — Payroll Run Lifecycle', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOrgAdmin(page);
    await selectOrgWorkspace(page);
  });

  test('creates a payroll run for the current month', async ({ page }) => {
    await page.goto('/org/payroll');
    await page.getByRole('button', { name: /new pay run/i }).click();
    // Select month/year
    await page.getByLabel(/month/i).selectOption({ label: 'April' });
    await page.getByLabel(/year/i).fill('2024');
    await page.getByRole('button', { name: /create/i }).click();
    await expect(page.getByText(/draft/i)).toBeVisible();
  });

  test('triggers async calculation and polls for completion', async ({ page }) => {
    await page.goto('/org/payroll');
    // Assume a DRAFT pay run exists from seed data
    await page.getByTestId('pay-run-row').first().click();
    await page.getByRole('button', { name: /calculate/i }).click();
    // Should show loading state (task dispatched)
    await expect(page.getByText(/calculating/i)).toBeVisible();
    // Poll until CALCULATED (max 30 seconds)
    await expect(page.getByText(/calculated/i)).toBeVisible({ timeout: 30000 });
  });

  test('submits pay run for approval', async ({ page }) => {
    await page.goto('/org/payroll');
    await page.getByTestId('pay-run-row').first().click();
    await page.getByRole('button', { name: /submit for approval/i }).click();
    await expect(page.getByText(/pending approval/i)).toBeVisible();
  });

  test('finalizes an approved pay run', async ({ page }) => {
    await page.goto('/org/payroll');
    await page.getByTestId('pay-run-row').filter({ hasText: /approved/i }).first().click();
    await page.getByRole('button', { name: /finalize/i }).click();
    // Confirm dialog
    await page.getByRole('button', { name: /confirm/i }).click();
    await expect(page.getByText(/finalized/i)).toBeVisible();
  });
});
```

- [ ] **Step 2: Ensure helpers file exists**

Create `frontend/e2e/helpers/auth.ts` if not present:

```typescript
import { Page } from '@playwright/test';

export async function loginAsOrgAdmin(page: Page) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(process.env.E2E_ORG_ADMIN_EMAIL ?? 'admin@test.com');
  await page.getByLabel(/password/i).fill(process.env.E2E_ORG_ADMIN_PASSWORD ?? 'testpass123');
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('/org/**', { timeout: 5000 });
}

export async function selectOrgWorkspace(page: Page) {
  // If workspace selector appears, pick first org
  const wsSelector = page.getByTestId('workspace-selector');
  if (await wsSelector.isVisible({ timeout: 2000 }).catch(() => false)) {
    await wsSelector.click();
    await page.getByTestId('workspace-option').first().click();
  }
}

export async function loginAsEmployee(page: Page) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(process.env.E2E_EMPLOYEE_EMAIL ?? 'employee@test.com');
  await page.getByLabel(/password/i).fill(process.env.E2E_EMPLOYEE_PASSWORD ?? 'testpass123');
  await page.getByRole('button', { name: /log in/i }).click();
  await page.waitForURL('/employee/**', { timeout: 5000 });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/org/payroll.spec.ts frontend/e2e/helpers/
git commit -m "test(e2e): payroll run lifecycle E2E spec"
```

---

## Task 5 — E2E: Attendance Regularization

**Files:**
- Create: `frontend/e2e/org/attendance-regularization.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/org/attendance-regularization.spec.ts
import { test, expect } from '@playwright/test';
import { loginAsEmployee, loginAsOrgAdmin, selectOrgWorkspace } from '../helpers/auth';

test.describe('Attendance Regularization Flow', () => {
  test('employee submits regularization request', async ({ page }) => {
    await loginAsEmployee(page);
    await page.goto('/employee/attendance');
    // Click on an ABSENT day
    await page.getByTestId('attendance-day-absent').first().click();
    await page.getByRole('button', { name: /regularize/i }).click();
    await page.getByLabel(/reason/i).fill('Was present but forgot to punch');
    await page.getByRole('button', { name: /submit/i }).click();
    await expect(page.getByText(/regularization request submitted/i)).toBeVisible();
  });

  test('org admin approves regularization and day status updates', async ({ page }) => {
    await loginAsOrgAdmin(page);
    await selectOrgWorkspace(page);
    await page.goto('/org/approvals');
    await page.getByTestId('approval-row').filter({ hasText: /attendance/i }).first().click();
    await page.getByRole('button', { name: /approve/i }).click();
    await expect(page.getByText(/approved/i)).toBeVisible();
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/e2e/org/attendance-regularization.spec.ts
git commit -m "test(e2e): attendance regularization approval flow E2E spec"
```

---

## Task 6 — E2E: Leave Approval Flow

**Files:**
- Create: `frontend/e2e/employee/leave-approval.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/employee/leave-approval.spec.ts
import { test, expect } from '@playwright/test';
import { loginAsEmployee, loginAsOrgAdmin, selectOrgWorkspace } from '../helpers/auth';

test.describe('Leave Approval Flow', () => {
  test('employee can submit a leave request', async ({ page }) => {
    await loginAsEmployee(page);
    await page.goto('/employee/leave');
    await page.getByRole('button', { name: /apply for leave/i }).click();
    await page.getByLabel(/leave type/i).selectOption({ index: 1 });
    // Pick start date
    await page.getByLabel(/start date/i).fill('2024-05-01');
    await page.getByLabel(/end date/i).fill('2024-05-03');
    await page.getByLabel(/reason/i).fill('Personal reasons');
    await page.getByRole('button', { name: /submit/i }).click();
    await expect(page.getByText(/leave request submitted/i)).toBeVisible();
  });

  test('balance decreases after leave is approved', async ({ page, context }) => {
    // Get current balance
    await loginAsEmployee(page);
    await page.goto('/employee/leave');
    const balanceText = await page.getByTestId('leave-balance').first().innerText();
    const initialBalance = parseFloat(balanceText);

    // Admin approves
    const adminPage = await context.newPage();
    await loginAsOrgAdmin(adminPage);
    await selectOrgWorkspace(adminPage);
    await adminPage.goto('/org/approvals');
    await adminPage.getByTestId('approval-row').filter({ hasText: /leave/i }).first().click();
    await adminPage.getByRole('button', { name: /approve/i }).click();

    // Employee balance updated
    await page.reload();
    const newBalanceText = await page.getByTestId('leave-balance').first().innerText();
    const newBalance = parseFloat(newBalanceText);
    expect(newBalance).toBeLessThan(initialBalance);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/e2e/employee/leave-approval.spec.ts
git commit -m "test(e2e): employee leave request + approval balance update E2E spec"
```

---

## Task 7 — E2E: Payslip View and Download

**Files:**
- Create: `frontend/e2e/employee/payslips.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/employee/payslips.spec.ts
import { test, expect } from '@playwright/test';
import { loginAsEmployee } from '../helpers/auth';

test.describe('Employee Payslips', () => {
  test('employee can view payslip details', async ({ page }) => {
    await loginAsEmployee(page);
    await page.goto('/employee/payslips');
    await expect(page.getByTestId('payslip-row')).toHaveCount.greaterThan(0);
    await page.getByTestId('payslip-row').first().click();
    await expect(page.getByText(/gross earnings/i)).toBeVisible();
    await expect(page.getByText(/deductions/i)).toBeVisible();
    await expect(page.getByText(/net pay/i)).toBeVisible();
  });

  test('employee can download payslip as PDF', async ({ page }) => {
    await loginAsEmployee(page);
    await page.goto('/employee/payslips');
    await page.getByTestId('payslip-row').first().click();
    // Listen for download
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /download/i }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/payslip.*\.pdf/i);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/e2e/employee/payslips.spec.ts
git commit -m "test(e2e): employee payslip view and PDF download E2E spec"
```

---

## Task 8 — Frontend Unit Tests

**Files:**
- Create: `frontend/src/pages/org/PayrollPage.test.tsx`
- Create: `frontend/src/pages/employee/LeavePage.test.tsx`
- Create: `frontend/src/pages/employee/AttendancePage.test.tsx`

- [ ] **Step 1: Write `PayrollPage.test.tsx`**

```tsx
// frontend/src/pages/org/PayrollPage.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PayrollPage from './PayrollPage';

// Mock API calls
vi.mock('@/lib/api/org-admin', () => ({
  getPayrollSummary: vi.fn().mockResolvedValue({
    tax_slab_sets: [],
    components: [],
    compensation_templates: [],
    compensation_assignments: [],
    pay_runs: [],
    payslip_count: 0,
  }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe('PayrollPage', () => {
  it('renders without crashing', async () => {
    render(<PayrollPage />, { wrapper });
    expect(screen.getByText(/payroll/i)).toBeDefined();
  });

  it('shows empty state when no pay runs exist', async () => {
    render(<PayrollPage />, { wrapper });
    // Wait for query to resolve
    expect(await screen.findByText(/no pay runs/i)).toBeDefined();
  });
});
```

- [ ] **Step 2: Write `LeavePage.test.tsx`**

```tsx
// frontend/src/pages/employee/LeavePage.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import LeavePage from './LeavePage';

vi.mock('@/lib/api/employee', () => ({
  getMyLeaveBalances: vi.fn().mockResolvedValue([
    { leave_type: { name: 'Casual Leave' }, available: 5 },
  ]),
  getMyLeaveRequests: vi.fn().mockResolvedValue([]),
  getLeaveTypes: vi.fn().mockResolvedValue([
    { id: 'lt-1', name: 'Casual Leave', code: 'CL' },
  ]),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe('LeavePage', () => {
  it('renders leave balance', async () => {
    render(<LeavePage />, { wrapper });
    expect(await screen.findByText(/casual leave/i)).toBeDefined();
    expect(await screen.findByText('5')).toBeDefined();
  });

  it('shows apply leave form when button clicked', async () => {
    render(<LeavePage />, { wrapper });
    const applyBtn = await screen.findByRole('button', { name: /apply/i });
    fireEvent.click(applyBtn);
    expect(screen.getByLabelText(/leave type/i)).toBeDefined();
  });
});
```

- [ ] **Step 3: Write `AttendancePage.test.tsx`**

```tsx
// frontend/src/pages/employee/AttendancePage.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AttendancePage from './AttendancePage';

vi.mock('@/lib/api/employee', () => ({
  getMyAttendance: vi.fn().mockResolvedValue({
    days: [],
    total_present: 0,
    total_absent: 0,
    total_half_day: 0,
  }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe('AttendancePage', () => {
  it('renders attendance summary', async () => {
    render(<AttendancePage />, { wrapper });
    expect(await screen.findByText(/present/i)).toBeDefined();
    expect(await screen.findByText(/absent/i)).toBeDefined();
  });
});
```

- [ ] **Step 4: Run Vitest**

```bash
cd frontend && npx vitest run src/pages/org/PayrollPage.test.tsx src/pages/employee/LeavePage.test.tsx src/pages/employee/AttendancePage.test.tsx
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/org/PayrollPage.test.tsx \
        frontend/src/pages/employee/LeavePage.test.tsx \
        frontend/src/pages/employee/AttendancePage.test.tsx
git commit -m "test(frontend): unit tests for PayrollPage, LeavePage, AttendancePage"
```

---

## Task 9 — Coverage Check and Gap Fill

- [ ] **Step 1: Generate backend coverage report**

```bash
cd backend && python -m pytest --cov=apps/payroll/services --cov=apps/timeoff/services --cov=apps/attendance/services --cov-report=term-missing --cov-fail-under=80
```

- [ ] **Step 2: Generate frontend coverage report**

```bash
cd frontend && npx vitest run --coverage
```

Expected: Coverage report shows all new service functions covered.

- [ ] **Step 3: Fix any gaps surfaced by coverage report**

Add additional tests for any uncovered lines identified in the reports. Follow TDD — write test, see fail, implement or confirm coverage.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: fill coverage gaps identified by coverage reports"
```
