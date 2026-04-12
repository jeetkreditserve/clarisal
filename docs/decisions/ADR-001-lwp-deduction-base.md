# ADR-001: LWP Deduction Base

**Status**: Accepted
**Date**: 2026-04-11

## Context
When an employee has unpaid leave, LWP deduction can be calculated on either gross pay or basic salary.
Clarisal currently uses gross pay as the deduction base.

## Decision
Retain gross pay as the default LWP deduction base.

## Consequences
- No code change is required in this slice.
- A future organisation-level setting can expose basic-salary-based deduction if needed.
- Payroll configuration documentation should describe the current default explicitly.
