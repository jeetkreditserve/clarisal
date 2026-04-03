# P03 — Leave Service Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two silent policy-violation bugs (carry-forward cap not enforced, max balance not enforced) and add leave encashment as a first-class feature with model, approval workflow, and API endpoints.

**Architecture:** All changes are in `backend/apps/timeoff/`. The existing `LeaveBalance`/`LeaveBalanceLedgerEntry` pattern is extended. Carry-forward and max balance logic is added to the existing cycle-end service function. Encashment follows the same approval-workflow integration pattern used by `AttendanceRegularizationRequest` and `LeaveRequest`.

**Tech Stack:** Django 4.2 · DRF · pytest · factory-boy

---

## Audit Findings Addressed

| ID | Finding | Severity |
|----|---------|----------|
| F6-02 | `carry_forward_cap` field exists but never enforced in service | 🟠 High |
| F6-03 | `max_balance` field exists but never checked before crediting | 🟠 High |
| Phase 1 | No leave encashment model or workflow | ❌ Missing |

---

## Prerequisite: Read these files before starting

- `backend/apps/timeoff/models.py` — understand `LeaveType`, `LeaveBalance`, `LeaveBalanceLedgerEntry`, `LeaveCycle`, `LeaveRequest`
- `backend/apps/timeoff/services.py` — find `credit_leave()`, the carry-forward function, and `create_leave_request()`
- `backend/apps/approvals/models.py` — understand `ApprovalWorkflow`, `ApprovalRun` (encashment will use this)

---

## File Structure

```
backend/apps/timeoff/
  models.py                   MODIFY — add LeaveEncashmentPolicy, LeaveEncashmentRequest
  services.py                 MODIFY — enforce carry-forward cap + max balance; add encashment services
  serializers.py              MODIFY — add encashment serializers
  org_urls.py                 MODIFY — add encashment org endpoints
  self_urls.py                MODIFY — add encashment employee endpoints
  views.py                    MODIFY — add encashment views
  migrations/
    000X_add_leave_encashment.py    CREATE
  tests/
    __init__.py                CREATE (if not exists)
    test_services.py           CREATE — carry-forward, max balance, encashment tests
    test_views.py              CREATE — encashment API endpoint tests
```

---

## Task 1: Enforce Carry-Forward Cap in Leave Service

**Files:** `backend/apps/timeoff/services.py`, `backend/apps/timeoff/tests/test_services.py` (new)

Context: `LeaveType.carry_forward_mode` can be `NONE`, `CAPPED`, or `UNLIMITED`. `LeaveType.carry_forward_cap` is the maximum days that can carry over. Currently, the service that processes cycle-end carry-forward never reads `carry_forward_cap`, so employees carry over unlimited days regardless of the configured cap.

