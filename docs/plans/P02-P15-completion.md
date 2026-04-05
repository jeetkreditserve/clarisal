# P02–P15 Completion Backlog

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the four frontend gaps that exist in completed backend plans (P02, P03, P04) where backend API + models + tests are fully implemented but no frontend hook, API wrapper, or UI was ever wired.

**Architecture:** All four tasks are pure frontend additions against already-stable backend endpoints. No backend model changes, no new migrations, no new backend tests required. Each task is: add TypeScript type → add API wrapper → add React Query hook → wire UI in an existing page.

**Tech Stack:** React 19 · TypeScript · TanStack Query v5 · Vitest · React Testing Library

---

## Context: What P16–P23 Already Cover

Before implementing anything here, note these items from P02–P15 that are **already planned** in future plans:

| Feature | Covered by |
|---|---|
| Investment Declaration (IT Declaration) employee UI | P20 Task 4 |
| Leave calendar withdrawal UX | P20 Task 6 |
| PayslipsPage year filter and bulk download | P20 Task 6 |
| Employee dashboard attendance summary | P20 Task 6 |
| Leave encashment annual automation (LWP lapse) | P18 Task 5 |

Do **not** re-implement those here.

---

## What This Plan Covers

| Gap | From Plan | Backend Status | Frontend Status |
|---|---|---|---|
| Full & Final Settlement display in offboarding | P02 | ✅ API endpoints exist | ❌ No hook, no UI |
| Arrears backend API + frontend | P02 | ❌ Model only, no API | ❌ No hook, no UI |
| Leave Encashment request UI | P03 | ✅ API endpoint exists | ❌ No hook, no UI |
| Probation completion button | P04 | ✅ API endpoint exists | ❌ No hook, no UI |

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `frontend/src/types/hr.ts` | Modify | Add `FullAndFinalSettlement`, `Arrears`, `LeaveEncashmentRequest` types; add `probation_end_date` to `EmployeeDetail` |
| `frontend/src/lib/api/org-admin.ts` | Modify | Add F&F, Arrears, and probation API functions |
| `frontend/src/lib/api/self-service.ts` | Modify | Add leave encashment API functions |
| `frontend/src/hooks/useOrgAdmin.ts` | Modify | Add F&F, Arrears, and probation hooks |
| `frontend/src/hooks/useEmployeeSelf.ts` | Modify | Add leave encashment hooks |
| `frontend/src/pages/org/EmployeeDetailPage.tsx` | Modify | Show F&F settlement in offboarding section; add probation completion button |
| `frontend/src/pages/org/PayrollPage.tsx` | Modify | Add Arrears section under compensation tab |
| `frontend/src/pages/employee/LeavePage.tsx` | Modify | Add leave encashment request section |
| `backend/apps/payroll/serializers.py` | Modify | Add `ArrearsSerializer`, `ArrearsCreateSerializer` |
| `backend/apps/payroll/views.py` | Modify | Add `OrgArrearsListCreateView`, `OrgArrearsDetailView` |
| `backend/apps/payroll/org_urls.py` | Modify | Register arrears URL patterns |
| `backend/apps/payroll/tests/test_views.py` | Modify | Add arrears endpoint tests |

---

## Task 1: Full & Final Settlement Frontend

**Files:**
- Modify: `frontend/src/types/hr.ts`
- Modify: `frontend/src/lib/api/org-admin.ts`
- Modify: `frontend/src/hooks/useOrgAdmin.ts`
- Modify: `frontend/src/pages/org/EmployeeDetailPage.tsx`

### Background

The backend has `OrgFullAndFinalSettlementListView` (GET `/org/payroll/full-and-final-settlements/`) and `OrgFullAndFinalSettlementDetailView` (GET `/org/payroll/full-and-final-settlements/<pk>/`). The F&F settlement is created automatically when a payroll run covering a departing employee is finalized. The frontend `EmployeeDetailPage` already shows an offboarding checklist panel but has no F&F financial summary.

The serializer returns:
```
id, employee_id, employee_name, offboarding_process_id, last_working_day, status,
prorated_salary, leave_encashment, gratuity, arrears, other_credits,
tds_deduction, pf_deduction, loan_recovery, other_deductions,
gross_payable, net_payable, notes, approved_at, paid_at, created_at, modified_at
```

