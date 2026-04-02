import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCreateLeaveCycle,
  useLeaveCycles,
  useUpdateLeaveCycle,
} from '@/hooks/useOrgAdmin'
import {
  useCreateCtLeaveCycle,
  useCtOrgConfiguration,
  useUpdateCtLeaveCycle,
} from '@/hooks/useCtOrganisations'
import { createDefaultLeaveCycleForm, LEAVE_CYCLE_TYPE_OPTIONS } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'

function getCycleWindowLabel(cycleType: string, startMonth: number, startDay: number) {
  if (cycleType === 'CALENDAR_YEAR') return '01 Jan -> 31 Dec'
  if (cycleType === 'FINANCIAL_YEAR') return '01 Apr -> 31 Mar'
  if (cycleType === 'EMPLOYEE_JOINING_DATE') return 'Based on employee joining date'
  return `Starts every year on ${String(startDay).padStart(2, '0')}/${String(startMonth).padStart(2, '0')}`
}

export function LeaveCyclesPage() {
  const navigate = useNavigate()
  const { organisationId } = useParams()
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const { data: cycles, isLoading } = useLeaveCycles()
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const createMutation = useCreateLeaveCycle()
  const createCtMutation = useCreateCtLeaveCycle(organisationId ?? '')
  const [editingId, setEditingId] = useState<string | null>(null)
  const updateMutation = useUpdateLeaveCycle(editingId ?? '')
  const updateCtMutation = useUpdateCtLeaveCycle(organisationId ?? '')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form, setForm] = useState(createDefaultLeaveCycleForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const resolvedCycles = isCtMode ? configuration?.leave_cycles : cycles
  const pageLoading = isCtMode ? isCtLoading : isLoading

  const cycleTypeOptions = useMemo(
    () => LEAVE_CYCLE_TYPE_OPTIONS.map((value) => ({ value, label: startCase(value) })),
    [],
  )

  const resetForm = () => {
    setEditingId(null)
    setForm(createDefaultLeaveCycleForm())
    setFieldErrors({})
    setIsModalOpen(false)
  }

  const saveCycle = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      if (editingId) {
        if (isCtMode && organisationId) {
          await updateCtMutation.mutateAsync({ cycleId: editingId, payload: form })
        } else {
          await updateMutation.mutateAsync(form)
        }
        toast.success('Leave cycle updated.')
      } else {
        if (isCtMode && organisationId) {
          await createCtMutation.mutateAsync(form)
        } else {
          await createMutation.mutateAsync(form)
        }
        toast.success('Leave cycle created.')
      }
      resetForm()
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to save leave cycle.'))
      }
    }
  }

  if (pageLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const activeCycles = resolvedCycles?.filter((cycle) => cycle.is_active) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • Leave configuration' : 'Leave configuration'}
        title="Leave cycles"
        description="Maintain the leave-year structures that plans attach to, with clearer operational visibility than the old thin CRUD form."
        actions={
          <>
            {isCtMode ? (
              <button type="button" className="btn-secondary" onClick={() => navigate(basePath)}>
                Back to organisation
              </button>
            ) : null}
            <button type="button" className="btn-primary" onClick={() => setIsModalOpen(true)}>
              Add leave cycle
            </button>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-4">
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Configured cycles</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{resolvedCycles?.length ?? 0}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Active cycles</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{activeCycles.length}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Default cycle</p>
          <p className="mt-3 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
            {resolvedCycles?.find((cycle) => cycle.is_default)?.name ?? 'Not configured'}
          </p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Attached plans</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
            {(resolvedCycles ?? []).reduce((sum, cycle) => sum + cycle.leave_plan_count, 0)}
          </p>
        </div>
      </div>

      <SectionCard title="Cycle catalogue" description="Leave cycles stay lightweight objects, but the page now shows what each one is carrying operationally.">
        <div className="space-y-4">
          {(resolvedCycles ?? []).map((cycle) => (
            <div key={cycle.id} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{cycle.name}</p>
                    {cycle.is_default ? <StatusBadge tone="success">Default</StatusBadge> : null}
                    <StatusBadge tone={cycle.is_active ? 'info' : 'neutral'}>{cycle.is_active ? 'Active' : 'Inactive'}</StatusBadge>
                  </div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">{startCase(cycle.cycle_type)}</p>
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setEditingId(cycle.id)
                    setForm({
                      name: cycle.name,
                      cycle_type: cycle.cycle_type,
                      start_month: cycle.start_month,
                      start_day: cycle.start_day,
                      is_default: cycle.is_default,
                      is_active: cycle.is_active,
                    })
                    setIsModalOpen(true)
                  }}
                >
                  Edit
                </button>
              </div>

              <div className="mt-5 grid gap-3 xl:grid-cols-4">
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Operational window</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">
                    {getCycleWindowLabel(cycle.cycle_type, cycle.start_month, cycle.start_day)}
                  </p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Attached plans</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{cycle.leave_plan_count}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Active plans</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{cycle.active_leave_plan_count}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(cycle.modified_at)}</p>
                </div>
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
        title={editingId ? 'Edit leave cycle' : 'Create leave cycle'}
        description="Keep cycle definitions lightweight, but make them explicit enough that leave plans can attach to the right operational year."
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetForm}>
              Cancel
            </button>
            <button
              type="submit"
              form="leave-cycle-form"
              className="btn-primary"
              disabled={
                createMutation.isPending ||
                updateMutation.isPending ||
                createCtMutation.isPending ||
                updateCtMutation.isPending
              }
            >
              {editingId ? 'Save changes' : 'Save cycle'}
            </button>
          </div>
        }
      >
        <form id="leave-cycle-form" onSubmit={saveCycle} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="leave-cycle-name">
              Cycle name
            </label>
            <input
              id="leave-cycle-name"
              className="field-input"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
            <FieldErrorText message={fieldErrors.name} />
          </div>
          <div>
            <label className="field-label">Cycle type</label>
            <AppSelect
              value={form.cycle_type}
              onValueChange={(value) => setForm((current) => ({ ...current, cycle_type: value }))}
              options={cycleTypeOptions}
            />
            <FieldErrorText message={fieldErrors.cycle_type} />
          </div>
          {form.cycle_type === 'CUSTOM_FIXED_START' ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="leave-cycle-month">
                  Start month
                </label>
                <input
                  id="leave-cycle-month"
                  type="number"
                  min={1}
                  max={12}
                  className="field-input"
                  value={form.start_month}
                  onChange={(event) => setForm((current) => ({ ...current, start_month: Number(event.target.value || 1) }))}
                />
              </div>
              <div>
                <label className="field-label" htmlFor="leave-cycle-day">
                  Start day
                </label>
                <input
                  id="leave-cycle-day"
                  type="number"
                  min={1}
                  max={31}
                  className="field-input"
                  value={form.start_day}
                  onChange={(event) => setForm((current) => ({ ...current, start_day: Number(event.target.value || 1) }))}
                />
              </div>
            </div>
          ) : null}
          <AppCheckbox
            checked={form.is_default}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))}
            label="Default cycle"
          />
          <AppCheckbox
            checked={form.is_active}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_active: checked }))}
            label="Active cycle"
          />
        </form>
      </AppDialog>
    </div>
  )
}