- [x] **Step 1: Create tests directory and write failing tests**

  ```bash
  mkdir -p backend/apps/timeoff/tests
  touch backend/apps/timeoff/tests/__init__.py
  ```

  Create `backend/apps/timeoff/tests/test_services.py`:
  ```python
  """
  Tests for timeoff service layer.
  Tests MUST be run with pytest-django (uses @pytest.mark.django_db).
  Uses factory_boy fixtures defined in conftest.py.
  """
  import pytest
  from decimal import Decimal
  from datetime import date
  from apps.timeoff.models import (
      LeaveBalance, LeaveBalanceLedgerEntry, LeaveType, LeaveCycle,
      CarryForwardMode,
  )


  @pytest.mark.django_db
  class TestCarryForwardCapEnforcement:

      def _setup_leave_balance(self, leave_type, employee, cycle, balance_amount):
          """Helper: set up a leave balance for testing carry-forward."""
          lb, _ = LeaveBalance.objects.get_or_create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              defaults={
                  'opening_balance': ZERO,
                  'credited_amount': balance_amount,
                  'used_amount': ZERO,
                  'pending_amount': ZERO,
                  'carried_forward_amount': ZERO,
              }
          )
          lb.credited_amount = balance_amount
          lb.save(update_fields=['credited_amount'])
          return lb

      def test_carry_forward_none_produces_zero_balance_in_new_cycle(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """LeaveType with carry_forward_mode=NONE should carry over ₹0."""
          from apps.timeoff.services import process_cycle_end_carry_forward
          employee = employee_factory(organisation=organisation)
          old_cycle = leave_cycle_factory(organisation=organisation)
          new_cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              annual_entitlement=Decimal('12'),
              carry_forward_mode=CarryForwardMode.NONE,
              carry_forward_cap=None,
          )
          self._setup_leave_balance(leave_type, employee, old_cycle, Decimal('5'))

          process_cycle_end_carry_forward(
              employee=employee,
              leave_type=leave_type,
              old_cycle=old_cycle,
              new_cycle=new_cycle,
          )

          new_balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=new_cycle
          )
          assert new_balance.opening_balance == Decimal('0')

      def test_carry_forward_capped_respects_cap(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """LeaveType with carry_forward_mode=CAPPED, cap=5 should carry over max 5 days."""
          from apps.timeoff.services import process_cycle_end_carry_forward
          employee = employee_factory(organisation=organisation)
          old_cycle = leave_cycle_factory(organisation=organisation)
          new_cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              carry_forward_mode=CarryForwardMode.CAPPED,
              carry_forward_cap=Decimal('5'),
          )
          # Employee has 10 days remaining — only 5 should carry forward
          self._setup_leave_balance(leave_type, employee, old_cycle, Decimal('10'))

          process_cycle_end_carry_forward(
              employee=employee,
              leave_type=leave_type,
              old_cycle=old_cycle,
              new_cycle=new_cycle,
          )

          new_balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=new_cycle
          )
          assert new_balance.opening_balance == Decimal('5'), (
              f"Expected 5 days carry-forward (capped) but got {new_balance.opening_balance}"
          )

      def test_carry_forward_capped_with_balance_below_cap_carries_full_balance(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """If remaining balance < cap, entire remaining balance carries forward."""
          from apps.timeoff.services import process_cycle_end_carry_forward
          employee = employee_factory(organisation=organisation)
          old_cycle = leave_cycle_factory(organisation=organisation)
          new_cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              carry_forward_mode=CarryForwardMode.CAPPED,
              carry_forward_cap=Decimal('10'),
          )
          self._setup_leave_balance(leave_type, employee, old_cycle, Decimal('3'))

          process_cycle_end_carry_forward(
              employee=employee, leave_type=leave_type,
              old_cycle=old_cycle, new_cycle=new_cycle,
          )

          new_balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=new_cycle
          )
          assert new_balance.opening_balance == Decimal('3')

      def test_carry_forward_unlimited_carries_full_balance(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """UNLIMITED carry-forward should preserve all remaining days."""
          from apps.timeoff.services import process_cycle_end_carry_forward
          employee = employee_factory(organisation=organisation)
          old_cycle = leave_cycle_factory(organisation=organisation)
          new_cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              carry_forward_mode=CarryForwardMode.UNLIMITED,
              carry_forward_cap=None,
          )
          self._setup_leave_balance(leave_type, employee, old_cycle, Decimal('45'))

          process_cycle_end_carry_forward(
              employee=employee, leave_type=leave_type,
              old_cycle=old_cycle, new_cycle=new_cycle,
          )

          new_balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=new_cycle
          )
          assert new_balance.opening_balance == Decimal('45')

      def test_carry_forward_creates_ledger_entry(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """Carry-forward must create a CARRY_FORWARD ledger entry."""
          from apps.timeoff.services import process_cycle_end_carry_forward
          from apps.timeoff.models import LeaveBalanceLedgerEntryType
          employee = employee_factory(organisation=organisation)
          old_cycle = leave_cycle_factory(organisation=organisation)
          new_cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              carry_forward_mode=CarryForwardMode.CAPPED,
              carry_forward_cap=Decimal('5'),
          )
          self._setup_leave_balance(leave_type, employee, old_cycle, Decimal('8'))

          process_cycle_end_carry_forward(
              employee=employee, leave_type=leave_type,
              old_cycle=old_cycle, new_cycle=new_cycle,
          )

          ledger_entry = LeaveBalanceLedgerEntry.objects.filter(
              employee=employee,
              leave_type=leave_type,
              cycle=new_cycle,
              entry_type=LeaveBalanceLedgerEntryType.CARRY_FORWARD,
          ).first()
          assert ledger_entry is not None
          assert ledger_entry.amount == Decimal('5')
  ```

  Run:
  ```bash
  cd backend
  pytest apps/timeoff/tests/test_services.py::TestCarryForwardCapEnforcement -v
  # Expected: FAIL — process_cycle_end_carry_forward does not exist or doesn't enforce cap
  ```

