import { useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCreateLeaveCycle,
  useCreateLeavePlan,
  useCreateOnDutyPolicy,
  useLeaveCycles,
  useLeavePlans,
  useOnDutyPolicies,
  useOrgLeaveRequests,
  useOrgOnDutyRequests,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { getLeaveStatusTone } from '@/lib/status'

export function LeavePlansPage() {
  const { data: cycles, isLoading } = useLeaveCycles()
  const { data: plans } = useLeavePlans()
  const { data: policies } = useOnDutyPolicies()
  const { data: leaveRequests } = useOrgLeaveRequests()
  const { data: odRequests } = useOrgOnDutyRequests()
  const createCycleMutation = useCreateLeaveCycle()
  const createPlanMutation = useCreateLeavePlan()
  const createPolicyMutation = useCreateOnDutyPolicy()

  const [cycleForm, setCycleForm] = useState({
    name: 'Default Leave Year',
    cycle_type: 'CALENDAR_YEAR',
    start_month: 1,
    start_day: 1,
    is_default: true,
    is_active: true,
  })
  const [planForm, setPlanForm] = useState({
    leave_cycle_id: '',
    name: 'General Leave Plan',
    description: '',
    is_default: true,
    is_active: true,
    priority: 100,
    leave_types: [
      {
        code: 'CL',
        name: 'Casual Leave',
        description: '',
        color: '#2563eb',
        is_paid: true,
        is_loss_of_pay: false,
        annual_entitlement: '12.00',
        credit_frequency: 'MONTHLY',
        prorate_on_join: true,
        carry_forward_mode: 'CAPPED',
        carry_forward_cap: '6.00',
        max_balance: '18.00',
        allows_half_day: true,
        requires_attachment: false,
        min_notice_days: 0,
        allow_past_request: false,
        allow_future_request: true,
        is_active: true,
      },
    ],
    rules: [],
  })
  const [policyForm, setPolicyForm] = useState({
    name: 'Default On Duty Policy',
    description: '',
    is_default: true,
    is_active: true,
    allow_half_day: true,
    allow_time_range: true,
    requires_attachment: false,
    min_notice_days: 0,
    allow_past_request: false,
    allow_future_request: true,
  })

  const handleCycleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createCycleMutation.mutateAsync(cycleForm)
      toast.success('Leave cycle created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create leave cycle.'))
    }
  }

  const handlePlanSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createPlanMutation.mutateAsync(planForm)
      toast.success('Leave plan created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create leave plan.'))
    }
  }

  const handlePolicySubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createPolicyMutation.mutateAsync(policyForm)
      toast.success('On-duty policy created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create on-duty policy.'))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Leave and OD" title="Policies, plans, and requests" description="Configure leave cycles, leave structures, on-duty policies, and monitor requests routed through approvals." />

      <div className="grid gap-6 xl:grid-cols-3">
        <SectionCard title="Leave cycle" description="Leave cycles can follow calendar year, financial year, or custom periods.">
          <form onSubmit={handleCycleSubmit} className="grid gap-4">
            <input className="field-input" value={cycleForm.name} onChange={(event) => setCycleForm((current) => ({ ...current, name: event.target.value }))} />
            <select className="field-select" value={cycleForm.cycle_type} onChange={(event) => setCycleForm((current) => ({ ...current, cycle_type: event.target.value }))}>
              {['CALENDAR_YEAR', 'FINANCIAL_YEAR', 'CUSTOM_FIXED_START', 'EMPLOYEE_JOINING_DATE'].map((type) => (
                <option key={type} value={type}>
                  {type.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            <button type="submit" className="btn-primary" disabled={createCycleMutation.isPending}>
              Save cycle
            </button>
          </form>
          <div className="mt-5 space-y-2">
            {cycles?.map((cycle) => (
              <div key={cycle.id} className="surface-muted rounded-[18px] px-3 py-3">
                <p className="font-medium text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{cycle.cycle_type.replace(/_/g, ' ')}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Leave plan" description="Leave plans support multiple leave types with different accrual and carry-forward rules.">
          <form onSubmit={handlePlanSubmit} className="grid gap-4">
            <select className="field-select" value={planForm.leave_cycle_id} onChange={(event) => setPlanForm((current) => ({ ...current, leave_cycle_id: event.target.value }))} required>
              <option value="">Select leave cycle</option>
              {cycles?.map((cycle) => (
                <option key={cycle.id} value={cycle.id}>
                  {cycle.name}
                </option>
              ))}
            </select>
            <input className="field-input" value={planForm.name} onChange={(event) => setPlanForm((current) => ({ ...current, name: event.target.value }))} />
            <input className="field-input" value={planForm.leave_types[0].name} onChange={(event) => setPlanForm((current) => ({ ...current, leave_types: [{ ...current.leave_types[0], name: event.target.value }] }))} placeholder="Primary leave type name" />
            <input className="field-input" value={planForm.leave_types[0].annual_entitlement} onChange={(event) => setPlanForm((current) => ({ ...current, leave_types: [{ ...current.leave_types[0], annual_entitlement: event.target.value }] }))} placeholder="Annual entitlement" />
            <select className="field-select" value={planForm.leave_types[0].credit_frequency} onChange={(event) => setPlanForm((current) => ({ ...current, leave_types: [{ ...current.leave_types[0], credit_frequency: event.target.value }] }))}>
              {['MANUAL', 'MONTHLY', 'QUARTERLY', 'HALF_YEARLY', 'YEARLY'].map((frequency) => (
                <option key={frequency} value={frequency}>
                  {frequency.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            <button type="submit" className="btn-primary" disabled={createPlanMutation.isPending}>
              Save plan
            </button>
          </form>
          <div className="mt-5 space-y-2">
            {plans?.map((plan) => (
              <div key={plan.id} className="surface-muted rounded-[18px] px-3 py-3">
                <p className="font-medium text-[hsl(var(--foreground-strong))]">{plan.name}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{plan.leave_types.map((type) => type.name).join(', ')}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="On-duty policy" description="Use OD for field travel, customer visits, and other attendance exceptions that should still go through approvals.">
          <form onSubmit={handlePolicySubmit} className="grid gap-4">
            <input className="field-input" value={policyForm.name} onChange={(event) => setPolicyForm((current) => ({ ...current, name: event.target.value }))} />
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input type="checkbox" checked={policyForm.allow_time_range} onChange={(event) => setPolicyForm((current) => ({ ...current, allow_time_range: event.target.checked }))} />
              Allow time range requests
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input type="checkbox" checked={policyForm.allow_half_day} onChange={(event) => setPolicyForm((current) => ({ ...current, allow_half_day: event.target.checked }))} />
              Allow half-day OD
            </label>
            <button type="submit" className="btn-primary" disabled={createPolicyMutation.isPending}>
              Save OD policy
            </button>
          </form>
          <div className="mt-5 space-y-2">
            {policies?.map((policy) => (
              <div key={policy.id} className="surface-muted rounded-[18px] px-3 py-3">
                <p className="font-medium text-[hsl(var(--foreground-strong))]">{policy.name}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{policy.is_default ? 'Default policy' : 'Secondary policy'}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Recent leave requests" description="Review current leave traffic across the organisation.">
          <div className="space-y-3">
            {leaveRequests?.slice(0, 8).map((request) => (
              <div key={request.id} className="surface-muted flex items-center justify-between rounded-[20px] px-4 py-3">
                <div>
                  <p className="font-medium text-[hsl(var(--foreground-strong))]">{request.employee_name}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">{request.leave_type_name} • {request.start_date}</p>
                </div>
                <StatusBadge tone={getLeaveStatusTone(request.status)}>{request.status}</StatusBadge>
              </div>
            ))}
          </div>
        </SectionCard>
        <SectionCard title="Recent OD requests" description="Track on-duty movement and approval load.">
          <div className="space-y-3">
            {odRequests?.slice(0, 8).map((request) => (
              <div key={request.id} className="surface-muted flex items-center justify-between rounded-[20px] px-4 py-3">
                <div>
                  <p className="font-medium text-[hsl(var(--foreground-strong))]">{request.employee_name}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">{request.policy_name} • {request.start_date}</p>
                </div>
                <StatusBadge tone={getLeaveStatusTone(request.status)}>{request.status}</StatusBadge>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
