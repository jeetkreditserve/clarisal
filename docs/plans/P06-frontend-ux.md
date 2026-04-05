# P06 — Frontend UX Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all UX audit findings: replace `window.confirm()` with accessible dialogs, add aria-labels to icon buttons, wire payslip download, fix form labels, add collapsible nav groups, consistent error handling, overflow-safe tables, status tone functions, leave balance preview, and loading feedback.

**Architecture:** All changes are frontend-only React/TypeScript. The `ConfirmDialog` component is built on the existing `AppDialog` primitive (Radix UI). Status tone functions extend the existing `lib/status.ts`. No new routes or API endpoints required.

**Tech Stack:** React 19 · TypeScript · Tailwind CSS 4 · Radix UI · TanStack Query v5 · Vitest

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/components/ui/ConfirmDialog.tsx` | Create | Accessible confirm dialog replacing window.confirm |
| `frontend/src/pages/org/PayrollPage.tsx` | Modify | Replace window.confirm, fix form labels, add overflow-x-auto, toast.loading |
| `frontend/src/pages/org/EmployeeDetailPage.tsx` | Modify | Replace window.confirm, add aria-labels |
| `frontend/src/pages/org/LocationsPage.tsx` | Modify | Replace window.confirm, add aria-labels |
| `frontend/src/pages/org/LeavePlanBuilderPage.tsx` | Modify | Convert to 3-step wizard |
| `frontend/src/pages/employee/PayslipsPage.tsx` | Modify | Wire download button |
| `frontend/src/pages/employee/LeavePage.tsx` | Modify | Add real-time balance preview |
| `frontend/src/components/layouts/OrgLayout.tsx` | Modify | Collapsible nav groups |
| `frontend/src/lib/status.ts` | Modify | Add payroll/compensation/attendance tone functions |
| `frontend/src/routes/index.tsx` | Modify | Wrap routes with AppErrorBoundary |
| `frontend/src/components/ui/AppErrorBoundary.tsx` | Create | React error boundary for route errors |
| `frontend/src/components/ui/ConfirmDialog.test.tsx` | Create | Component unit test |

---

## Task 1 — `ConfirmDialog` Component

**Files:**
- Create: `frontend/src/components/ui/ConfirmDialog.tsx`
- Create: `frontend/src/components/ui/ConfirmDialog.test.tsx`

- [x] **Step 1: Write the test**

```tsx
// frontend/src/components/ui/ConfirmDialog.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ConfirmDialog } from './ConfirmDialog';

describe('ConfirmDialog', () => {
  it('renders trigger and dialog content', async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        trigger={<button>Delete</button>}
        title="Delete item?"
        description="This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={onConfirm}
      />
    );
    fireEvent.click(screen.getByText('Delete'));
    expect(screen.getByText('Delete item?')).toBeDefined();
    expect(screen.getByText('This action cannot be undone.')).toBeDefined();
  });

  it('calls onConfirm when confirm button clicked', async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        trigger={<button>Delete</button>}
        title="Confirm?"
        onConfirm={onConfirm}
      />
    );
    fireEvent.click(screen.getByText('Delete'));
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('closes without calling onConfirm when cancel clicked', () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        trigger={<button>Delete</button>}
        title="Confirm?"
        onConfirm={onConfirm}
      />
    );
    fireEvent.click(screen.getByText('Delete'));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
```

- [x] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/components/ui/ConfirmDialog.test.tsx
```

Expected: `FAIL` — module not found.

- [x] **Step 3: Create `ConfirmDialog.tsx`**

```tsx
// frontend/src/components/ui/ConfirmDialog.tsx
import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AppButton } from './AppButton';

interface ConfirmDialogProps {
  trigger: React.ReactNode;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'primary';
  onConfirm: () => void | Promise<void>;
}

export function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  onConfirm,
}: ConfirmDialogProps) {
  const [open, setOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  async function handleConfirm() {
    setLoading(true);
    try {
      await onConfirm();
      setOpen(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl p-6 w-full max-w-md z-50 focus:outline-none"
          aria-describedby={description ? 'confirm-dialog-desc' : undefined}
        >
          <Dialog.Title className="text-lg font-semibold mb-2">{title}</Dialog.Title>
          {description && (
            <Dialog.Description id="confirm-dialog-desc" className="text-sm text-gray-600 mb-4">
              {description}
            </Dialog.Description>
          )}
          <div className="flex justify-end gap-3 mt-6">
            <Dialog.Close asChild>
              <AppButton variant="outline" disabled={loading}>
                {cancelLabel}
              </AppButton>
            </Dialog.Close>
            <AppButton
              variant={variant === 'danger' ? 'destructive' : 'primary'}
              onClick={handleConfirm}
              disabled={loading}
              aria-label={confirmLabel}
            >
              {loading ? 'Processing…' : confirmLabel}
            </AppButton>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

- [x] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/ui/ConfirmDialog.test.tsx
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/ConfirmDialog.tsx frontend/src/components/ui/ConfirmDialog.test.tsx
git commit -m "feat(ui): ConfirmDialog component replacing window.confirm"
```

