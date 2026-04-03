# P08 — Reports & Analytics

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `reports` Django app with six report types (Payroll Register, Headcount, Attrition, Leave Utilization, Attendance Summary, Tax Summary), Excel export via `openpyxl`, and a React `ReportsPage` with download buttons.

**Architecture:** A single `ReportsPage` view dispatches to report-specific service classes via a `type` parameter. Each report generates JSON or streams a file download. `openpyxl` is used for Excel. CSV uses Python's `csv` module. No new Celery tasks (reports are fast enough to run synchronously for typical org sizes <5000 employees; async can be added in P04 if needed).

**Tech Stack:** Django 4.2 · DRF · openpyxl · React 19 · TanStack Query v5

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/apps/reports/__init__.py` | Create | App package |
| `backend/apps/reports/apps.py` | Create | Django app config |
| `backend/apps/reports/base.py` | Create | `BaseReport` abstract class |
| `backend/apps/reports/payroll_register.py` | Create | Payroll register report |
| `backend/apps/reports/headcount.py` | Create | Headcount/attrition report |
| `backend/apps/reports/leave_utilization.py` | Create | Leave utilization report |
| `backend/apps/reports/attendance_summary.py` | Create | Attendance summary report |
| `backend/apps/reports/tax_summary.py` | Create | Tax summary (PT + TDS) report |
| `backend/apps/reports/views.py` | Create | `OrgReportView` dispatcher |
| `backend/apps/reports/urls.py` | Create | URL patterns |
| `backend/apps/reports/tests/test_reports.py` | Create | Report unit tests |
| `backend/requirements.txt` | Modify | Add `openpyxl` |
| `backend/clarisal/settings/base.py` | Modify | Add `apps.reports` to INSTALLED_APPS |
| `backend/clarisal/urls.py` | Modify | Register reports URLs |
| `frontend/src/lib/api/org-admin.ts` | Modify | Add report download functions |
| `frontend/src/pages/org/ReportsPage.tsx` | Create | Reports UI |

---

## Task 1 — `reports` App and Base Class

**Files:**
- Create: `backend/apps/reports/__init__.py`
- Create: `backend/apps/reports/apps.py`
- Create: `backend/apps/reports/base.py`

- [ ] **Step 1: Create app**

```bash
cd backend && python manage.py startapp reports apps/reports
```

- [ ] **Step 2: Update `apps.py`**

```python
# backend/apps/reports/apps.py
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reports'
    label = 'reports'
```

- [ ] **Step 3: Add to `INSTALLED_APPS` and install `openpyxl`**

Add `'apps.reports'` to `LOCAL_APPS` in `backend/clarisal/settings/base.py`.

Add `openpyxl>=3.1.0` to `backend/requirements.txt`.

```bash
pip install openpyxl
```

- [ ] **Step 4: Create `base.py`**

```python
# backend/apps/reports/base.py
from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from datetime import date
from typing import Any

import openpyxl
from django.http import HttpResponse