`status` choices: `DRAFT | CALCULATED | APPROVED | PAID | CANCELLED`

- [x] **Step 1: Add TypeScript type**

In `frontend/src/types/hr.ts`, add after the `OffboardingProcess` interface:

```typescript
export type FNFStatus = 'DRAFT' | 'CALCULATED' | 'APPROVED' | 'PAID' | 'CANCELLED'

export interface FullAndFinalSettlement {
  id: string
  employee_id: string
  employee_name: string
  offboarding_process_id: string | null
  last_working_day: string
  status: FNFStatus
  prorated_salary: string
  leave_encashment: string
  gratuity: string
  arrears: string
  other_credits: string
  tds_deduction: string
  pf_deduction: string
  loan_recovery: string
  other_deductions: string
  gross_payable: string
  net_payable: string
  notes: string
  approved_at: string | null
  paid_at: string | null
  created_at: string
  modified_at: string
}
```

- [x] **Step 2: Add API functions**

In `frontend/src/lib/api/org-admin.ts`, add imports for `FullAndFinalSettlement` from `@/types/hr` and add:

```typescript
export async function fetchOrgFullAndFinalSettlements() {
  const { data } = await api.get<FullAndFinalSettlement[]>('/org/payroll/full-and-final-settlements/')
  return data
}

export async function fetchOrgFullAndFinalSettlement(id: string) {
  const { data } = await api.get<FullAndFinalSettlement>(`/org/payroll/full-and-final-settlements/${id}/`)
  return data
}
```

- [x] **Step 3: Add React Query hooks**

In `frontend/src/hooks/useOrgAdmin.ts`, add imports for the two new API functions and add at the end of the file:

```typescript
export function useOrgFullAndFinalSettlements() {
  return useQuery({
    queryKey: ['org', 'fnf-settlements'],
    queryFn: fetchOrgFullAndFinalSettlements,
  })
}

export function useOrgFullAndFinalSettlement(id: string) {
  return useQuery({
    queryKey: ['org', 'fnf-settlements', id],
    queryFn: () => fetchOrgFullAndFinalSettlement(id),
    enabled: Boolean(id),
  })
}
```

- [x] **Step 4: Wire F&F summary in EmployeeDetailPage**

In `frontend/src/pages/org/EmployeeDetailPage.tsx`, after the existing offboarding section (which shows the checklist when `employee.offboarding` exists), add a F&F financial summary panel. The employee has `full_and_final_settlement` on their offboarding object only when the org finalized payroll for them. Instead of fetching the list, fetch by employee ID matching from the employee detail endpoint. Since the backend doesn't expose F&F per-employee directly, use the list endpoint and filter client-side, or fetch only when the employee is in an offboarding state.

Add this hook call near the other hooks in the component:

```typescript
const { data: fnfSettlements } = useOrgFullAndFinalSettlements()
const fnfSettlement = fnfSettlements?.find((s) => s.employee_id === employeeId) ?? null
```

Add this block inside the offboarding card (after the checklist `</div>` and before the closing tag of the offboarding section):