---

## Task 2 — Replace `window.confirm()` in PayrollPage

**Files:**
- Modify: `frontend/src/pages/org/PayrollPage.tsx`

- [x] **Step 1: Find all `window.confirm` calls**

```bash
grep -n "window.confirm" frontend/src/pages/org/PayrollPage.tsx
```

Note each line number and the action it guards.

- [x] **Step 2: Replace each `window.confirm` call with `ConfirmDialog`**

For each confirm pattern like:
```tsx
// Before:
if (window.confirm('Are you sure you want to finalize this pay run?')) {
  finalizeMutation.mutate(payRun.id);
}
```

Wrap the trigger button with `ConfirmDialog`:
```tsx
// After:
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

<ConfirmDialog
  trigger={
    <AppButton variant="primary">Finalize Pay Run</AppButton>
  }
  title="Finalize Pay Run?"
  description="This will lock the pay run and generate payslips. This action cannot be undone."
  confirmLabel="Finalize"
  onConfirm={() => finalizeMutation.mutate(payRun.id)}
/>
```

Apply the same replacement for all other `window.confirm` calls in the file (delete template, delete tax slab, rerun payroll, etc.).

- [x] **Step 3: Replace `window.confirm` across all other org pages**

```bash
grep -rn "window.confirm" frontend/src/pages/
```

For each occurrence in `EmployeeDetailPage.tsx`, `LocationsPage.tsx`, `DepartmentsPage.tsx`, `ApprovalWorkflowsPage.tsx`, and any other pages found, apply the same ConfirmDialog wrapping pattern.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/
git commit -m "fix(ux): replace all window.confirm() calls with accessible ConfirmDialog"
```

---

## Task 3 — Aria Labels on Icon-Only Buttons

**Files:**
- Modify: multiple page files across `frontend/src/pages/`

- [x] **Step 1: Find all icon-only buttons without aria-label**

```bash
grep -rn "<AppButton\|<button" frontend/src/pages/ | grep -v "aria-label" | grep -i "icon\|<.*Icon\|svg"
```

Also search for icon button patterns:
```bash
grep -rn "IconButton\|icon.*button\|<button.*>\s*<" frontend/src/pages/ --include="*.tsx"
```

- [x] **Step 2: Add `aria-label` to every icon-only button found**

Pattern to apply for each icon button:
```tsx
// Before:
<AppButton variant="ghost" size="icon" onClick={handleEdit}>
  <PencilIcon className="h-4 w-4" />
</AppButton>

// After:
<AppButton variant="ghost" size="icon" onClick={handleEdit} aria-label="Edit employee">
  <PencilIcon className="h-4 w-4" />
</AppButton>
```

Apply descriptive, action-specific labels: "Edit [resource]", "Delete [resource]", "Download payslip", "View details", etc.

- [x] **Step 3: Verify no remaining unlabelled icon buttons**

```bash
grep -rn "size=\"icon\"\|size='icon'" frontend/src/pages/ | grep -v "aria-label"
```

Expected: Zero results.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/
git commit -m "fix(a11y): add aria-label to all icon-only buttons across all pages"
```

---

## Task 4 — Wire Payslip Download Button

**Files:**
- Modify: `frontend/src/pages/employee/PayslipsPage.tsx`

- [x] **Step 1: Check existing download hook**

```bash
grep -rn "useDownloadMyPayslip\|downloadPayslip" frontend/src/lib/api/ frontend/src/hooks/
```

Note the hook name and signature.

- [x] **Step 2: Wire the download button in `PayslipsPage.tsx`**

In `PayslipsPage.tsx`, locate the payslip detail view or list row. Add a download button connected to the hook:

