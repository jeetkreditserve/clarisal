import { useState } from 'react'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useCreateLeavePlan, useLeaveCycles, useLeavePlans, useUpdateLeavePlan } from '@/hooks/useOrgAdmin'
import { createDefaultLeavePlanForm, LEAVE_CREDIT_FREQUENCY_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { startCase } from '@/lib/format'

export function LeavePlansPage() {
  const { data: cycles, isLoading } = useLeaveCycles()
  const { data: plans } = useLeavePlans()
  const createPlanMutation = useCreateLeavePlan()
  const [editingId, setEditingId] = useState<string | null>(null)
  const updatePlanMutation = useUpdateLeavePlan(editingId ?? '')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [planForm, setPlanForm] = useState(createDefaultLeavePlanForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const leaveCycleOptions = [
    { value: '', label: 'Select leave cycle' },
    ...(cycles?.map((cycle) => ({ value: cycle.id, label: cycle.name })) ?? []),
  ]
  const creditFrequencyOptions = LEAVE_CREDIT_FREQUENCY_OPTIONS.map((frequency) => ({
    value: frequency,
    label: startCase(frequency),
  }))

  const resetForm = () => {
    setEditingId(null)
    setPlanForm(createDefaultLeavePlanForm())
    setFieldErrors({})
    setIsModalOpen(false)
  }

  const handlePlanSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      if (editingId) {
        await updatePlanMutation.mutateAsync(planForm)
        toast.success('Leave plan updated.')
      } else {
        await createPlanMutation.mutateAsync(planForm)
        toast.success('Leave plan created.')
      }
      resetForm()
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to save leave plan.'))
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
        actions={
          <button type="button" className="btn-primary" onClick={() => setIsModalOpen(true)}>
            Add leave plan
          </button>
        }
      />

      <SectionCard
        title="Configured leave plans"
        description="Each plan can carry multiple leave types and assignment rules. The create and edit flows now use the same modal structure."
      >
        <div className="space-y-3">
          {plans?.map((plan) => (
            <div key={plan.id} className="surface-muted rounded-[20px] px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{plan.name}</p>
                  <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{plan.description || 'No description set'}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="text-sm text-[hsl(var(--muted-foreground))]">
                    {plan.is_default ? 'Default plan' : 'Secondary plan'} • {plan.leave_types.length} leave type(s)
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      const primaryType = plan.leave_types[0]
                      setEditingId(plan.id)
                      setPlanForm({
                        leave_cycle_id: plan.leave_cycle.id,
                        name: plan.name,
                        description: plan.description,
                        is_default: plan.is_default,
                        is_active: plan.is_active,
                        priority: plan.priority,
                        leave_types: [
                          {
                            name: primaryType?.name ?? '',
                            code: primaryType?.code ?? '',
                            description: primaryType?.description ?? '',
                            color: primaryType?.color ?? '#2563eb',
                            is_paid: primaryType?.is_paid ?? true,
                            is_loss_of_pay: primaryType?.is_loss_of_pay ?? false,
                            annual_entitlement: primaryType?.annual_entitlement ?? '0',
                            credit_frequency: primaryType?.credit_frequency ?? 'YEARLY',
                            carry_forward_mode: primaryType?.carry_forward_mode ?? 'NONE',
                            carry_forward_cap: primaryType?.carry_forward_cap ?? '',
                            max_balance: primaryType?.max_balance ?? '',
                            allows_half_day: primaryType?.allows_half_day ?? true,
                            requires_attachment: primaryType?.requires_attachment ?? false,
                            prorate_on_join: primaryType?.prorate_on_join ?? true,
                            min_notice_days: primaryType?.min_notice_days ?? 0,
                            allow_past_request: primaryType?.allow_past_request ?? false,
                            allow_future_request: primaryType?.allow_future_request ?? true,
                            is_active: true,
                          },
                        ],
                        rules: [],
                      })
                      setIsModalOpen(true)
                    }}
                  >
                    Edit
                  </button>
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

      <AppDialog
        open={isModalOpen}
        onOpenChange={(open) => {
          setIsModalOpen(open)
          if (!open) resetForm()
        }}
        title={editingId ? 'Edit leave plan' : 'Create leave plan'}
        description="Attach the plan to a leave cycle, then define the primary leave type with accrual and carry-forward rules."
        contentClassName="sm:w-[min(92vw,52rem)]"
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetForm}>
              Cancel
            </button>
            <button type="submit" form="leave-plan-form" className="btn-primary" disabled={createPlanMutation.isPending || updatePlanMutation.isPending}>
              {editingId ? 'Save changes' : 'Save leave plan'}
            </button>
          </div>
        }
      >
        <form id="leave-plan-form" onSubmit={handlePlanSubmit} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="leave-cycle-id">
              Leave cycle
            </label>
            <AppSelect
              id="leave-cycle-id"
              value={planForm.leave_cycle_id}
              onValueChange={(value) => setPlanForm((current) => ({ ...current, leave_cycle_id: value }))}
              options={leaveCycleOptions}
              placeholder="Select leave cycle"
            />
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
          <div>
            <label className="field-label" htmlFor="leave-plan-description">
              Description
            </label>
            <textarea
              id="leave-plan-description"
              className="field-textarea"
              value={planForm.description}
              onChange={(event) => setPlanForm((current) => ({ ...current, description: event.target.value }))}
            />
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
              <AppSelect
                id="credit-frequency"
                value={planForm.leave_types[0].credit_frequency}
                onValueChange={(value) =>
                  setPlanForm((current) => ({
                    ...current,
                    leave_types: [{ ...current.leave_types[0], credit_frequency: value }],
                  }))
                }
                options={creditFrequencyOptions}
              />
            </div>
          </div>
          <AppCheckbox
            id="leave-plan-default"
            checked={planForm.is_default}
            onCheckedChange={(checked) => setPlanForm((current) => ({ ...current, is_default: checked }))}
            label="Default leave plan"
          />
        </form>
      </AppDialog>
    </div>
  )
}