```tsx
{fnfSettlement && (
  <div className="surface-card mt-4 rounded-[28px] p-5">
    <div className="flex items-center justify-between">
      <p className="font-semibold text-[hsl(var(--foreground-strong))]">Full & Final Settlement</p>
      <StatusBadge
        tone={
          fnfSettlement.status === 'PAID' ? 'success'
          : fnfSettlement.status === 'APPROVED' ? 'info'
          : fnfSettlement.status === 'CANCELLED' ? 'danger'
          : 'warning'
        }
      >
        {fnfSettlement.status}
      </StatusBadge>
    </div>
    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
      Last working day: {fnfSettlement.last_working_day}
    </p>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
      {[
        { label: 'Prorated salary', value: fnfSettlement.prorated_salary },
        { label: 'Leave encashment', value: fnfSettlement.leave_encashment },
        { label: 'Gratuity', value: fnfSettlement.gratuity },
        { label: 'Arrears', value: fnfSettlement.arrears },
        { label: 'Other credits', value: fnfSettlement.other_credits },
        { label: 'TDS deduction', value: `-${fnfSettlement.tds_deduction}` },
        { label: 'PF deduction', value: `-${fnfSettlement.pf_deduction}` },
        { label: 'Loan recovery', value: `-${fnfSettlement.loan_recovery}` },
        { label: 'Other deductions', value: `-${fnfSettlement.other_deductions}` },
      ].map(({ label, value }) => (
        <div key={label} className="surface-muted rounded-[18px] p-3">
          <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
          <p className="mt-1 font-semibold text-[hsl(var(--foreground-strong))]">₹{value}</p>
        </div>
      ))}
    </div>
    <div className="mt-4 flex items-center justify-between rounded-[18px] bg-[hsl(var(--foreground-strong)_/_0.06)] px-4 py-3">
      <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Net payable</p>
      <p className="text-lg font-bold text-[hsl(var(--foreground-strong))]">₹{fnfSettlement.net_payable}</p>
    </div>
    {fnfSettlement.notes ? (
      <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">{fnfSettlement.notes}</p>
    ) : null}
  </div>
)}
```

Import `useOrgFullAndFinalSettlements` at the top of the file alongside other hook imports.

- [x] **Step 5: Run Vitest**

```bash
cd frontend && npx vitest run src/pages/org/EmployeeDetailPage
```

Expected: existing tests still pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/hr.ts frontend/src/lib/api/org-admin.ts frontend/src/hooks/useOrgAdmin.ts frontend/src/pages/org/EmployeeDetailPage.tsx
git commit -m "feat(payroll): add Full & Final Settlement display in employee offboarding section"
```

---

## Task 2: Arrears Backend API + Frontend

**Files:**
- Modify: `backend/apps/payroll/serializers.py`
- Modify: `backend/apps/payroll/views.py`
- Modify: `backend/apps/payroll/org_urls.py`
- Modify: `backend/apps/payroll/tests/test_views.py`
- Modify: `frontend/src/types/hr.ts`
- Modify: `frontend/src/lib/api/org-admin.ts`
- Modify: `frontend/src/hooks/useOrgAdmin.ts`
- Modify: `frontend/src/pages/org/PayrollPage.tsx`

### Background

`Arrears` model exists in `backend/apps/payroll/models.py` with fields:
- `employee` (FK), `pay_run` (FK, nullable), `for_period_year`, `for_period_month`, `reason`, `amount`, `is_included_in_payslip`

No serializer, no views, no URL entries exist yet. Arrears are manual adjustments for underpayments in previous periods — org admin creates them and they roll into the next payroll run calculation.

- [x] **Step 1: Write failing test**

In `backend/apps/payroll/tests/test_views.py`, add a test class for arrears after existing test classes:

```python
class TestOrgArrearsAPI:
    def test_create_arrear(self, org_admin_client, employee):
        response = org_admin_client.post(
            '/api/v1/org/payroll/arrears/',
            {
                'employee_id': str(employee.id),
                'for_period_year': 2024,
                'for_period_month': 3,
                'reason': 'Missed allowance Q4',
                'amount': '5000.00',
            },
            content_type='application/json',
        )
        assert response.status_code == 201
        assert response.json()['amount'] == '5000.00'
        assert response.json()['is_included_in_payslip'] is False

    def test_list_arrears(self, org_admin_client):
        response = org_admin_client.get('/api/v1/org/payroll/arrears/')
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

- [x] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest apps/payroll/tests/test_views.py::TestOrgArrearsAPI -v
```

Expected: 404 or AttributeError — endpoints don't exist yet.

- [x] **Step 3: Add serializers**

In `backend/apps/payroll/serializers.py`, import `Arrears` from `.models` and add after the `InvestmentDeclarationWriteSerializer`:

```python
class ArrearsSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source='employee.id', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    pay_run_id = serializers.UUIDField(source='pay_run.id', read_only=True, allow_null=True)

    class Meta:
        model = Arrears
        fields = [
            'id',
            'employee_id',
            'employee_name',
            'pay_run_id',
            'for_period_year',
            'for_period_month',
            'reason',
            'amount',
            'is_included_in_payslip',
            'created_at',
        ]


class ArrearsCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    for_period_year = serializers.IntegerField(min_value=2000, max_value=2099)
    for_period_month = serializers.IntegerField(min_value=1, max_value=12)
    reason = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
```

- [x] **Step 4: Add views**

In `backend/apps/payroll/views.py`, import `Arrears`, `ArrearsSerializer`, `ArrearsCreateSerializer` and add after `OrgFullAndFinalSettlementDetailView`:

```python
class OrgArrearsListCreateView(APIView):
    permission_classes = [IsOrgAdmin]

    def get(self, request):
        organisation = get_org_from_request(request)
        employee_id = request.query_params.get('employee_id')
        queryset = Arrears.objects.filter(employee__organisation=organisation).select_related('employee__user', 'pay_run')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return Response(ArrearsSerializer(queryset, many=True).data)

    def post(self, request):
        organisation = get_org_from_request(request)
        serializer = ArrearsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        from apps.employees.models import Employee
        employee = get_object_or_404(Employee, id=d['employee_id'], organisation=organisation)
        arrear = Arrears.objects.create(
            employee=employee,
            for_period_year=d['for_period_year'],
            for_period_month=d['for_period_month'],
            reason=d['reason'],
            amount=d['amount'],
        )
        return Response(ArrearsSerializer(arrear).data, status=status.HTTP_201_CREATED)
```

- [x] **Step 5: Register URLs**

In `backend/apps/payroll/org_urls.py`, add after the F&F settlement lines:

```python
path('payroll/arrears/', OrgArrearsListCreateView.as_view(), name='org-arrears-list-create'),
```

Also import `OrgArrearsListCreateView` at the top of the file.

- [x] **Step 6: Run tests to verify pass**

```bash
cd backend && python -m pytest apps/payroll/tests/test_views.py::TestOrgArrearsAPI -v
```

Expected: 2/2 PASS.

- [x] **Step 7: Add TypeScript type**

In `frontend/src/types/hr.ts`, add after `FullAndFinalSettlement`:

```typescript
export interface Arrears {
  id: string
  employee_id: string
  employee_name: string
  pay_run_id: string | null
  for_period_year: number
  for_period_month: number
  reason: string
  amount: string
  is_included_in_payslip: boolean
  created_at: string
}
```

- [x] **Step 8: Add API functions**

In `frontend/src/lib/api/org-admin.ts`, import `Arrears` from `@/types/hr` and add:

```typescript
export async function fetchOrgArrears(employeeId?: string) {
  const params = employeeId ? `?employee_id=${employeeId}` : ''
  const { data } = await api.get<Arrears[]>(`/org/payroll/arrears/${params}`)
  return data
}

export async function createOrgArrear(payload: {
  employee_id: string
  for_period_year: number
  for_period_month: number
  reason: string
  amount: string
}) {
  const { data } = await api.post<Arrears>('/org/payroll/arrears/', payload)
  return data
}
```

- [x] **Step 9: Add React Query hooks**

In `frontend/src/hooks/useOrgAdmin.ts`, import `fetchOrgArrears` and `createOrgArrear` and add:

```typescript
export function useOrgArrears(employeeId?: string) {
  return useQuery({
    queryKey: ['org', 'arrears', employeeId],
    queryFn: () => fetchOrgArrears(employeeId),
  })
}