- [x] **Step 2: Implement `process_cycle_end_carry_forward()` in `timeoff/services.py`**

  Find the existing carry-forward logic in `backend/apps/timeoff/services.py` (search for `CARRY_FORWARD` or `carry_forward`). If a function already exists, modify it. If not, add:

  ```python
  from django.db import transaction

  @transaction.atomic
  def process_cycle_end_carry_forward(employee, leave_type, old_cycle, new_cycle):
      """
      Compute and apply carry-forward from old_cycle to new_cycle for a given employee/leave_type.
      Respects carry_forward_mode (NONE/CAPPED/UNLIMITED) and carry_forward_cap.
      Creates a LeaveBalance for new_cycle with opening_balance = carry_forward amount.
      Creates a CARRY_FORWARD ledger entry in the new cycle.
      """
      from apps.timeoff.models import (
          LeaveBalance, LeaveBalanceLedgerEntry, CarryForwardMode,
          LeaveBalanceLedgerEntryType,
      )

      # Get the ending balance from old cycle
      try:
          old_balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=old_cycle
          )
      except LeaveBalance.DoesNotExist:
          return  # No balance in old cycle — nothing to carry forward

      available_balance = (
          old_balance.opening_balance
          + old_balance.credited_amount
          - old_balance.used_amount
          - old_balance.pending_amount
      )

      # Determine carry-forward amount based on mode
      mode = leave_type.carry_forward_mode
      if mode == CarryForwardMode.NONE:
          carry_forward_amount = Decimal('0')
      elif mode == CarryForwardMode.CAPPED:
          cap = leave_type.carry_forward_cap or Decimal('0')
          carry_forward_amount = min(available_balance, cap)
      elif mode == CarryForwardMode.UNLIMITED:
          carry_forward_amount = max(Decimal('0'), available_balance)
      else:
          carry_forward_amount = Decimal('0')

      carry_forward_amount = max(Decimal('0'), carry_forward_amount)

      # Record carry-forward on old balance for audit
      old_balance.carried_forward_amount = carry_forward_amount
      old_balance.save(update_fields=['carried_forward_amount'])

      if carry_forward_amount == Decimal('0'):
          return

      # Create or update new cycle balance
      new_balance, created = LeaveBalance.objects.get_or_create(
          employee=employee,
          leave_type=leave_type,
          cycle=new_cycle,
          defaults={
              'opening_balance': carry_forward_amount,
              'credited_amount': Decimal('0'),
              'used_amount': Decimal('0'),
              'pending_amount': Decimal('0'),
              'carried_forward_amount': Decimal('0'),
          },
      )
      if not created:
          new_balance.opening_balance += carry_forward_amount
          new_balance.save(update_fields=['opening_balance'])

      # Create ledger entry
      LeaveBalanceLedgerEntry.objects.create(
          employee=employee,
          leave_type=leave_type,
          cycle=new_cycle,
          entry_type=LeaveBalanceLedgerEntryType.CARRY_FORWARD,
          amount=carry_forward_amount,
          effective_date=new_cycle.start_date if hasattr(new_cycle, 'start_date') else None,
          note=f'Carry-forward from cycle {old_cycle}',
      )
  ```

- [x] **Step 3: Run tests to verify carry-forward tests pass**

  ```bash
  cd backend
  pytest apps/timeoff/tests/test_services.py::TestCarryForwardCapEnforcement -v
  # Expected: all PASS
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add backend/apps/timeoff/services.py backend/apps/timeoff/tests/
  git commit -m "fix(leave): enforce carry_forward_cap and carry_forward_mode in cycle-end processing"
  ```

---

## Task 2: Enforce Max Balance Before Crediting

