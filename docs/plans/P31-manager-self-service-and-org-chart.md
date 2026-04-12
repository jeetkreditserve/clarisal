# P31 — Manager Self-Service (MSS) & Interactive Org Chart

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a dedicated Manager Self-Service layer that gives managers a "My Team" view with direct-report leave balances, attendance deviations, and approval queues filtered to their team. Replace the CSS-only indented org chart with a D3-based interactive graphical chart with zoom, pan, and search.

**Architecture:** MSS is a new frontend layer built on existing backend APIs — no new models needed. The `reporting_to` FK on `Employee` already establishes the team hierarchy. New API endpoints are needed for manager-scoped aggregates (team leave summary, attendance deviations). The D3 org chart is a frontend-only component change — the recursive `OrgChartBranch` backend API is unchanged.

**Tech Stack:** Django 4.2 · DRF · PostgreSQL · React 19 · TypeScript · D3.js · Radix UI · TanStack Query · pytest · Vitest

---

## Audit Findings Addressed

- CSS-only indented org chart unusable for 50+ employees — no graphical nodes, zoom, pan, or search (Gap #15 — Medium)
- No dedicated manager/MSS layer — managers have no "My Team" view with filtered leave, attendance, and approvals (Gap #28 — Medium)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/apps/employees/views.py` | Modify | Add `MyTeamView` — manager-scoped employee list |
| `backend/apps/employees/serializers.py` | Modify | `TeamMemberSummarySerializer` with leave + attendance aggregates |
| `backend/apps/employees/urls.py` | Modify | Register `/api/v1/self/my-team/` routes |
| `backend/apps/timeoff/views.py` | Modify | Add `MyTeamLeaveView` — team leave balances for manager |
| `backend/apps/attendance/views.py` | Modify | Add `MyTeamAttendanceView` — team attendance deviations |
| `backend/apps/approvals/views.py` | Modify | Add manager filter to approval list endpoint |
| `backend/apps/employees/tests/test_views.py` | Modify | MSS endpoint tests |
| `frontend/src/pages/employee/MyTeamPage.tsx` | Create | Manager home page with team cards |
| `frontend/src/pages/employee/MyTeamAttendancePage.tsx` | Create | Team attendance deviation table |
| `frontend/src/pages/org/OrgChartPage.tsx` | Modify | Replace CSS tree with D3 force-directed chart |
| `frontend/src/components/OrgChartD3.tsx` | Create | D3 graphical org chart component |
| `frontend/src/lib/api/employees.ts` | Modify | Add team API calls |
| `frontend/src/routes/index.tsx` | Modify | Register `/employee/my-team` route |

---

## Task 1: Backend — Manager-Scoped API Endpoints

### My Team Endpoint

- [x] In `employees/views.py`, add `MyTeamView`:

```python
class MyTeamView(APIView):
    permission_classes = [IsAuthenticated, IsWorkforceUser]

    def get(self, request):
        employee = get_active_employee(request)
        direct_reports = Employee.objects.filter(
            reporting_to=employee,
            organisation=employee.organisation,
            status=EmployeeStatus.ACTIVE,
        ).select_related('department', 'designation')
        serializer = TeamMemberSummarySerializer(
            direct_reports, many=True, context={'request': request}
        )
        return Response(serializer.data)
```

- [x] Register at `GET /api/v1/me/my-team/` (the existing self-service namespace in this app is `/me/`, not `/self/`).
- [x] Add `TeamMemberSummarySerializer` in `employees/serializers.py`:

```python
class TeamMemberSummarySerializer(serializers.ModelSerializer):
    pending_leave_requests = serializers.SerializerMethodField()
    attendance_deviations_this_month = serializers.SerializerMethodField()
    leave_balance_summary = serializers.SerializerMethodField()

    def get_pending_leave_requests(self, employee):
        return LeaveRequest.objects.filter(
            employee=employee, status=LeaveRequestStatus.PENDING
        ).count()

    def get_attendance_deviations_this_month(self, employee):
        # Count of days with unresolved punch deviations in current month
        today = date.today()
        return AttendancePunch.objects.filter(
            employee=employee,
            punch_date__year=today.year,
            punch_date__month=today.month,
            is_regularised=False,
            deviation_flag__isnull=False,
        ).values('punch_date').distinct().count()

    def get_leave_balance_summary(self, employee):
        # Return total available leave days (PL + CL)
        ...
```

### Team Leave View

- [x] In `timeoff/views.py`, add `MyTeamLeaveView` returning team leave requests for the current week/month:

```python
GET /api/v1/me/my-team/leave/
?status=PENDING&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
```

- [x] Scope to direct reports only (not sub-hierarchy unless `include_indirect=true` query param).
- [x] Return employee name, leave type, from_date, to_date, status, leave_request_id.

### Team Attendance View

- [x] In `attendance/views.py`, add `MyTeamAttendanceView`:

```python
GET /api/v1/me/my-team/attendance/?date=YYYY-MM-DD
```

- [x] Return per-employee: present/absent/on-leave/work-from-home status for the requested date.
- [x] Default to today if no date param.

### Manager-Filtered Approvals

- [x] In `approvals/views.py`, add `?scope=my_team` query parameter to the existing approval list endpoint:
  - When `scope=my_team`, filter pending approvals to only those where the requestor is a direct report of the requesting manager.
  - When scope is absent, return all org-wide pending approvals (for HR admins as before).

## Task 2: Backend — DB Indexes for Manager Queries

- [x] Add indexes for the new manager queries (these were noted as missing in the v4 audit):

```python
# In Employee model Meta:
# Implemented as composite indexes to avoid duplicating Django's implicit FK indexes.
models.Index(fields=['organisation', 'reporting_to', 'status'], name='emp_org_mgr_status_idx'),
models.Index(fields=['organisation', 'department', 'status'], name='emp_org_dept_status_idx'),
```

- [x] Create a migration for these indexes.
- [x] These are additive — no data changes required.

## Task 3: Frontend — My Team Page

- [x] Create `frontend/src/pages/employee/MyTeamPage.tsx`:

```
Layout:
┌─────────────────────────────────────────────────────────┐
│ My Team (5 direct reports)                              │
├─────────────────────────────────────────────────────────┤
│ [Pending Approvals badge: 3]  [View All Approvals →]    │
├─────────────────────────────────────────────────────────┤
│ Team cards (grid):                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Priya Sharma │  │ Rahul Mehta  │  │ Ananya Gupta │ │
│  │ Sr Engineer  │  │ Designer     │  │ Analyst      │ │
│  │ ● Present    │  │ ⏱ On Leave  │  │ ● Present   │ │
│  │ 0 pending    │  │ 1 pending    │  │ 0 pending    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Today's leave: Rahul Mehta (Annual Leave)               │
│ Pending requests: [3 items — quick approve/reject]      │
└─────────────────────────────────────────────────────────┘
```

- [x] Fetch team data from `GET /api/v1/me/my-team/`.
- [x] Fetch today's leave from `GET /api/v1/me/my-team/leave/?from_date=today&to_date=today`.
- [x] Fetch pending approvals from `GET /api/v1/me/approvals/inbox/?scope=my_team`.
- [x] Show "You have no direct reports" empty state if the team is empty.
- [x] Register route at `/me/my-team`.
- [x] Add "My Team" nav item to the employee sidebar (only visible if the employee has at least one direct report).

## Task 4: Frontend — Team Attendance Page

- [x] Create `frontend/src/pages/employee/MyTeamAttendancePage.tsx`:
  - Calendar date selector (defaults to today)
  - Table: employee name, status (Present/Absent/On Leave/WFH), punch-in time, punch-out time, deviation flag
  - Filter by status (show only absent/deviations)
  - Export as CSV button
- [x] Register at `/me/my-team/attendance`.

## Task 5: Frontend — D3 Interactive Org Chart

> **Finding (Gap #15 — Medium):** The current `OrgChartPage` uses a recursive CSS component (`border-l` + `ml-4` indentation). For orgs with 50+ employees this becomes an unusable vertical list.

- [x] Install D3: `npm install d3 @types/d3` in `frontend/`.
- [x] Create `frontend/src/components/OrgChartD3.tsx`:

```
Features:
- D3 tree layout (d3.tree()) — top-to-bottom hierarchy
- Nodes: rounded rect with avatar initials, name, designation, department badge
- Edges: smooth bezier curves between parent → child
- Zoom: d3.zoom() — scroll to zoom, drag to pan
- Click node: show employee mini-card (leave balance, contact, join date)
- Search bar: highlight matching nodes, dim non-matches
- Toggle: hide inactive employees (default on)
- Collapse/expand subtree on node click (hold Ctrl/Cmd)
- Legend: department colours
```

- [x] The component receives the existing org-chart tree payload from `/api/v1/org/org-chart/` and builds the D3 hierarchy from that structure.
- [x] Keep the existing CSS tree as a `<details>` accessible fallback below the D3 chart (for screen readers and low-powered devices).
- [x] In `OrgChartPage.tsx`, replace the `OrgChartBranch` recursive render with `<OrgChartD3 data={orgChartData} />`.
- [x] Add Vitest tests for `OrgChartD3`:
  - Renders without crash given a flat employee list
  - Search filters nodes correctly
  - Empty org returns empty state

## Task 6: Tests

- [x] Add backend tests in `employees/tests/test_views.py`:
  - `GET /api/v1/self/my-team/` as manager with 3 direct reports → returns 3 employees with aggregated fields
  - `GET /api/v1/self/my-team/` as non-manager employee (no direct reports) → returns empty list
  - `GET /api/v1/self/my-team/leave/` → returns only leave requests for direct reports
  - Manager cannot see leave requests of employees outside their direct-report tree
- [x] Add Vitest smoke tests for `MyTeamPage` and `MyTeamAttendancePage`.