export function useCreateOrgArrear() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createOrgArrear,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org', 'arrears'] })
    },
  })
}
```

- [x] **Step 10: Add Arrears section in PayrollPage**

In `frontend/src/pages/org/PayrollPage.tsx`, add `'arrears'` to `PAYROLL_SECTION_OPTIONS`:

```typescript
const PAYROLL_SECTION_OPTIONS = [
  { value: 'setup', label: 'Setup' },
  { value: 'compensation', label: 'Compensation' },
  { value: 'arrears', label: 'Arrears' },
  { value: 'runs', label: 'Runs' },
  { value: 'filings', label: 'Filings' },
] as const
```

Import `useOrgArrears`, `useCreateOrgArrear`, `Arrears` from the appropriate hooks/types. Add a state variable for the arrears form and a new section handler that renders when `activeSection === 'arrears'`:

```tsx
{activeSection === 'arrears' && (
  <SectionCard
    title="Salary arrears"
    description="Record underpayments from prior periods. Arrears are automatically included in the next calculated payroll run for the employee."
  >
    {/* Create form */}
    <form onSubmit={handleCreateArrear} className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label className="field-label">Employee</label>
        <AppSelect
          value={arrearForm.employee_id}
          onValueChange={(v) => setArrearForm((f) => ({ ...f, employee_id: v }))}
          options={(employees?.results ?? []).map((e) => ({ value: e.id, label: e.full_name }))}
          placeholder="Select employee"
        />
      </div>
      <div>
        <label className="field-label">Year</label>
        <input className="field-input" type="number" min={2000} max={2099} value={arrearForm.for_period_year}
          onChange={(e) => setArrearForm((f) => ({ ...f, for_period_year: Number(e.target.value) }))} />
      </div>
      <div>
        <label className="field-label">Month</label>
        <AppSelect
          value={String(arrearForm.for_period_month)}
          onValueChange={(v) => setArrearForm((f) => ({ ...f, for_period_month: Number(v) }))}
          options={Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1), label: new Date(0, i).toLocaleString('en-IN', { month: 'long' }) }))}
        />
      </div>
      <div className="sm:col-span-2">
        <label className="field-label">Reason</label>
        <input className="field-input" value={arrearForm.reason}
          onChange={(e) => setArrearForm((f) => ({ ...f, reason: e.target.value }))} placeholder="e.g. Missed Q3 performance allowance" />
      </div>
      <div>
        <label className="field-label">Amount (₹)</label>
        <input className="field-input" type="number" step="0.01" min="0.01" value={arrearForm.amount}
          onChange={(e) => setArrearForm((f) => ({ ...f, amount: e.target.value }))} />
      </div>
      <div className="flex items-end">
        <button type="submit" className="btn-primary" disabled={createArrearMutation.isPending}>
          Add arrear
        </button>
      </div>
    </form>

    {/* List */}
    <div className="mt-6 space-y-3">
      {arrears?.map((a) => (
        <div key={a.id} className="surface-muted flex flex-wrap items-center justify-between gap-3 rounded-[22px] p-4">
          <div>
            <p className="font-semibold text-[hsl(var(--foreground-strong))]">{a.employee_name}</p>
            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
              {a.reason} · {new Date(0, a.for_period_month - 1).toLocaleString('en-IN', { month: 'long' })} {a.for_period_year}
            </p>
          </div>
          <div className="text-right">
            <p className="font-semibold text-[hsl(var(--foreground-strong))]">₹{a.amount}</p>
            <StatusBadge tone={a.is_included_in_payslip ? 'success' : 'warning'}>
              {a.is_included_in_payslip ? 'Included in payslip' : 'Pending'}
            </StatusBadge>
          </div>
        </div>
      )) ?? null}
      {arrears?.length === 0 && (
        <EmptyState title="No arrears recorded" description="Arrears for underpaid prior periods appear here." />
      )}
    </div>
  </SectionCard>
)}
```

Add supporting state and handler before the return statement:

```typescript
const { data: arrears } = useOrgArrears()
const createArrearMutation = useCreateOrgArrear()
const [arrearForm, setArrearForm] = useState({
  employee_id: '',
  for_period_year: new Date().getFullYear(),
  for_period_month: new Date().getMonth() + 1,
  reason: '',
  amount: '',
})