**Files:** `backend/apps/timeoff/services.py`, `backend/apps/timeoff/tests/test_services.py`

- [x] **Step 1: Write the failing tests**

  Add to `test_services.py`:
  ```python
  @pytest.mark.django_db
  class TestMaxBalanceEnforcement:

      def test_credit_does_not_exceed_max_balance(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """If crediting would push balance past max_balance, only credit up to max."""
          from apps.timeoff.services import credit_leave_for_period
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              annual_entitlement=Decimal('24'),
              credit_frequency='MONTHLY',
              max_balance=Decimal('15'),
          )
          # Pre-populate with 13 days already in balance
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('13'),
              used_amount=Decimal('0'), pending_amount=Decimal('0'),
              carried_forward_amount=Decimal('0'),
          )

          # Monthly credit = 24/12 = 2 days. Balance would go 13 + 2 = 15 (exactly at cap).
          credit_leave_for_period(employee=employee, leave_type=leave_type, cycle=cycle)

          balance = LeaveBalance.objects.get(employee=employee, leave_type=leave_type, cycle=cycle)
          assert balance.credited_amount == Decimal('15'), (
              f"Expected 15 total credited (capped at max_balance) but got {balance.credited_amount}"
          )

      def test_credit_denied_when_already_at_max_balance(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """If balance is already at max_balance, no credit is added."""
          from apps.timeoff.services import credit_leave_for_period
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              annual_entitlement=Decimal('12'),
              credit_frequency='MONTHLY',
              max_balance=Decimal('10'),
          )
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('10'),
              used_amount=Decimal('0'), pending_amount=Decimal('0'),
              carried_forward_amount=Decimal('0'),
          )

          credit_leave_for_period(employee=employee, leave_type=leave_type, cycle=cycle)

          balance = LeaveBalance.objects.get(employee=employee, leave_type=leave_type, cycle=cycle)
          assert balance.credited_amount == Decimal('10')  # Unchanged

      def test_max_balance_none_means_no_cap(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """If max_balance is None, there is no cap on credits."""
          from apps.timeoff.services import credit_leave_for_period
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              annual_entitlement=Decimal('24'),
              credit_frequency='MONTHLY',
              max_balance=None,
          )
          # Current balance: 20 days (large)
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('20'),
              used_amount=Decimal('0'), pending_amount=Decimal('0'),
              carried_forward_amount=Decimal('0'),
          )
          credit_leave_for_period(employee=employee, leave_type=leave_type, cycle=cycle)

          balance = LeaveBalance.objects.get(employee=employee, leave_type=leave_type, cycle=cycle)
          assert balance.credited_amount == Decimal('22')  # 20 + 2 (monthly = 24/12)
  ```

  Run:
  ```bash
  pytest apps/timeoff/tests/test_services.py::TestMaxBalanceEnforcement -v
  # Expected: FAIL
  ```

- [x] **Step 2: Modify `credit_leave_for_period()` in `timeoff/services.py`**

  Find the function that credits monthly leave (look for `credit_frequency` logic). Add the max balance check:

  ```python
  def credit_leave_for_period(employee, leave_type, cycle, credit_date=None):
      """
      Credit the appropriate leave amount for one period.
      Respects max_balance cap if set.
      """
      from apps.timeoff.models import LeaveBalance, LeaveBalanceLedgerEntry, LeaveBalanceLedgerEntryType

      # Calculate credit amount based on frequency
      credit_amount = _calculate_period_credit(leave_type)
      if credit_amount <= ZERO:
          return

      balance, _ = LeaveBalance.objects.get_or_create(
          employee=employee, leave_type=leave_type, cycle=cycle,
          defaults={
              'opening_balance': ZERO, 'credited_amount': ZERO,
              'used_amount': ZERO, 'pending_amount': ZERO,
              'carried_forward_amount': ZERO,
          },
      )

      # Enforce max_balance cap
      if leave_type.max_balance is not None:
          current_total = balance.opening_balance + balance.credited_amount
          available_capacity = leave_type.max_balance - current_total
          if available_capacity <= ZERO:
              return  # Already at or above max — no credit
          credit_amount = min(credit_amount, available_capacity)

      # Apply credit
      balance.credited_amount += credit_amount
      balance.save(update_fields=['credited_amount'])

      LeaveBalanceLedgerEntry.objects.create(
          employee=employee,
          leave_type=leave_type,
          cycle=cycle,
          entry_type=LeaveBalanceLedgerEntryType.CREDIT,
          amount=credit_amount,
          effective_date=credit_date or date.today(),
          note=f'Periodic credit ({leave_type.credit_frequency})',
      )
  ```

