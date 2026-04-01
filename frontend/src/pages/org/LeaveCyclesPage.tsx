import { useState } from 'react'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useCreateLeaveCycle, useLeaveCycles } from '@/hooks/useOrgAdmin'
import { createDefaultLeaveCycleForm, LEAVE_CYCLE_TYPE_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'

export function LeaveCyclesPage() {
  const { data: cycles, isLoading } = useLeaveCycles()
  const createCycleMutation = useCreateLeaveCycle()
  const [cycleForm, setCycleForm] = useState(createDefaultLeaveCycleForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handleCycleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createCycleMutation.mutateAsync(cycleForm)
      toast.success('Leave cycle created.')
      setCycleForm(createDefaultLeaveCycleForm())
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to create leave cycle.'))
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
        title="Leave cycles"
        description="Define the leave year separately from leave-plan entitlements so policy changes stay readable and deliberate."
      />

      <div className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
        <SectionCard title="Create leave cycle" description="Calendar year, financial year, and custom cycles are all supported by policy.">
          <form onSubmit={handleCycleSubmit} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="leave-cycle-name">
                Cycle name
              </label>
              <input
                id="leave-cycle-name"
                className="field-input"
                value={cycleForm.name}
                onChange={(event) => setCycleForm((current) => ({ ...current, name: event.target.value }))}
                required
              />
              <FieldErrorText message={fieldErrors.name} />
            </div>
            <div>
              <label className="field-label" htmlFor="leave-cycle-type">
                Cycle type
              </label>
              <AppSelect
                id="leave-cycle-type"
                value={cycleForm.cycle_type}
                onValueChange={(value) => setCycleForm((current) => ({ ...current, cycle_type: value }))}
                options={LEAVE_CYCLE_TYPE_OPTIONS.map((type) => ({
                  value: type,
                  label: type.replace(/_/g, ' '),
                }))}
              />
              <FieldErrorText message={fieldErrors.cycle_type} />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="start-month">
                  Start month
                </label>
                <input
                  id="start-month"
                  className="field-input"
                  type="number"
                  min={1}
                  max={12}
                  value={cycleForm.start_month}
                  onChange={(event) => setCycleForm((current) => ({ ...current, start_month: Number(event.target.value) }))}
                />
              </div>
              <div>
                <label className="field-label" htmlFor="start-day">
                  Start day
                </label>
                <input
                  id="start-day"
                  className="field-input"
                  type="number"
                  min={1}
                  max={31}
                  value={cycleForm.start_day}
                  onChange={(event) => setCycleForm((current) => ({ ...current, start_day: Number(event.target.value) }))}
                />
              </div>
            </div>
            <AppCheckbox
              checked={cycleForm.is_default}
              onCheckedChange={(checked) => setCycleForm((current) => ({ ...current, is_default: checked }))}
              label="Default leave cycle"
              description="This cycle becomes the default option for leave plans that do not specify another leave year."
            />
            <button type="submit" className="btn-primary" disabled={createCycleMutation.isPending}>
              Save leave cycle
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Configured leave cycles" description="Keep one default cycle, then add exception cycles only when the organisation genuinely needs them.">
          <div className="space-y-3">
            {cycles?.map((cycle) => (
              <div key={cycle.id} className="surface-muted rounded-[20px] px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{cycle.cycle_type.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="text-sm text-[hsl(var(--muted-foreground))]">
                    {cycle.is_default ? 'Default' : 'Secondary'} • starts {cycle.start_month}/{cycle.start_day}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
