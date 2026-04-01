import { useState } from 'react'
import { toast } from 'sonner'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useCreateLeavePlan, useLeaveCycles, useLeavePlans } from '@/hooks/useOrgAdmin'
import { createDefaultLeavePlanForm, LEAVE_CREDIT_FREQUENCY_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'

export function LeavePlansPage() {
  const { data: cycles, isLoading } = useLeaveCycles()
  const { data: plans } = useLeavePlans()
  const createPlanMutation = useCreateLeavePlan()
  const [planForm, setPlanForm] = useState(createDefaultLeavePlanForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handlePlanSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createPlanMutation.mutateAsync(planForm)
      toast.success('Leave plan created.')
      setPlanForm(createDefaultLeavePlanForm())
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to create leave plan.'))
      }
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
      <PageHeader
        eyebrow="Leave configuration"
        title="Leave plans"
        description="Configure leave structures and entitlements separately from leave-year settings and on-duty policy rules."
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard
          title="Create leave plan"
          description="Attach the plan to a leave cycle, then define the first leave type with accrual and carry-forward rules."
        >
          <form onSubmit={handlePlanSubmit} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="leave-cycle-id">
                Leave cycle
              </label>
              <select
                id="leave-cycle-id"
                className="field-select"
                value={planForm.leave_cycle_id}
                onChange={(event) => setPlanForm((current) => ({ ...current, leave_cycle_id: event.target.value }))}
                required
              >
                <option value="">Select leave cycle</option>
                {cycles?.map((cycle) => (
                  <option key={cycle.id} value={cycle.id}>
                    {cycle.name}
                  </option>
                ))}
              </select>
              <FieldErrorText message={fieldErrors.leave_cycle_id} />
            </div>
            <div>
              <label className="field-label" htmlFor="leave-plan-name">
                Plan name
              </label>
              <input
                id="leave-plan-name"
                className="field-input"
                value={planForm.name}
                onChange={(event) => setPlanForm((current) => ({ ...current, name: event.target.value }))}
                required
              />
              <FieldErrorText message={fieldErrors.name} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="leave-type-name">
                  Primary leave type
                </label>
                <input
                  id="leave-type-name"
                  className="field-input"
                  value={planForm.leave_types[0].name}
                  onChange={(event) =>
                    setPlanForm((current) => ({
                      ...current,
                      leave_types: [{ ...current.leave_types[0], name: event.target.value }],
                    }))
                  }
                />
              </div>
              <div>
                <label className="field-label" htmlFor="leave-type-code">
                  Leave code
                </label>
                <input
                  id="leave-type-code"
                  className="field-input"
                  value={planForm.leave_types[0].code}
                  onChange={(event) =>
                    setPlanForm((current) => ({
                      ...current,
                      leave_types: [{ ...current.leave_types[0], code: event.target.value.toUpperCase() }],
                    }))
                  }
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="annual-entitlement">
                  Annual entitlement
                </label>
                <input
                  id="annual-entitlement"
                  className="field-input"
                  value={planForm.leave_types[0].annual_entitlement}
                  onChange={(event) =>
                    setPlanForm((current) => ({
                      ...current,
                      leave_types: [{ ...current.leave_types[0], annual_entitlement: event.target.value }],
                    }))
                  }
                />
              </div>
              <div>
                <label className="field-label" htmlFor="credit-frequency">
                  Credit frequency
                </label>
                <select
                  id="credit-frequency"
                  className="field-select"
                  value={planForm.leave_types[0].credit_frequency}
                  onChange={(event) =>
                    setPlanForm((current) => ({
                      ...current,
                      leave_types: [{ ...current.leave_types[0], credit_frequency: event.target.value }],
                    }))
                  }
                >
                  {LEAVE_CREDIT_FREQUENCY_OPTIONS.map((frequency) => (
                    <option key={frequency} value={frequency}>
                      {frequency.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                type="checkbox"
                checked={planForm.is_default}
                onChange={(event) => setPlanForm((current) => ({ ...current, is_default: event.target.checked }))}
              />
              Default leave plan
            </label>
            <button type="submit" className="btn-primary" disabled={createPlanMutation.isPending}>
              Save leave plan
            </button>
          </form>
        </SectionCard>

        <SectionCard
          title="Configured leave plans"
          description="Each plan can eventually carry multiple leave types and assignment rules. This view keeps the current setup readable."
        >
          <div className="space-y-3">
            {plans?.map((plan) => (
              <div key={plan.id} className="surface-muted rounded-[20px] px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{plan.name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{plan.description || 'No description set'}</p>
                  </div>
                  <div className="text-sm text-[hsl(var(--muted-foreground))]">
                    {plan.is_default ? 'Default plan' : 'Secondary plan'} • {plan.leave_types.length} leave type(s)
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {plan.leave_types.map((leaveType) => (
                    <div key={leaveType.id} className="surface-shell rounded-[16px] px-3 py-3">
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{leaveType.name}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        {leaveType.annual_entitlement} days • {leaveType.credit_frequency.replace(/_/g, ' ')}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