class BaseReport(ABC):
    """
    Abstract base for all reports.
    Subclasses implement `generate_rows()` returning a list of dicts.
    Calling `.to_json()`, `.to_csv_response()`, or `.to_excel_response()` produces the output.
    """

    @property
    @abstractmethod
    def title(self) -> str:
        """Human-readable report name."""

    @property
    @abstractmethod
    def columns(self) -> list[str]:
        """Ordered column headers for the report."""

    @abstractmethod
    def generate_rows(self) -> list[dict[str, Any]]:
        """Return a list of row dicts. Keys must match `columns`."""

    def to_json(self) -> dict:
        return {
            'title': self.title,
            'columns': self.columns,
            'rows': self.generate_rows(),
        }

    def to_csv_response(self) -> HttpResponse:
        rows = self.generate_rows()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.title}.csv"'
        writer = csv.DictWriter(response, fieldnames=self.columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
        return response

    def to_excel_response(self) -> HttpResponse:
        rows = self.generate_rows()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = self.title[:31]  # Excel sheet name limit
        # Header row
        ws.append(self.columns)
        for row in rows:
            ws.append([row.get(col, '') for col in self.columns])
        # Auto-size columns
        for col_idx, col_name in enumerate(self.columns, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(
                len(col_name) + 2, 12
            )
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{self.title}.xlsx"'
        return response
```

- [ ] **Step 5: Commit**

```bash
git add backend/apps/reports/ backend/requirements.txt backend/clarisal/settings/base.py
git commit -m "feat(reports): create reports app with BaseReport abstract class + openpyxl"
```

---

## Task 2 — Payroll Register Report

**Files:**
- Create: `backend/apps/reports/payroll_register.py`

- [ ] **Step 1: Write the failing test first**

Create `backend/apps/reports/tests/__init__.py` and `backend/apps/reports/tests/test_reports.py`:

```python
# backend/apps/reports/tests/test_reports.py
from decimal import Decimal
from django.test import TestCase
from apps.reports.payroll_register import PayrollRegisterReport
from apps.accounts.tests.factories import OrganisationFactory
from apps.payroll.tests.factories import PayrollRunFactory, PayrollRunItemFactory


class TestPayrollRegisterReport(TestCase):
    def setUp(self):
        self.org = OrganisationFactory()
        self.pay_run = PayrollRunFactory(organisation=self.org, month=4, year=2024)

    def test_report_includes_all_employees_in_run(self):
        PayrollRunItemFactory(pay_run=self.pay_run, gross_pay=Decimal('50000'), net_pay=Decimal('43000'))
        PayrollRunItemFactory(pay_run=self.pay_run, gross_pay=Decimal('60000'), net_pay=Decimal('52000'))
        report = PayrollRegisterReport(organisation=self.org, pay_run_id=str(self.pay_run.id))
        data = report.to_json()
        self.assertEqual(len(data['rows']), 2)

    def test_report_row_contains_required_fields(self):
        PayrollRunItemFactory(pay_run=self.pay_run, gross_pay=Decimal('50000'), net_pay=Decimal('43000'))
        report = PayrollRegisterReport(organisation=self.org, pay_run_id=str(self.pay_run.id))
        row = report.to_json()['rows'][0]
        for field in ['Employee Name', 'Employee Code', 'Department', 'Gross Pay', 'Net Pay']:
            self.assertIn(field, row)
```

- [ ] **Step 2: Implement `payroll_register.py`**

```python
# backend/apps/reports/payroll_register.py
from __future__ import annotations
from .base import BaseReport
from apps.payroll.models import PayrollRun, PayrollRunItem


class PayrollRegisterReport(BaseReport):
    title = 'Payroll Register'
    columns = [
        'Employee Code', 'Employee Name', 'Department', 'Location',
        'Gross Pay', 'Total Deductions', 'Net Pay',
        'PF Employee', 'ESI Employee', 'Professional Tax', 'TDS',
    ]

    def __init__(self, organisation, pay_run_id: str):
        self.organisation = organisation
        self.pay_run_id = pay_run_id

    def generate_rows(self):
        items = (
            PayrollRunItem.objects
            .filter(pay_run__id=self.pay_run_id, pay_run__organisation=self.organisation)
            .select_related('employee__user', 'employee__department', 'employee__location')
        )
        rows = []
        for item in items:
            snap = item.snapshot or {}
            rows.append({
                'Employee Code': item.employee.employee_code or '',
                'Employee Name': item.employee.user.get_full_name(),
                'Department': item.employee.department.name if item.employee.department else '',
                'Location': item.employee.location.name if item.employee.location else '',
                'Gross Pay': str(item.gross_pay or 0),
                'Total Deductions': str(item.total_deductions or 0),
                'Net Pay': str(item.net_pay or 0),
                'PF Employee': str(snap.get('pf_employee', 0)),
                'ESI Employee': str(snap.get('esi_employee', 0)),
                'Professional Tax': str(snap.get('professional_tax', 0)),
                'TDS': str(snap.get('tds_monthly', 0)),
            })
        return rows
```

- [ ] **Step 3: Run test**

```bash
cd backend && python -m pytest apps/reports/tests/test_reports.py::TestPayrollRegisterReport -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/reports/payroll_register.py backend/apps/reports/tests/
git commit -m "feat(reports): PayrollRegisterReport with all statutory deduction columns"
```

---

## Task 3 — Headcount & Attrition Report

**Files:**
- Create: `backend/apps/reports/headcount.py`

- [ ] **Step 1: Implement `headcount.py`**

```python
# backend/apps/reports/headcount.py
from __future__ import annotations
from datetime import date
from .base import BaseReport
from apps.employees.models import Employee, EmployeeStatus


class HeadcountReport(BaseReport):
    title = 'Headcount by Department'
    columns = ['Department', 'Location', 'Active Employees', 'On Probation']

    def __init__(self, organisation):
        self.organisation = organisation

    def generate_rows(self):
        from django.db.models import Count, Q
        from apps.departments.models import Department
        dept_qs = Department.objects.filter(organisation=self.organisation)
        rows = []
        for dept in dept_qs:
            active = Employee.objects.filter(
                organisation=self.organisation,
                department=dept,
                status=EmployeeStatus.ACTIVE,
            ).count()
            on_probation = Employee.objects.filter(
                organisation=self.organisation,
                department=dept,
                status=EmployeeStatus.ACTIVE,
                probation_end_date__gt=date.today(),
            ).count()
            rows.append({
                'Department': dept.name,
                'Location': '',
                'Active Employees': active,
                'On Probation': on_probation,
            })
        return rows


class AttritionReport(BaseReport):
    title = 'Attrition Report'
    columns = ['Employee Name', 'Department', 'Last Working Day', 'Exit Type', 'Reason']

    def __init__(self, organisation, start_date: date, end_date: date):
        self.organisation = organisation
        self.start_date = start_date
        self.end_date = end_date

    def generate_rows(self):
        exited = Employee.objects.filter(
            organisation=self.organisation,
            status__in=[EmployeeStatus.RESIGNED, EmployeeStatus.TERMINATED, EmployeeStatus.RETIRED],
        ).select_related('user', 'department')
        rows = []
        for emp in exited:
            rows.append({
                'Employee Name': emp.user.get_full_name(),
                'Department': emp.department.name if emp.department else '',
                'Last Working Day': str(emp.date_of_exit or ''),
                'Exit Type': emp.status,
                'Reason': '',
            })
        return rows
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/reports/headcount.py
git commit -m "feat(reports): HeadcountReport and AttritionReport"
```

---

## Task 4 — Leave Utilization Report

**Files:**
- Create: `backend/apps/reports/leave_utilization.py`

- [ ] **Step 1: Implement**

```python
# backend/apps/reports/leave_utilization.py
from __future__ import annotations
from .base import BaseReport
from apps.timeoff.models import LeaveType
from apps.timeoff.repositories import get_leave_balance_snapshot
from apps.employees.models import Employee, EmployeeStatus


class LeaveUtilizationReport(BaseReport):
    title = 'Leave Utilization'
    columns = ['Employee Name', 'Leave Type', 'Accrued', 'Used', 'Pending', 'Available']

    def __init__(self, organisation):
        self.organisation = organisation

    def generate_rows(self):
        employees = Employee.objects.filter(
            organisation=self.organisation,
            status=EmployeeStatus.ACTIVE,
        ).select_related('user')
        leave_types = LeaveType.objects.filter(organisation=self.organisation, is_active=True)
        rows = []
        for emp in employees:
            for lt in leave_types:
                snap = get_leave_balance_snapshot(emp.id, lt.id)
                rows.append({
                    'Employee Name': emp.user.get_full_name(),
                    'Leave Type': lt.name,
                    'Accrued': str(snap['accrued']),
                    'Used': str(snap['used']),
                    'Pending': str(snap['pending']),
                    'Available': str(snap['available']),
                })
        return rows
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/reports/leave_utilization.py
git commit -m "feat(reports): LeaveUtilizationReport using repository layer"
```

---

## Task 5 — Attendance Summary & Tax Summary Reports

**Files:**
- Create: `backend/apps/reports/attendance_summary.py`
- Create: `backend/apps/reports/tax_summary.py`

- [ ] **Step 1: Create `attendance_summary.py`**

```python
# backend/apps/reports/attendance_summary.py
from __future__ import annotations
from datetime import date
from .base import BaseReport
from apps.attendance.models import AttendanceDay, AttendanceDayStatus
from apps.employees.models import Employee, EmployeeStatus
from django.db.models import Count, Q


class AttendanceSummaryReport(BaseReport):
    title = 'Attendance Summary'
    columns = ['Employee Name', 'Employee Code', 'Department', 'Present Days',
               'Half Days', 'Absent Days', 'On Leave Days', 'Late Marks']

    def __init__(self, organisation, month: int, year: int):
        self.organisation = organisation
        self.month = month
        self.year = year

    def generate_rows(self):
        employees = Employee.objects.filter(
            organisation=self.organisation,
            status=EmployeeStatus.ACTIVE,
        ).select_related('user', 'department')
        rows = []
        for emp in employees:
            days_qs = AttendanceDay.objects.filter(
                employee=emp,
                work_date__month=self.month,
                work_date__year=self.year,
            )
            present = days_qs.filter(status=AttendanceDayStatus.PRESENT).count()
            half_day = days_qs.filter(status=AttendanceDayStatus.HALF_DAY).count()
            absent = days_qs.filter(status=AttendanceDayStatus.ABSENT).count()
            on_leave = days_qs.filter(status=AttendanceDayStatus.ON_LEAVE).count()
            late = days_qs.filter(is_late=True).count()
            rows.append({
                'Employee Name': emp.user.get_full_name(),
                'Employee Code': emp.employee_code or '',
                'Department': emp.department.name if emp.department else '',
                'Present Days': present,
                'Half Days': half_day,
                'Absent Days': absent,
                'On Leave Days': on_leave,
                'Late Marks': late,
            })
        return rows
```

- [ ] **Step 2: Create `tax_summary.py`**

```python
# backend/apps/reports/tax_summary.py
from __future__ import annotations
from .base import BaseReport
from apps.payroll.models import PayrollRunItem, PayrollRun, PayrollRunStatus
from apps.employees.models import Employee, EmployeeStatus


class TaxSummaryReport(BaseReport):
    title = 'Tax Summary'
    columns = ['Employee Name', 'Employee Code', 'Month', 'Year',
               'Professional Tax', 'TDS Monthly', 'PF Employee', 'PF Employer', 'ESI Employee', 'ESI Employer']

    def __init__(self, organisation, fiscal_year: str):
        """fiscal_year e.g. '2024-25'"""
        self.organisation = organisation
        self.fiscal_year = fiscal_year

    def _get_fy_months(self):
        start_year = int(self.fiscal_year.split('-')[0])
        # FY: April (start_year) to March (start_year+1)
        months = [(m, start_year) for m in range(4, 13)] + [(m, start_year + 1) for m in range(1, 4)]
        return months

    def generate_rows(self):
        rows = []
        for month, year in self._get_fy_months():
            items = (
                PayrollRunItem.objects
                .filter(
                    pay_run__organisation=self.organisation,
                    pay_run__month=month,
                    pay_run__year=year,
                    pay_run__status=PayrollRunStatus.FINALIZED,
                )
                .select_related('employee__user')
            )
            for item in items:
                snap = item.snapshot or {}
                rows.append({
                    'Employee Name': item.employee.user.get_full_name(),
                    'Employee Code': item.employee.employee_code or '',
                    'Month': month,
                    'Year': year,
                    'Professional Tax': str(snap.get('professional_tax', 0)),
                    'TDS Monthly': str(snap.get('tds_monthly', 0)),
                    'PF Employee': str(snap.get('pf_employee', 0)),
                    'PF Employer': str(snap.get('pf_employer', 0)),
                    'ESI Employee': str(snap.get('esi_employee', 0)),
                    'ESI Employer': str(snap.get('esi_employer', 0)),
                })
        return rows
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/reports/attendance_summary.py backend/apps/reports/tax_summary.py
git commit -m "feat(reports): AttendanceSummaryReport and TaxSummaryReport"
```

---

## Task 6 — Reports API View

**Files:**
- Create: `backend/apps/reports/views.py`
- Create: `backend/apps/reports/urls.py`
- Modify: `backend/clarisal/urls.py`

- [ ] **Step 1: Create `views.py`**

```python
# backend/apps/reports/views.py
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.accounts.permissions import IsOrgAdmin, BelongsToActiveOrg
from apps.accounts.workspaces import get_active_admin_organisation

from .payroll_register import PayrollRegisterReport
from .headcount import HeadcountReport, AttritionReport
from .leave_utilization import LeaveUtilizationReport
from .attendance_summary import AttendanceSummaryReport
from .tax_summary import TaxSummaryReport

REPORT_REGISTRY = {
    'payroll-register': PayrollRegisterReport,
    'headcount': HeadcountReport,
    'attrition': AttritionReport,
    'leave-utilization': LeaveUtilizationReport,
    'attendance-summary': AttendanceSummaryReport,
    'tax-summary': TaxSummaryReport,
}


class OrgReportView(APIView):
    """
    GET /api/org/reports/{type}/
    Query params:
      - format: json (default) | csv | xlsx
      - pay_run_id: required for payroll-register
      - month, year: required for attendance-summary
      - fiscal_year: required for tax-summary
    """
    permission_classes = [IsOrgAdmin, BelongsToActiveOrg]

    def get(self, request, report_type: str):
        organisation = get_active_admin_organisation(request, request.user)
        if organisation is None:
            return Response({'error': 'No active org workspace.'}, status=status.HTTP_400_BAD_REQUEST)

        if report_type not in REPORT_REGISTRY:
            return Response(
                {'error': f'Unknown report type. Available: {list(REPORT_REGISTRY.keys())}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        report_cls = REPORT_REGISTRY[report_type]
        fmt = request.query_params.get('format', 'json')

        # Build kwargs based on report type
        kwargs = {'organisation': organisation}
        if report_type == 'payroll-register':
            pay_run_id = request.query_params.get('pay_run_id')
            if not pay_run_id:
                return Response({'error': 'pay_run_id is required for payroll-register'}, status=400)
            kwargs['pay_run_id'] = pay_run_id
        elif report_type in ('attendance-summary',):
            kwargs['month'] = int(request.query_params.get('month', 1))
            kwargs['year'] = int(request.query_params.get('year', 2024))
        elif report_type == 'tax-summary':
            kwargs['fiscal_year'] = request.query_params.get('fiscal_year', '2024-25')

        report = report_cls(**kwargs)

        if fmt == 'csv':
            return report.to_csv_response()
        elif fmt == 'xlsx':
            return report.to_excel_response()
        else:
            return Response(report.to_json())
```

- [ ] **Step 2: Create `urls.py`**

```python
# backend/apps/reports/urls.py
from django.urls import path
from .views import OrgReportView

urlpatterns = [
    path('reports/<str:report_type>/', OrgReportView.as_view()),
]
```

- [ ] **Step 3: Register in `clarisal/urls.py`**

Add `path('org/', include('apps.reports.urls'))` to both the legacy and versioned URL includes.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/reports/views.py backend/apps/reports/urls.py backend/clarisal/urls.py
git commit -m "feat(reports): OrgReportView dispatcher with JSON/CSV/Excel format support"
```

---

## Task 7 — Frontend ReportsPage

**Files:**
- Create: `frontend/src/pages/org/ReportsPage.tsx`
- Modify: `frontend/src/lib/api/org-admin.ts`
- Modify: `frontend/src/components/layouts/OrgLayout.tsx` (add Reports to nav)
- Modify: `frontend/src/routes/index.tsx` (add /org/reports route)

- [ ] **Step 1: Add API functions**

In `frontend/src/lib/api/org-admin.ts`, add:

```typescript
export async function downloadReport(
  reportType: string,
  params: Record<string, string>,
  format: 'json' | 'csv' | 'xlsx' = 'xlsx',
): Promise<Blob | object> {
  const queryString = new URLSearchParams({ ...params, format }).toString();
  const response = await apiClient.get(`/api/org/reports/${reportType}/?${queryString}`, {
    responseType: format === 'json' ? 'json' : 'blob',
  });
  return response.data;
}
```

- [ ] **Step 2: Create `ReportsPage.tsx`**

```tsx
// frontend/src/pages/org/ReportsPage.tsx
import * as React from 'react';
import { AppButton } from '@/components/ui/AppButton';
import { AppSelect } from '@/components/ui/AppSelect';
import toast from 'react-hot-toast';
import { downloadReport } from '@/lib/api/org-admin';

const REPORT_TYPES = [
  { value: 'payroll-register', label: 'Payroll Register' },
  { value: 'headcount', label: 'Headcount by Department' },
  { value: 'attrition', label: 'Attrition Report' },
  { value: 'leave-utilization', label: 'Leave Utilization' },
  { value: 'attendance-summary', label: 'Attendance Summary' },
  { value: 'tax-summary', label: 'Tax Summary (PT + TDS)' },
];

export default function ReportsPage() {
  const [reportType, setReportType] = React.useState('headcount');
  const [format, setFormat] = React.useState<'xlsx' | 'csv'>('xlsx');
  const [month, setMonth] = React.useState(String(new Date().getMonth() + 1));
  const [year, setYear] = React.useState(String(new Date().getFullYear()));
  const [fiscalYear, setFiscalYear] = React.useState('2024-25');
  const [payRunId, setPayRunId] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);

  async function handleDownload() {
    setIsLoading(true);
    const toastId = toast.loading('Generating report…');
    try {
      const params: Record<string, string> = {};
      if (reportType === 'payroll-register') params.pay_run_id = payRunId;
      if (reportType === 'attendance-summary') { params.month = month; params.year = year; }
      if (reportType === 'tax-summary') params.fiscal_year = fiscalYear;

      const blob = await downloadReport(reportType, params, format) as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType}-report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Report downloaded', { id: toastId });
    } catch (err) {
      toast.error('Failed to generate report', { id: toastId });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold mb-6">Reports</h1>

      <div className="bg-white rounded-lg border p-6 space-y-4">
        <div>
          <label htmlFor="report-type" className="block text-sm font-medium mb-1">Report Type</label>
          <select
            id="report-type"
            className="w-full border rounded-md px-3 py-2 text-sm"
            value={reportType}
            onChange={e => setReportType(e.target.value)}
          >
            {REPORT_TYPES.map(rt => (
              <option key={rt.value} value={rt.value}>{rt.label}</option>
            ))}
          </select>
        </div>

        {reportType === 'attendance-summary' && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="att-month" className="block text-sm font-medium mb-1">Month</label>
              <input id="att-month" type="number" min={1} max={12} className="w-full border rounded-md px-3 py-2 text-sm"
                value={month} onChange={e => setMonth(e.target.value)} />
            </div>
            <div>
              <label htmlFor="att-year" className="block text-sm font-medium mb-1">Year</label>
              <input id="att-year" type="number" min={2020} max={2099} className="w-full border rounded-md px-3 py-2 text-sm"
                value={year} onChange={e => setYear(e.target.value)} />
            </div>
          </div>
        )}

        {reportType === 'tax-summary' && (
          <div>
            <label htmlFor="fy" className="block text-sm font-medium mb-1">Fiscal Year</label>
            <input id="fy" type="text" placeholder="2024-25" className="w-full border rounded-md px-3 py-2 text-sm"
              value={fiscalYear} onChange={e => setFiscalYear(e.target.value)} />
          </div>
        )}

        {reportType === 'payroll-register' && (
          <div>
            <label htmlFor="pay-run-id" className="block text-sm font-medium mb-1">Pay Run ID</label>
            <input id="pay-run-id" type="text" placeholder="UUID of the pay run"
              className="w-full border rounded-md px-3 py-2 text-sm"
              value={payRunId} onChange={e => setPayRunId(e.target.value)} />
          </div>
        )}

        <div>
          <label htmlFor="report-format" className="block text-sm font-medium mb-1">Format</label>
          <select
            id="report-format"
            className="w-full border rounded-md px-3 py-2 text-sm"
            value={format}
            onChange={e => setFormat(e.target.value as 'xlsx' | 'csv')}
          >
            <option value="xlsx">Excel (.xlsx)</option>
            <option value="csv">CSV (.csv)</option>
          </select>
        </div>

        <AppButton onClick={handleDownload} disabled={isLoading} className="w-full">
          {isLoading ? 'Generating…' : 'Download Report'}
        </AppButton>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add route and nav item**

In `frontend/src/routes/index.tsx`:
```tsx
import ReportsPage from '@/pages/org/ReportsPage';
// Inside org routes:
{ path: 'reports', element: <AppErrorBoundary><ReportsPage /></AppErrorBoundary> }
```

In `OrgLayout.tsx` nav groups, add `{ label: 'Reports', href: '/org/reports', icon: ChartBarIcon }` to the Compensation group.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/org/ReportsPage.tsx \
        frontend/src/lib/api/org-admin.ts \
        frontend/src/routes/index.tsx \
        frontend/src/components/layouts/OrgLayout.tsx
git commit -m "feat(reports): ReportsPage with type selector, period params, and download"
```

---

## Verification

```bash
# Backend
cd backend && python -m pytest apps/reports/ -v
# Expected: all pass

# Manual curl test
curl -H "Cookie: ..." "http://localhost:8000/api/org/reports/headcount/?format=xlsx" \
  --output headcount.xlsx
file headcount.xlsx
# Expected: Microsoft Excel
```