const handleCreateArrear = async (event: React.FormEvent) => {
  event.preventDefault()
  try {
    await createArrearMutation.mutateAsync({
      ...arrearForm,
      for_period_year: Number(arrearForm.for_period_year),
      for_period_month: Number(arrearForm.for_period_month),
    })
    toast.success('Arrear recorded.')
    setArrearForm((f) => ({ ...f, employee_id: '', reason: '', amount: '' }))
  } catch (error) {
    toast.error(getErrorMessage(error, 'Unable to record arrear.'))
  }
}
```

- [x] **Step 11: Run Vitest**

```bash
cd frontend && npx vitest run src/pages/org/PayrollPage
```

Expected: existing tests pass.

- [ ] **Step 12: Commit**

```bash
git add backend/apps/payroll/serializers.py backend/apps/payroll/views.py backend/apps/payroll/org_urls.py backend/apps/payroll/tests/test_views.py frontend/src/types/hr.ts frontend/src/lib/api/org-admin.ts frontend/src/hooks/useOrgAdmin.ts frontend/src/pages/org/PayrollPage.tsx
git commit -m "feat(payroll): add Arrears API endpoints and PayrollPage arrears management section"
```

---

## Task 3: Leave Encashment Frontend

**Files:**
- Modify: `frontend/src/types/hr.ts`
- Modify: `frontend/src/lib/api/self-service.ts`
- Modify: `frontend/src/hooks/useEmployeeSelf.ts`
- Modify: `frontend/src/pages/employee/LeavePage.tsx`

### Background

The backend has:
- `GET /me/leave-encashments/` — list employee's encashment requests (`LeaveEncashmentRequestSerializer`)
- `POST /me/leave-encashments/` — create encashment request (`LeaveEncashmentRequestCreateSerializer`)

`LeaveEncashmentRequestSerializer` returns:
`id, employee_id, employee_name, leave_type_id, leave_type_name, cycle_start, cycle_end, days_to_encash, encashment_amount, status, rejection_reason, created_at`

`LeaveEncashmentStatus` choices: `PENDING | APPROVED | REJECTED | PAID | CANCELLED`

The `LeaveOverview` API (`GET /me/leave/`) already returns `balances[]` with `allows_encashment` per leave type.

`LeaveEncashmentRequestCreateSerializer` requires: `leave_type_id`, `days_to_encash`.

- [x] **Step 1: Add TypeScript type**

In `frontend/src/types/hr.ts`, add:

```typescript
export type LeaveEncashmentStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'PAID' | 'CANCELLED'

export interface LeaveEncashmentRequest {
  id: string
  employee_id: string
  employee_name: string
  leave_type_id: string
  leave_type_name: string
  cycle_start: string
  cycle_end: string
  days_to_encash: string
  encashment_amount: string | null
  status: LeaveEncashmentStatus
  rejection_reason: string
  created_at: string
}
```

Also, check if `LeaveOverview.balances` has `allows_encashment`. Read the type to see if it needs extending:

```typescript
// In LeaveOverview.balances entry, add if missing:
allows_encashment: boolean
max_encashment_days_per_year: string | null
```

- [x] **Step 2: Add API functions**

In `frontend/src/lib/api/self-service.ts`, import `LeaveEncashmentRequest` from `@/types/hr` and add:

```typescript
export async function fetchMyLeaveEncashments() {
  const { data } = await api.get<LeaveEncashmentRequest[]>('/me/leave-encashments/')
  return data
}

export async function createMyLeaveEncashment(payload: {
  leave_type_id: string
  days_to_encash: string
}) {
  const { data } = await api.post<LeaveEncashmentRequest>('/me/leave-encashments/', payload)
  return data
}
```

- [x] **Step 3: Add React Query hooks**

In `frontend/src/hooks/useEmployeeSelf.ts`, import the two new API functions and add at the end of the file:

```typescript
export function useMyLeaveEncashments() {
  return useQuery({
    queryKey: ['me', 'leave-encashments'],
    queryFn: fetchMyLeaveEncashments,
  })
}