- [x] **Step 3: Run tests and commit**

  ```bash
  pytest apps/timeoff/tests/test_services.py -v
  # Expected: all PASS

  git add backend/apps/timeoff/services.py
  git commit -m "fix(leave): enforce max_balance cap before crediting leave — prevents balance exceeding configured maximum"
  ```

---

## Task 3: Add Leave Overdraw and Balance Tests

**Files:** `backend/apps/timeoff/tests/test_services.py`

- [-] **Step 1: Write the failing tests**

  Add to `test_services.py`:
  ```python
  @pytest.mark.django_db
  class TestLeaveBalanceValidation:

      def test_non_lop_leave_overdraw_prevented(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """Employees cannot take more non-LOP leave than available balance."""
          from apps.timeoff.services import validate_leave_balance
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              is_loss_of_pay=False,
          )
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('5'),
              used_amount=Decimal('0'), pending_amount=Decimal('0'),
              carried_forward_amount=Decimal('0'),
          )

          with pytest.raises(ValueError, match='insufficient.*balance|not enough.*leave'):
              validate_leave_balance(
                  employee=employee, leave_type=leave_type, cycle=cycle,
                  requested_units=Decimal('6'),
              )

      def test_pending_leaves_count_against_available_balance(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """Pending (not yet approved) leaves reduce available balance."""
          from apps.timeoff.services import validate_leave_balance
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation, is_loss_of_pay=False,
          )
          # Balance: 10 credited, 2 pending
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('10'),
              used_amount=Decimal('0'), pending_amount=Decimal('2'),
              carried_forward_amount=Decimal('0'),
          )

          # Available = 10 - 0 (used) - 2 (pending) = 8. Request for 9 should fail.
          with pytest.raises(ValueError):
              validate_leave_balance(
                  employee=employee, leave_type=leave_type, cycle=cycle,
                  requested_units=Decimal('9'),
              )

      def test_lop_leave_allows_overdraw(
          self, employee_factory, leave_type_factory, leave_cycle_factory, organisation
      ):
          """Loss-of-pay leave type allows overdraw."""
          from apps.timeoff.services import validate_leave_balance
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              is_loss_of_pay=True,
          )
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('0'),
              used_amount=Decimal('0'), pending_amount=Decimal('0'),
              carried_forward_amount=Decimal('0'),
          )
          # Should NOT raise even though balance is 0
          validate_leave_balance(
              employee=employee, leave_type=leave_type, cycle=cycle,
              requested_units=Decimal('5'),
          )
  ```

  Run:
  ```bash
  pytest apps/timeoff/tests/test_services.py::TestLeaveBalanceValidation -v
  # Expected: FAIL
  ```

- [-] **Step 2: Add `validate_leave_balance()` function to `services.py`**

  In `backend/apps/timeoff/services.py`, add:
  ```python
  def validate_leave_balance(employee, leave_type, cycle, requested_units: Decimal):
      """
      Validate that the employee has sufficient leave balance for the requested units.
      For non-LOP leave: raises ValueError if balance insufficient.
      For LOP leave: always passes.
      """
      if leave_type.is_loss_of_pay:
          return  # LOP always allowed

      try:
          balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=cycle
          )
          available = (
              balance.opening_balance
              + balance.credited_amount
              - balance.used_amount
              - balance.pending_amount
          )
      except LeaveBalance.DoesNotExist:
          available = Decimal('0')

      if requested_units > available:
          raise ValueError(
              f"Insufficient leave balance. Available: {available} days, "
              f"Requested: {requested_units} days."
          )
  ```

- [ ] **Step 3: Run tests and commit**

  ```bash
  pytest apps/timeoff/tests/test_services.py -v
  # Expected: all PASS

  git add backend/apps/timeoff/services.py
  git commit -m "refactor(leave): extract validate_leave_balance() and add comprehensive balance tests"
  ```