```tsx
import { useDownloadMyPayslip } from '@/hooks/useDownloadMyPayslip';

function PayslipRow({ payslip }: { payslip: Payslip }) {
  const { download, isLoading } = useDownloadMyPayslip();

  return (
    <tr>
      {/* existing cells */}
      <td>
        <AppButton
          variant="ghost"
          size="icon"
          aria-label={`Download payslip for ${payslip.period_label}`}
          onClick={() => download(payslip.id)}
          disabled={isLoading}
        >
          <DownloadIcon className="h-4 w-4" />
        </AppButton>
      </td>
    </tr>
  );
}
```

If the hook does not exist, create `frontend/src/hooks/useDownloadMyPayslip.ts`:

```typescript
import { useState } from 'react';
import { downloadMyPayslip } from '@/lib/api/employee';

export function useDownloadMyPayslip() {
  const [isLoading, setIsLoading] = useState(false);

  async function download(payslipId: string) {
    setIsLoading(true);
    try {
      const blob = await downloadMyPayslip(payslipId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `payslip-${payslipId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setIsLoading(false);
    }
  }

  return { download, isLoading };
}
```

If `downloadMyPayslip` does not exist in `frontend/src/lib/api/employee.ts`, add:

```typescript
export async function downloadMyPayslip(payslipId: string): Promise<Blob> {
  const response = await apiClient.get(`/api/me/payroll/payslips/${payslipId}/download/`, {
    responseType: 'blob',
  });
  return response.data;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/employee/PayslipsPage.tsx frontend/src/hooks/useDownloadMyPayslip.ts frontend/src/lib/api/employee.ts
git commit -m "feat(payslips): wire payslip download button for employees"
```

---

## Task 5 — Add Form Labels in PayrollPage

**Files:**
- Modify: `frontend/src/pages/org/PayrollPage.tsx`

- [x] **Step 1: Find all bare `<input>` elements without associated `<label>`**

```bash
grep -n "<input\|<select\|<textarea" frontend/src/pages/org/PayrollPage.tsx | head -40
```

- [x] **Step 2: Fix each unlabelled input**

For each bare input:
```tsx
// Before:
<input type="number" value={rate} onChange={...} placeholder="Tax rate %" />

// After:
<label htmlFor="tax-rate-input" className="text-sm font-medium">
  Tax Rate (%)
  <span className="text-red-500 ml-1" aria-hidden="true">*</span>
</label>
<input
  id="tax-rate-input"
  type="number"
  value={rate}
  onChange={...}
  placeholder="Tax rate %"
  aria-required="true"
/>
```

Apply to all inputs: tax slab rates, income range inputs, compensation template line amounts, etc.

- [x] **Step 3: Replace native date inputs with `AppDatePicker`**

Find all `<input type="date"` in `PayrollPage.tsx`:
```bash
grep -n 'type="date"' frontend/src/pages/org/PayrollPage.tsx
```

Replace each with the existing `AppDatePicker` component:
```tsx
// Before:
<input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />

// After:
import { AppDatePicker } from '@/components/ui/AppDatePicker';
<AppDatePicker value={startDate} onChange={setStartDate} label="Start Date" />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/org/PayrollPage.tsx
git commit -m "fix(a11y): add form labels and replace native date inputs in PayrollPage"
```

---

## Task 6 — Table Overflow Safety

**Files:**
- Modify: `frontend/src/pages/org/PayrollPage.tsx` and all other pages with `<table>` elements

- [x] **Step 1: Find all bare `<table>` elements**

```bash
grep -rn "<table" frontend/src/pages/ --include="*.tsx" | grep -v "overflow-x-auto"
```

- [x] **Step 2: Wrap each table in `<div className="overflow-x-auto">`**

```tsx
// Before:
<table className="w-full text-sm">
  ...
</table>

// After:
<div className="overflow-x-auto">
  <table className="w-full text-sm">
    ...
  </table>
</div>
```

Apply across all pages found.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/
git commit -m "fix(ux): wrap all tables in overflow-x-auto for horizontal scroll safety"
```

---

## Task 7 — Status Tone Functions

**Files:**
- Modify: `frontend/src/lib/status.ts`

- [x] **Step 1: Read the existing `status.ts`**

Open the file and identify the existing tone functions (e.g., `getLeaveStatusTone`, `getApprovalStatusTone`).

- [x] **Step 2: Add new tone functions**

Append to `frontend/src/lib/status.ts`:

```typescript
// Payroll run status tones
export function getPayrollRunStatusTone(status: string): string {
  const tones: Record<string, string> = {
    DRAFT: 'gray',
    CALCULATING: 'blue',
    CALCULATED: 'blue',
    PENDING_APPROVAL: 'yellow',
    APPROVED: 'green',
    FINALIZED: 'green',
    REJECTED: 'red',
  };
  return tones[status] ?? 'gray';
}

// Compensation assignment status tones
export function getCompensationStatusTone(status: string): string {
  const tones: Record<string, string> = {
    DRAFT: 'gray',
    PENDING_APPROVAL: 'yellow',
    ACTIVE: 'green',
    REJECTED: 'red',
    EXPIRED: 'gray',
    SUPERSEDED: 'gray',
  };
  return tones[status] ?? 'gray';
}

// Attendance import status tones
export function getAttendanceImportTone(status: string): string {
  const tones: Record<string, string> = {
    PENDING: 'yellow',
    PROCESSING: 'blue',
    COMPLETED: 'green',
    FAILED: 'red',
    PARTIAL: 'orange',
  };
  return tones[status] ?? 'gray';
}

// Attendance day status tones
export function getAttendanceDayStatusTone(status: string): string {
  const tones: Record<string, string> = {
    PRESENT: 'green',
    HALF_DAY: 'yellow',
    ABSENT: 'red',
    ON_LEAVE: 'blue',
    ON_DUTY: 'purple',
    HOLIDAY: 'gray',
    WEEKEND: 'gray',
    INCOMPLETE: 'orange',
  };
  return tones[status] ?? 'gray';
}
```

- [x] **Step 3: Apply new tone functions in relevant pages**

In `PayrollPage.tsx`, replace hardcoded status badge colours with `getPayrollRunStatusTone`:
```tsx
import { getPayrollRunStatusTone } from '@/lib/status';

<AppBadge tone={getPayrollRunStatusTone(payRun.status)}>
  {payRun.status}
</AppBadge>
```

Apply similarly in compensation assignment tables and attendance import pages.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/status.ts frontend/src/pages/
git commit -m "feat(ui): add payroll/compensation/attendance status tone functions"
```

---

## Task 8 — Collapsible Nav Groups in OrgLayout

**Files:**
- Modify: `frontend/src/components/layouts/OrgLayout.tsx`

- [x] **Step 1: Read existing nav structure**

Open `OrgLayout.tsx` and identify the navigation items list. Note existing structure (flat list vs grouped).

- [x] **Step 2: Add collapsible group state and rendering**

```tsx
// Add state for collapsed groups
const [collapsedGroups, setCollapsedGroups] = React.useState<Record<string, boolean>>({});

function toggleGroup(groupName: string) {
  setCollapsedGroups(prev => ({ ...prev, [groupName]: !prev[groupName] }));
}

// Nav group definitions
const navGroups = [
  {
    name: 'People',
    items: [
      { label: 'Employees', href: '/org/employees', icon: UsersIcon },
      { label: 'Departments', href: '/org/departments', icon: BuildingIcon },
      { label: 'Locations', href: '/org/locations', icon: MapPinIcon },
    ],
  },
  {
    name: 'Time & Leave',
    items: [
      { label: 'Attendance', href: '/org/attendance', icon: ClockIcon },
      { label: 'Leave Plans', href: '/org/leave-plans', icon: CalendarIcon },
    ],
  },
  {
    name: 'Compensation',
    items: [
      { label: 'Payroll', href: '/org/payroll', icon: CurrencyIcon },
      { label: 'Documents', href: '/org/documents', icon: DocumentIcon },
    ],
  },
  {
    name: 'Governance',
    items: [
      { label: 'Approvals', href: '/org/approvals', icon: CheckCircleIcon },
      { label: 'Audit Log', href: '/org/audit', icon: ShieldIcon },
    ],
  },
];

// Render:
{navGroups.map(group => (
  <div key={group.name}>
    <button
      onClick={() => toggleGroup(group.name)}
      className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-700"
      aria-expanded={!collapsedGroups[group.name]}
      aria-controls={`nav-group-${group.name}`}
    >
      {group.name}
      <ChevronDownIcon
        className={`h-4 w-4 transition-transform ${collapsedGroups[group.name] ? '-rotate-90' : ''}`}
      />
    </button>
    <div
      id={`nav-group-${group.name}`}
      className={collapsedGroups[group.name] ? 'hidden' : ''}
    >
      {group.items.map(item => (
        <NavLink key={item.href} to={item.href} className="...">
          <item.icon className="h-5 w-5" aria-hidden="true" />
          {item.label}
        </NavLink>
      ))}
    </div>
  </div>
))}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layouts/OrgLayout.tsx
git commit -m "feat(nav): collapsible nav group sections in OrgLayout"
```

---

## Task 9 — Real-Time Leave Balance Preview in LeavePage

**Files:**
- Modify: `frontend/src/pages/employee/LeavePage.tsx`

- [x] **Step 1: Add live balance preview to leave request form**

When the user selects a leave type and enters dates, show a preview of how many days will be deducted and the remaining balance:

```tsx
// Inside the leave request form component
const [selectedLeaveTypeId, setSelectedLeaveTypeId] = React.useState('');
const [startDate, setStartDate] = React.useState('');
const [endDate, setEndDate] = React.useState('');

// Calculate requested days (simple weekday count or calendar days)
const requestedDays = React.useMemo(() => {
  if (!startDate || !endDate) return 0;
  const start = new Date(startDate);
  const end = new Date(endDate);
  const diffTime = end.getTime() - start.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
}, [startDate, endDate]);

// Get current balance for selected leave type
const balances = useMyLeaveBalances();
const currentBalance = balances.data?.find(b => b.leave_type.id === selectedLeaveTypeId)?.available ?? 0;
const remainingAfter = currentBalance - requestedDays;

// Render preview:
{selectedLeaveTypeId && startDate && endDate && (
  <div className="rounded-md bg-blue-50 p-3 text-sm mt-3">
    <div className="flex justify-between">
      <span>Requested days:</span>
      <span className="font-medium">{requestedDays}</span>
    </div>
    <div className="flex justify-between">
      <span>Current balance:</span>
      <span className="font-medium">{currentBalance}</span>
    </div>
    <div className={`flex justify-between font-semibold ${remainingAfter < 0 ? 'text-red-600' : 'text-green-700'}`}>
      <span>Remaining after:</span>
      <span>{remainingAfter}</span>
    </div>
    {remainingAfter < 0 && (
      <p className="text-red-600 text-xs mt-1">
        Insufficient balance. {Math.abs(remainingAfter)} day(s) will be treated as LOP if applicable.
      </p>
    )}
  </div>
)}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/employee/LeavePage.tsx
git commit -m "feat(leave): real-time balance preview in leave request form"
```

---

## Task 10 — Toast Loading Feedback for Long Operations

**Files:**
- Modify: `frontend/src/pages/org/PayrollPage.tsx`

- [x] **Step 1: Add `toast.loading()` to long-running mutations**

Identify the mutations in `PayrollPage.tsx` for payroll calculation, finalization, and calculation polling. Add loading toasts:

```tsx
import toast from 'react-hot-toast';

// For calculate mutation:
const calculateMutation = useMutation({
  mutationFn: (payRunId: string) => triggerPayrollCalculation(payRunId),
  onMutate: () => {
    return toast.loading('Dispatching calculation…');
  },
  onSuccess: (data, _, toastId) => {
    toast.dismiss(toastId as string);
    toast.success('Calculation started. Results will appear shortly.');
    // Start polling for status
    startPolling(data.task_id);
  },
  onError: (_, __, toastId) => {
    toast.dismiss(toastId as string);
    toast.error('Failed to start calculation. Please try again.');
  },
});

// For finalize mutation:
const finalizeMutation = useMutation({
  mutationFn: (payRunId: string) => finalizePayRun(payRunId),
  onMutate: () => {
    return toast.loading('Finalizing pay run…');
  },
  onSuccess: (_, __, toastId) => {
    toast.dismiss(toastId as string);
    toast.success('Pay run finalized successfully.');
    queryClient.invalidateQueries({ queryKey: ['payroll-summary'] });
  },
  onError: (error: Error, _, toastId) => {
    toast.dismiss(toastId as string);
    toast.error(`Finalization failed: ${error.message}`);
  },
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/org/PayrollPage.tsx
git commit -m "feat(ux): toast.loading feedback for payroll calculate and finalize operations"
```

---

## Task 11 — AppErrorBoundary on All Routes

**Files:**
- Create: `frontend/src/components/ui/AppErrorBoundary.tsx`
- Modify: `frontend/src/routes/index.tsx`

- [x] **Step 1: Create `AppErrorBoundary.tsx`**

```tsx
// frontend/src/components/ui/AppErrorBoundary.tsx
import React from 'react';

interface State {
  hasError: boolean;
  error: Error | null;
}

export class AppErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  State
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[AppErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Something went wrong</h2>
          <p className="text-gray-500 text-sm mb-4">
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </p>
          <button
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [x] **Step 2: Wrap routes in `AppErrorBoundary`**

In `frontend/src/routes/index.tsx`, find the route definitions. Wrap each top-level route element:

```tsx
import { AppErrorBoundary } from '@/components/ui/AppErrorBoundary';

// Before:
{ path: '/org/payroll', element: <PayrollPage /> }

// After:
{
  path: '/org/payroll',
  element: (
    <AppErrorBoundary>
      <PayrollPage />
    </AppErrorBoundary>
  )
}
```

Or, if using a layout-based structure, wrap the layout outlet once:

```tsx
{
  path: '/org',
  element: (
    <AppErrorBoundary>
      <OrgLayout />
    </AppErrorBoundary>
  ),
  children: [...]
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/AppErrorBoundary.tsx frontend/src/routes/index.tsx
git commit -m "feat(ui): AppErrorBoundary wrapping all routes to prevent blank screen on crash"
```

---

## Task 12 — LeavePlanBuilder 3-Step Wizard

**Files:**
- Modify: `frontend/src/pages/org/LeavePlanBuilderPage.tsx`

- [x] **Step 1: Add wizard step state**

```tsx
// Steps: 1 = Basic Info, 2 = Leave Types, 3 = Assignment Rules
const [currentStep, setCurrentStep] = React.useState<1 | 2 | 3>(1);
const TOTAL_STEPS = 3;
const STEP_LABELS = ['Basic Info', 'Leave Types', 'Assignment Rules'];
```

- [x] **Step 2: Add progress bar component inline**

```tsx
function WizardProgressBar({ currentStep, totalSteps, labels }: {
  currentStep: number;
  totalSteps: number;
  labels: string[];
}) {
  return (
    <nav aria-label="Progress" className="mb-8">
      <ol className="flex items-center gap-2">
        {labels.map((label, idx) => {
          const step = idx + 1;
          const isComplete = step < currentStep;
          const isCurrent = step === currentStep;
          return (
            <li key={label} className="flex items-center flex-1">
              <div className={`flex items-center justify-center h-8 w-8 rounded-full text-sm font-medium
                ${isComplete ? 'bg-blue-600 text-white' : isCurrent ? 'border-2 border-blue-600 text-blue-600' : 'border-2 border-gray-300 text-gray-400'}`}
                aria-current={isCurrent ? 'step' : undefined}
              >
                {isComplete ? '✓' : step}
              </div>
              <span className={`ml-2 text-sm ${isCurrent ? 'font-semibold text-gray-900' : 'text-gray-500'}`}>
                {label}
              </span>
              {idx < totalSteps - 1 && <div className="flex-1 h-px bg-gray-200 mx-4" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
```

- [x] **Step 3: Split form content into step sections**

```tsx
return (
  <div className="max-w-2xl mx-auto py-8 px-4">
    <WizardProgressBar currentStep={currentStep} totalSteps={TOTAL_STEPS} labels={STEP_LABELS} />

    {currentStep === 1 && (
      <Step1BasicInfo formData={formData} onChange={setFormData} />
    )}
    {currentStep === 2 && (
      <Step2LeaveTypes formData={formData} onChange={setFormData} />
    )}
    {currentStep === 3 && (
      <Step3AssignmentRules formData={formData} onChange={setFormData} />
    )}

    <div className="flex justify-between mt-8">
      {currentStep > 1 && (
        <AppButton variant="outline" onClick={() => setCurrentStep(s => (s - 1) as 1 | 2 | 3)}>
          Back
        </AppButton>
      )}
      {currentStep < TOTAL_STEPS ? (
        <AppButton onClick={() => setCurrentStep(s => (s + 1) as 1 | 2 | 3)}>
          Next
        </AppButton>
      ) : (
        <AppButton onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? 'Creating…' : 'Create Leave Plan'}
        </AppButton>
      )}
    </div>
  </div>
);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/org/LeavePlanBuilderPage.tsx
git commit -m "feat(ux): convert LeavePlanBuilderPage to 3-step wizard with progress bar"
```

---

## Verification

```bash
# Run all new unit tests
cd frontend && npx vitest run src/components/ui/ConfirmDialog.test.tsx

# Check no remaining window.confirm calls
grep -rn "window.confirm" frontend/src/pages/ && echo "FOUND - fix remaining" || echo "CLEAN"

# Check no icon buttons missing aria-label
grep -rn 'size="icon"' frontend/src/pages/ | grep -v "aria-label" | wc -l
# Expected: 0
```