export function useCreateMyLeaveEncashment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMyLeaveEncashment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'leave-encashments'] })
      queryClient.invalidateQueries({ queryKey: ['me', 'leave'] })
    },
  })
}
```

- [x] **Step 4: Add encashment section in LeavePage**

In `frontend/src/pages/employee/LeavePage.tsx`, import `useMyLeaveEncashments` and `useCreateMyLeaveEncashment` from `@/hooks/useEmployeeSelf`. Add state for the encashment form and handler.

Add after the existing "Request leave" `SectionCard`:

```tsx
{/* Encashment section — only shown when at least one leave type allows encashment */}
{data?.balances.some((b) => b.allows_encashment) && (
  <SectionCard
    title="Request leave encashment"
    description="Convert earned leave days to payout. Subject to your organisation's encashment policy and approval."
  >
    <form onSubmit={handleEncashmentSubmit} className="grid gap-4 sm:grid-cols-2">
      <div>
        <label className="field-label">Leave type</label>
        <AppSelect
          value={encashmentForm.leave_type_id}
          onValueChange={(v) => setEncashmentForm((f) => ({ ...f, leave_type_id: v }))}
          options={(data?.balances ?? [])
            .filter((b) => b.allows_encashment)
            .map((b) => ({ value: b.leave_type_id, label: b.leave_type_name }))}
          placeholder="Select leave type"
        />
      </div>
      <div>
        <label className="field-label">Days to encash</label>
        <input
          className="field-input"
          type="number"
          step="0.5"
          min="0.5"
          value={encashmentForm.days_to_encash}
          onChange={(e) => setEncashmentForm((f) => ({ ...f, days_to_encash: e.target.value }))}
        />
      </div>
      <div className="sm:col-span-2">
        <button type="submit" className="btn-primary" disabled={createEncashmentMutation.isPending}>
          Submit encashment request
        </button>
      </div>
    </form>

    {encashments && encashments.length > 0 && (
      <div className="mt-6 space-y-3">
        {encashments.map((e) => (
          <div key={e.id} className="surface-muted flex flex-wrap items-center justify-between gap-3 rounded-[22px] p-4">
            <div>
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">{e.leave_type_name}</p>
              <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                {e.days_to_encash} days · {e.cycle_start} to {e.cycle_end}
              </p>
              {e.rejection_reason && (
                <p className="mt-1 text-sm text-[hsl(var(--danger,_0_80%_50%))]">{e.rejection_reason}</p>
              )}
            </div>
            <div className="text-right">
              {e.encashment_amount && (
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">₹{e.encashment_amount}</p>
              )}
              <StatusBadge
                tone={
                  e.status === 'PAID' ? 'success'
                  : e.status === 'APPROVED' ? 'info'
                  : e.status === 'REJECTED' ? 'danger'
                  : 'warning'
                }
              >
                {e.status}
              </StatusBadge>
            </div>
          </div>
        ))}
      </div>
    )}
  </SectionCard>
)}
```

Add before the return statement:

```typescript
const { data: encashments } = useMyLeaveEncashments()
const createEncashmentMutation = useCreateMyLeaveEncashment()
const [encashmentForm, setEncashmentForm] = useState({ leave_type_id: '', days_to_encash: '' })

const handleEncashmentSubmit = async (event: React.FormEvent) => {
  event.preventDefault()
  try {
    await createEncashmentMutation.mutateAsync(encashmentForm)
    toast.success('Encashment request submitted.')
    setEncashmentForm({ leave_type_id: '', days_to_encash: '' })
  } catch (error) {
    toast.error(getErrorMessage(error, 'Unable to submit encashment request.'))
  }
}
```

Import `toast` from `sonner` and `getErrorMessage` from `@/lib/errors` if not already imported.

- [x] **Step 5: Run Vitest**

```bash
cd frontend && npx vitest run src/pages/employee/LeavePage
```

Expected: existing tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/hr.ts frontend/src/lib/api/self-service.ts frontend/src/hooks/useEmployeeSelf.ts frontend/src/pages/employee/LeavePage.tsx
git commit -m "feat(leave): add employee leave encashment request UI"
```

---

## Task 4: Probation Completion UI

**Files:**
- Modify: `frontend/src/types/hr.ts`
- Modify: `frontend/src/lib/api/org-admin.ts`
- Modify: `frontend/src/hooks/useOrgAdmin.ts`
- Modify: `frontend/src/pages/org/EmployeeDetailPage.tsx`

### Background

The backend has:
- `PATCH /org/employees/<pk>/probation-complete/` — clears `probation_end_date`, writes audit log
- `EmployeeDetail` serializer includes `probation_end_date: DateField | null`
- The TypeScript `EmployeeDetail` interface does NOT yet include `probation_end_date`