---

## Task 4: Add Leave Encashment Model and Approval Workflow

**Files:** `backend/apps/timeoff/models.py`, migration

- [ ] **Step 1: Write the failing test**

  Add to `test_services.py`:
  ```python
  @pytest.mark.django_db
  class TestLeaveEncashment:

      def test_encashment_request_created_with_pending_approval(
          self, employee_factory, leave_type_factory, leave_cycle_factory,
          approval_workflow_factory, organisation
      ):
          from apps.timeoff.services import create_leave_encashment_request
          from apps.timeoff.models import LeaveEncashmentRequest, LeaveEncashmentStatus
          employee = employee_factory(organisation=organisation)
          cycle = leave_cycle_factory(organisation=organisation)
          leave_type = leave_type_factory(
              organisation=organisation,
              allows_encashment=True,
          )
          LeaveBalance.objects.create(
              employee=employee, leave_type=leave_type, cycle=cycle,
              opening_balance=Decimal('0'), credited_amount=Decimal('10'),
              used_amount=Decimal('0'), pending_amount=Decimal('0'),
              carried_forward_amount=Decimal('0'),
          )
          workflow = approval_workflow_factory(organisation=organisation)

          request = create_leave_encashment_request(
              employee=employee,
              leave_type=leave_type,
              cycle=cycle,
              days_to_encash=Decimal('5'),
              actor=employee.user,
          )

          assert request.status == LeaveEncashmentStatus.PENDING
          assert request.days_to_encash == Decimal('5')
          assert request.approval_run is not None
  ```

  Run:
  ```bash
  pytest apps/timeoff/tests/test_services.py::TestLeaveEncashment -v
  # Expected: FAIL
  ```

- [ ] **Step 2: Add `allows_encashment` to `LeaveType` and create encashment models**

  In `backend/apps/timeoff/models.py`:

  Add to `LeaveType`:
  ```python
  allows_encashment = models.BooleanField(
      default=False,
      help_text='Whether employees can request encashment of this leave type.',
  )
  max_encashment_days_per_year = models.DecimalField(
      max_digits=5, decimal_places=2, null=True, blank=True,
      help_text='Maximum days that can be encashed per cycle. Null = no limit.',
  )
  ```

  Add new model classes:
  ```python
  class LeaveEncashmentStatus(models.TextChoices):
      PENDING = 'PENDING', 'Pending Approval'
      APPROVED = 'APPROVED', 'Approved'
      REJECTED = 'REJECTED', 'Rejected'
      PAID = 'PAID', 'Paid'
      CANCELLED = 'CANCELLED', 'Cancelled'


  class LeaveEncashmentRequest(AuditedBaseModel):
      """Employee request to encash leave balance as monetary compensation."""
      employee = models.ForeignKey(
          'employees.Employee',
          on_delete=models.CASCADE,
          related_name='leave_encashment_requests',
      )
      leave_type = models.ForeignKey(
          LeaveType,
          on_delete=models.PROTECT,
          related_name='encashment_requests',
      )
      cycle = models.ForeignKey(
          LeaveCycle,
          on_delete=models.PROTECT,
          related_name='encashment_requests',
      )
      days_to_encash = models.DecimalField(max_digits=5, decimal_places=2)
      encashment_amount = models.DecimalField(
          max_digits=12, decimal_places=2, null=True, blank=True,
          help_text='Calculated encashment amount (days × daily rate).',
      )
      status = models.CharField(
          max_length=20, choices=LeaveEncashmentStatus.choices,
          default=LeaveEncashmentStatus.PENDING,
      )
      approval_run = models.ForeignKey(
          'approvals.ApprovalRun',
          null=True, blank=True,
          on_delete=models.SET_NULL,
          related_name='leave_encashment_requests',
      )
      rejection_reason = models.TextField(blank=True)
      paid_in_pay_run = models.ForeignKey(
          'payroll.PayrollRun',
          null=True, blank=True,
          on_delete=models.SET_NULL,
          related_name='leave_encashments',
      )

      class Meta:
          ordering = ['-created_at']
          indexes = [
              models.Index(fields=['employee', 'status']),
          ]

      def handle_approval_status_change(self, new_status: str, actor):
          """Called by approval service when approval run completes."""
          from apps.timeoff.services import finalize_leave_encashment
          if new_status == 'APPROVED':
              self.status = LeaveEncashmentStatus.APPROVED
              self.save(update_fields=['status'])
              finalize_leave_encashment(self, actor)
          elif new_status == 'REJECTED':
              self.status = LeaveEncashmentStatus.REJECTED
              self.save(update_fields=['status'])
  ```

  Create migration:
  ```bash
  python manage.py makemigrations timeoff --name add_leave_encashment
  ```

