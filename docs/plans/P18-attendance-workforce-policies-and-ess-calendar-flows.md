# P18 — Attendance Workforce Policies & ESS Calendar Flows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the attendance and leave policy gaps still called out by the audit: overtime pay rate configuration, comp-off/TOIL, WFH tracking, shift rotation, annual leave lapse automation, dedicated LWP handling, and employee attendance/leave calendar views.

**Architecture:** Keep daily attendance computation in `attendance`, leave balances in `timeoff`, and pay-impact calculations in `payroll`. Introduce clear domain models for comp-off, WFH, and shift rotations instead of overloading existing punch or leave entities.

**Tech Stack:** Django 4.2 · DRF · Celery · React 19 · TypeScript · pytest · Vitest · Playwright

---

## Audit Findings Addressed

- Overtime pay rate missing
- Comp-off / TOIL missing
- Shift rotation patterns missing
- WFH tracking missing
- Annual leave lapse not scheduled
- LWP dedicated handling incomplete
- Visual attendance calendar missing
- Leave calendar / withdrawal flow missing

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/attendance/models.py` | Modify | Add WFH and shift-rotation policy entities |
| `backend/apps/attendance/services.py` | Modify | Rotation, WFH, calendar, and overtime policy orchestration |
| `backend/apps/attendance/tasks.py` | Create | Rotation and daily calendar jobs if needed |
| `backend/apps/attendance/serializers.py` | Modify | New API payloads |
| `backend/apps/attendance/views.py` | Modify | Admin/self-service endpoints |
| `backend/apps/timeoff/models.py` | Modify | Add comp-off accrual/claim and lapse scheduling support |
| `backend/apps/timeoff/services.py` | Modify | Comp-off accruals, lapse jobs, LWP integration |
| `backend/apps/timeoff/tasks.py` | Create | Leave lapse and accrual jobs |
| `backend/apps/payroll/services.py` | Modify | Consume OT pay and LWP outputs |
| `backend/apps/attendance/tests/test_services.py` | Create/Modify | Workforce policy tests |
| `backend/apps/timeoff/tests/test_services.py` | Modify | Comp-off and lapse tests |
| `frontend/src/pages/employee/AttendancePage.tsx` | Modify | Calendar and WFH status UI |
| `frontend/src/pages/employee/LeavePage.tsx` | Modify | Leave calendar and withdrawal UX |
| `frontend/src/components/ui/MonthCalendar.tsx` | Modify | Attendance/leave visual states |

---

## Task 1: Add Overtime Pay Configuration

- [x] Add overtime pay-rate configuration to attendance policy or shift policy, including threshold and multiplier rules.
- [x] Persist overtime payout inputs separately from raw overtime minutes so payroll can consume approved, policy-compliant values.
- [x] Update payroll integration to create OT earning lines only from approved attendance outputs.

## Task 2: Implement Comp-Off / TOIL

- [x] Add comp-off accrual models linked to overtime or approved special-duty events.
- [x] Add expiry, approval, and redemption rules so comp-off behaves differently from generic leave types.
- [x] Integrate comp-off consumption into leave balance checks and employee-facing leave calendars.

## Task 3: Add WFH Tracking

- [x] Add WFH request or designation entities with approval and status tracking.
- [x] Reflect WFH in attendance day summaries and employee calendars without pretending a WFH day is a physical punch day.
- [x] Expose WFH counts and statuses to org and employee views.

## Task 4: Add Shift Rotation Patterns

- [x] Add rotation templates, assignment rules, and scheduler logic rather than forcing manual shift assignment churn.
- [x] Support common patterns such as weekly rotation, cyclic rotation, and rostered team rotation.
- [x] Recalculate attendance expectations against the effective rotated shift for each day.

## Task 5: Automate Annual Leave Lapse and LWP Handling

- [x] Create explicit cycle-end tasks to lapse leave where carry-forward is disabled.
- [x] Add a dedicated LWP representation instead of relying only on downstream payroll proration.
- [x] Ensure leave, attendance, and payroll all agree on the same LWP semantics.

## Task 6: Add Employee Calendar UX

- [x] Upgrade `frontend/src/components/ui/MonthCalendar.tsx` and employee attendance/leave pages to show day-level states such as Present, Absent, Leave, Holiday, WFH, Comp-Off, and Incomplete.
- [x] Add leave-calendar withdrawal actions where policy allows it.
- [x] Add OD and comp-off history visibility instead of form-only flows.

## Task 7: Cleanup and Full Coverage

- [x] Remove stale attendance assumptions that every policy is fixed-shift and office-presence only.
- [x] Fully cover new attendance/timeoff services, tasks, and calendar UI behavior.
- [ ] Run at least one E2E journey covering attendance punch, WFH/leave visibility, and comp-off redemption.