This is a simple read+action: show the probation end date in the employee profile section, and provide a "Mark probation complete" button when `probation_end_date` is not null.

- [x] **Step 1: Add `probation_end_date` to TypeScript type**

In `frontend/src/types/hr.ts`, find the `EmployeeDetail` interface and add after `date_of_exit`:

```typescript
probation_end_date: string | null
```

- [x] **Step 2: Add API function**

In `frontend/src/lib/api/org-admin.ts`, add:

```typescript
export async function markEmployeeProbationComplete(employeeId: string) {
  const { data } = await api.patch<EmployeeDetail>(`/org/employees/${employeeId}/probation-complete/`)
  return data
}
```

Import `EmployeeDetail` from `@/types/hr` if not already imported.

- [x] **Step 3: Add React Query hook**

In `frontend/src/hooks/useOrgAdmin.ts`, import `markEmployeeProbationComplete` and add:

```typescript
export function useMarkEmployeeProbationComplete(employeeId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => markEmployeeProbationComplete(employeeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org', 'employees', employeeId] })
    },
  })
}
```

- [x] **Step 4: Wire probation display + button in EmployeeDetailPage**

In `frontend/src/pages/org/EmployeeDetailPage.tsx`, import `useMarkEmployeeProbationComplete`.

Add near the other mutation hooks:

```typescript
const probationCompleteMutation = useMarkEmployeeProbationComplete(employeeId)
```

Add a handler:

```typescript
const handleProbationComplete = async () => {
  try {
    await probationCompleteMutation.mutateAsync()
    toast.success('Probation marked as complete.')
  } catch (error) {
    toast.error(getErrorMessage(error, 'Unable to mark probation complete.'))
  }
}
```

Find the section that shows `date_of_joining` and `date_of_exit` in the employee detail header (or profile section). Add a probation row adjacent to it:

```tsx
{employee.probation_end_date && (
  <div className="flex items-center gap-3">
    <div className="flex-1">
      <p className="text-xs uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Probation ends</p>
      <p className="mt-1 font-semibold text-[hsl(var(--foreground-strong))]">{employee.probation_end_date}</p>
    </div>
    <ConfirmDialog
      trigger={
        <button type="button" className="btn-secondary text-sm" disabled={probationCompleteMutation.isPending}>
          Mark complete
        </button>
      }
      title="Mark probation complete?"
      description={`This will clear the probation end date for ${employee.full_name} and log the event. This cannot be undone.`}
      confirmLabel="Mark complete"
      onConfirm={handleProbationComplete}
    />
  </div>
)}
```

`ConfirmDialog` is already imported in `EmployeeDetailPage.tsx` (verified at line 8).

- [x] **Step 5: Run Vitest**

```bash
cd frontend && npx vitest run src/pages/org/EmployeeDetailPage
```

Expected: existing tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/hr.ts frontend/src/lib/api/org-admin.ts frontend/src/hooks/useOrgAdmin.ts frontend/src/pages/org/EmployeeDetailPage.tsx
git commit -m "feat(employees): add probation end date display and Mark Complete button in EmployeeDetailPage"
```

---

## Verification Checklist

After all four tasks:

1. **F&F Settlement** — Open an employee with completed offboarding in org-admin. The offboarding section shows the F&F financial summary with net payable.
2. **Arrears** — In PayrollPage, switch to "Arrears" tab. Select an employee, enter amount and reason, submit. The arrear appears in the list.
3. **Leave Encashment** — Log in as an employee with an encashable leave type. LeavePage shows the encashment section. Submit a request. It appears in the list with PENDING status.
4. **Probation** — In EmployeeDetailPage for an employee with `probation_end_date` set, the probation date and "Mark complete" button appear. Clicking confirms and clears the date.

---

## What's Already Handled Elsewhere

- **Investment Declaration (IT Declaration) UI** → P20 Task 4 — do not duplicate here
- **Leave calendar withdrawal UX** → P20 Task 6
- **PayslipsPage year/search filters** → P20 Task 6
- **Dashboard attendance cards** → P20 Task 6
- **Leave encashment annual automation** → P18 Task 5