- [ ] **Step 3: Add encashment service functions**

  In `backend/apps/timeoff/services.py`, add:
  ```python
  def create_leave_encashment_request(
      employee, leave_type, cycle, days_to_encash: Decimal, actor
  ) -> 'LeaveEncashmentRequest':
      """
      Create a leave encashment request and trigger the approval workflow.
      Validates:
      - Leave type allows encashment
      - Employee has sufficient balance
      - Does not exceed max_encashment_days_per_year
      """
      from apps.timeoff.models import LeaveEncashmentRequest, LeaveEncashmentStatus
      from apps.approvals.services import create_approval_run

      if not leave_type.allows_encashment:
          raise ValueError(f"Leave type '{leave_type.name}' does not allow encashment.")

      # Validate balance
      try:
          balance = LeaveBalance.objects.get(
              employee=employee, leave_type=leave_type, cycle=cycle
          )
          available = (
              balance.opening_balance + balance.credited_amount
              - balance.used_amount - balance.pending_amount
          )
      except LeaveBalance.DoesNotExist:
          available = Decimal('0')

      if days_to_encash > available:
          raise ValueError(
              f"Cannot encash {days_to_encash} days. Available balance: {available} days."
          )

      if leave_type.max_encashment_days_per_year:
          already_encashed = LeaveEncashmentRequest.objects.filter(
              employee=employee, leave_type=leave_type, cycle=cycle,
              status__in=[LeaveEncashmentStatus.PENDING, LeaveEncashmentStatus.APPROVED, LeaveEncashmentStatus.PAID],
          ).aggregate(total=Sum('days_to_encash'))['total'] or Decimal('0')
          if already_encashed + days_to_encash > leave_type.max_encashment_days_per_year:
              raise ValueError(
                  f"Exceeds annual encashment limit of {leave_type.max_encashment_days_per_year} days."
              )

      encashment_request = LeaveEncashmentRequest.objects.create(
          employee=employee,
          leave_type=leave_type,
          cycle=cycle,
          days_to_encash=days_to_encash,
          status=LeaveEncashmentStatus.PENDING,
      )

      # Get or find the encashment approval workflow
      workflow = _get_leave_approval_workflow(employee)
      if workflow:
          approval_run = create_approval_run(
              workflow=workflow,
              request_kind='LEAVE_ENCASHMENT',
              requested_by_employee=employee,
              requested_by_user=actor,
              content_object=encashment_request,
          )
          encashment_request.approval_run = approval_run
          encashment_request.save(update_fields=['approval_run'])

      return encashment_request


  def finalize_leave_encashment(encashment_request, actor):
      """
      Called when an encashment request is approved.
      Debits the leave balance and flags the request as approved.
      """
      from apps.timeoff.models import LeaveBalanceLedgerEntry, LeaveBalanceLedgerEntryType

      balance = LeaveBalance.objects.select_for_update().get(
          employee=encashment_request.employee,
          leave_type=encashment_request.leave_type,
          cycle=encashment_request.cycle,
      )
      balance.used_amount += encashment_request.days_to_encash
      balance.save(update_fields=['used_amount'])

      LeaveBalanceLedgerEntry.objects.create(
          employee=encashment_request.employee,
          leave_type=encashment_request.leave_type,
          cycle=encashment_request.cycle,
          entry_type=LeaveBalanceLedgerEntryType.DEBIT,
          amount=encashment_request.days_to_encash,
          effective_date=date.today(),
          note=f'Leave encashment — {encashment_request.days_to_encash} days',
      )
  ```

