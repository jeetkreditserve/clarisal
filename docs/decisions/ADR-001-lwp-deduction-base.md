# ADR-001: LWP / Loss-of-Pay Deduction Calculation Base

**Status**: Accepted
**Date**: 2026-04-11 (enriched 2026-04-12)

## Context

When an employee has Leave Without Pay (LWP) or Loss of Pay (LOP) days in a payroll
period, two decisions must be made:

1. **What is the deduction base?** — Gross pay vs Basic salary
2. **What is the day-count denominator?** — Calendar days vs Working days

## Decisions

### Decision 1: Deduction Base = Gross Pay

LWP deduction is calculated on the employee's **gross pay**, not basic salary.

**Rationale**: Most Indian companies use gross pay as the base. Basic-only deduction
would penalise employees differently based on how their CTC is structured (high-basic
vs allowance-heavy packages). A future org-level setting can expose basic-salary deduction.

### Decision 2: Day-Count Denominator = Calendar Days

The per-day rate uses **actual calendar days in the payroll month** as the denominator.

Implementation (`backend/apps/payroll/services.py`, line 1426):

```python
total_days_in_period = period_end.day   # = calendar days in payroll month
daily_gross = gross_pay / Decimal(total_days_in_period)
lop_deduction = daily_gross * lop_days
lop_deduction = min(lop_deduction, gross_pay)  # cap at gross to prevent negative net
```

**Rationale**: Industry standard for Indian payroll (Keka, GreytHR, Zoho Payroll all
use calendar days). Objective, easy to reconcile, not challenged by labour authorities.

## Consequences

- Per-day rate is slightly higher in shorter months (Feb) than longer months (Mar/May).
  This is expected and accepted.
- LWP deduction is always capped at gross pay.
- Changing either decision later requires migrating historical `PayrollRunItem.lop_deduction`
  snapshots and clear employee communication.

## Alternatives Rejected

| Alternative | Reason for rejection |
|------------|---------------------|
| Deduction base = Basic salary | Penalises allowance-heavy structures unequally |
| Day denominator = Working days | Requires per-org shift calendar; more complex; non-standard |
| Day denominator = Fixed 30 | Incorrect in 28/29/31-day months |