- [ ] **Step 4: Run all timeoff tests and commit**

  ```bash
  cd backend
  pytest apps/timeoff/tests/ -v
  # Expected: all PASS

  git add backend/apps/timeoff/
  git commit -m "feat(leave): add leave encashment model, validation, and approval workflow integration"
  ```

---

## Task 5: Add Encashment API Endpoints

**Files:** `backend/apps/timeoff/serializers.py`, `views.py`, `org_urls.py`, `self_urls.py`

- [ ] **Step 1: Add serializers**

  In `backend/apps/timeoff/serializers.py`, add:
  ```python
  class LeaveEncashmentRequestSerializer(serializers.ModelSerializer):
      employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
      leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

      class Meta:
          model = LeaveEncashmentRequest
          fields = [
              'id', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
              'cycle', 'days_to_encash', 'encashment_amount', 'status',
              'approval_run', 'rejection_reason', 'created_at',
          ]
          read_only_fields = ['id', 'status', 'approval_run', 'encashment_amount', 'created_at']


  class LeaveEncashmentRequestCreateSerializer(serializers.Serializer):
      leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all())
      cycle = serializers.PrimaryKeyRelatedField(queryset=LeaveCycle.objects.all())
      days_to_encash = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0.5'))

      def validate_days_to_encash(self, value):
          if value <= 0:
              raise serializers.ValidationError("Days to encash must be positive.")
          return value
  ```

- [ ] **Step 2: Add views**

  In `backend/apps/timeoff/views.py`, add:
  ```python
  class MyLeaveEncashmentListCreateView(APIView):
      """Employee submits and lists their own encashment requests."""
      permission_classes = [IsEmployee, BelongsToActiveOrg]

      def get(self, request):
          employee = _get_active_employee(request)
          qs = LeaveEncashmentRequest.objects.filter(employee=employee).order_by('-created_at')
          return Response(LeaveEncashmentRequestSerializer(qs, many=True).data)

      def post(self, request):
          employee = _get_active_employee(request)
          serializer = LeaveEncashmentRequestCreateSerializer(data=request.data)
          serializer.is_valid(raise_exception=True)
          try:
              encashment = create_leave_encashment_request(
                  employee=employee,
                  leave_type=serializer.validated_data['leave_type'],
                  cycle=serializer.validated_data['cycle'],
                  days_to_encash=serializer.validated_data['days_to_encash'],
                  actor=request.user,
              )
          except ValueError as e:
              return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
          return Response(
              LeaveEncashmentRequestSerializer(encashment).data,
              status=status.HTTP_201_CREATED,
          )


  class OrgLeaveEncashmentListView(APIView):
      """Org admin views all encashment requests in their organisation."""
      permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

      def get(self, request):
          organisation = _get_admin_organisation(request)
          qs = LeaveEncashmentRequest.objects.filter(
              employee__organisation=organisation
          ).select_related('employee__user', 'leave_type').order_by('-created_at')
          return Response(LeaveEncashmentRequestSerializer(qs, many=True).data)
  ```

- [ ] **Step 3: Register URLs**

  In `backend/apps/timeoff/self_urls.py`, add:
  ```python
  path('leave-encashments/', MyLeaveEncashmentListCreateView.as_view(), name='my-leave-encashments'),
  ```

  In `backend/apps/timeoff/org_urls.py`, add:
  ```python
  path('leave-encashments/', OrgLeaveEncashmentListView.as_view(), name='org-leave-encashments'),
  ```

- [ ] **Step 4: Run full test suite and commit**

  ```bash
  cd backend
  pytest apps/timeoff/ -v
  # Expected: all PASS

  git add backend/apps/timeoff/
  git commit -m "feat(leave): add leave encashment API endpoints for employees and org admin"
  ```

---

## Verification

```bash
cd backend
# Run all timeoff tests
pytest apps/timeoff/tests/ -v --tb=short

# Check coverage on timeoff services
pytest apps/timeoff/tests/ --cov=apps/timeoff/services --cov-report=term-missing
# Expected: >80% coverage

# Run regression check on full test suite
pytest --tb=short -q
# Expected: all tests pass
```
