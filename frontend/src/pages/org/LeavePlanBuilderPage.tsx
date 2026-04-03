import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import {
  useCreateLeavePlan,
  useDepartments,
  useEmployees,
  useLeaveCycles,
  useLeavePlan,
  useLocations,
  useUpdateLeavePlan,
} from '@/hooks/useOrgAdmin'
import {
  useCreateCtLeavePlan,
  useCtOrgConfiguration,
  useCtOrgEmployees,
  useUpdateCtLeavePlan,
} from '@/hooks/useCtOrganisations'
import {
  createDefaultLeavePlanForm,
  EMPLOYMENT_TYPE_OPTIONS,
  LEAVE_CREDIT_FREQUENCY_OPTIONS,
} from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'
import type { LeavePlan } from '@/types/hr'

interface LeaveTypeForm {
  id?: string
  code: string
  name: string
  description: string
  color: string
  is_paid: boolean
  is_loss_of_pay: boolean
  annual_entitlement: string
  credit_frequency: string
  credit_day_of_period: number | null
  prorate_on_join: boolean
  carry_forward_mode: string
  carry_forward_cap: string | null
  max_balance: string | null
  allows_half_day: boolean
  requires_attachment: boolean
  attachment_after_days: string | null
  min_notice_days: number
  max_consecutive_days: number | null
  allow_past_request: boolean
  allow_future_request: boolean
  is_active: boolean
}

interface LeavePlanRuleForm {
  id?: string
  name: string
  priority: number
  is_active: boolean
  department_id: string
  office_location_id: string
  specific_employee_id: string
  employment_type: string
  designation: string
}

interface LeavePlanForm {
  leave_cycle_id: string
  name: string
  description: string
  is_default: boolean
  is_active: boolean
  priority: number
  leave_types: LeaveTypeForm[]
  rules: LeavePlanRuleForm[]
}

const LEAVE_PLAN_STEP_LABELS = ['Plan basics', 'Leave types', 'Applicability'] as const

function createEmptyLeaveType() {
  return {
    id: undefined as string | undefined,
    code: '',
    name: '',
    description: '',
    color: '#2563eb',
    is_paid: true,
    is_loss_of_pay: false,
    annual_entitlement: '0.00',
    credit_frequency: 'YEARLY',
    credit_day_of_period: null,
    prorate_on_join: true,
    carry_forward_mode: 'NONE',
    carry_forward_cap: null,
    max_balance: null,
    allows_half_day: true,
    requires_attachment: false,
    attachment_after_days: null,
    min_notice_days: 0,
    max_consecutive_days: null,
    allow_past_request: false,
    allow_future_request: true,
    is_active: true,
  }
}

function createEmptyRule() {
  return {
    id: undefined as string | undefined,
    name: '',
    priority: 100,
    is_active: true,
    department_id: '',
    office_location_id: '',
    specific_employee_id: '',
    employment_type: '',
    designation: '',
  }
}

function mapPlanToForm(plan: LeavePlan): LeavePlanForm {
  return {
    leave_cycle_id: plan.leave_cycle.id,
    name: plan.name,
    description: plan.description,
    is_default: plan.is_default,
    is_active: plan.is_active,
    priority: plan.priority,
    leave_types: plan.leave_types.map((leaveType) => ({
      id: leaveType.id,
      code: leaveType.code,
      name: leaveType.name,
      description: leaveType.description,
      color: leaveType.color,
      is_paid: leaveType.is_paid,
      is_loss_of_pay: leaveType.is_loss_of_pay,
      annual_entitlement: leaveType.annual_entitlement,
      credit_frequency: leaveType.credit_frequency,
      credit_day_of_period: leaveType.credit_day_of_period ?? null,
      prorate_on_join: leaveType.prorate_on_join,
      carry_forward_mode: leaveType.carry_forward_mode,
      carry_forward_cap: leaveType.carry_forward_cap ?? '',
      max_balance: leaveType.max_balance ?? '',
      allows_half_day: leaveType.allows_half_day,
      requires_attachment: leaveType.requires_attachment,
      attachment_after_days: leaveType.attachment_after_days ?? '',
      min_notice_days: leaveType.min_notice_days,
      max_consecutive_days: leaveType.max_consecutive_days ?? null,
      allow_past_request: leaveType.allow_past_request,
      allow_future_request: leaveType.allow_future_request,
      is_active: leaveType.is_active,
    })),
    rules: plan.rules.map((rule) => ({
      id: rule.id,
      name: rule.name,
      priority: rule.priority,
      is_active: rule.is_active,
      department_id: rule.department ?? '',
      office_location_id: rule.office_location ?? '',
      specific_employee_id: rule.specific_employee ?? '',
      employment_type: rule.employment_type,
      designation: rule.designation,
    })),
  }
}

function buildPayload(form: LeavePlanForm) {
  return {
    ...form,
    leave_types: form.leave_types.map((leaveType) => ({
      ...(leaveType.id ? { id: leaveType.id } : {}),
      ...leaveType,
      code: leaveType.code.trim().toUpperCase(),
      credit_day_of_period: leaveType.credit_day_of_period,
      carry_forward_cap: leaveType.carry_forward_cap,
      max_balance: leaveType.max_balance,
      attachment_after_days: leaveType.attachment_after_days,
      max_consecutive_days: leaveType.max_consecutive_days,
    })),
    rules: form.rules.map((rule) => ({
      ...(rule.id ? { id: rule.id } : {}),
      ...rule,
      department_id: rule.department_id || null,
      office_location_id: rule.office_location_id || null,
      specific_employee_id: rule.specific_employee_id || null,
    })),
  }
}

export function LeavePlanBuilderPage() {
  const navigate = useNavigate()
  const { id, organisationId } = useParams()
  const isEditing = Boolean(id)
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const { data: leaveCycles, isLoading: isCyclesLoading } = useLeaveCycles()
  const { data: departments } = useDepartments(true)
  const { data: locations } = useLocations(true)
  const { data: employees } = useEmployees({ page: 1 })
  const { data: orgPlan, isLoading: isOrgPlanLoading } = useLeavePlan(id ?? '')
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const { data: ctEmployees } = useCtOrgEmployees(organisationId ?? '', { page: 1 }, isCtMode)
  const createMutation = useCreateLeavePlan()
  const updateMutation = useUpdateLeavePlan(id ?? '')
  const createCtMutation = useCreateCtLeavePlan(organisationId ?? '')
  const updateCtMutation = useUpdateCtLeavePlan(organisationId ?? '')
  const [form, setForm] = useState<LeavePlanForm>(createDefaultLeavePlanForm())
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1)
  const plan = isCtMode ? configuration?.leave_plans.find((item) => item.id === id) : orgPlan
  const resolvedLeaveCycles = isCtMode ? configuration?.leave_cycles : leaveCycles
  const resolvedDepartments = isCtMode ? configuration?.departments : departments
  const resolvedLocations = isCtMode ? configuration?.locations : locations
  const resolvedEmployees = isCtMode ? ctEmployees?.results : employees?.results

  useEffect(() => {
    if (plan) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm(mapPlanToForm(plan))
    } else if (!isEditing) {
      setForm(createDefaultLeavePlanForm())
    }
  }, [plan, isEditing])

  const cycleOptions = useMemo(
    () => [
      { value: '', label: 'Select leave cycle' },
      ...(resolvedLeaveCycles ?? []).map((cycle) => ({
        value: cycle.id,
        label: cycle.name,
        hint: `${startCase(cycle.cycle_type)} • ${cycle.active_leave_plan_count} active plan(s)`,
      })),
    ],
    [resolvedLeaveCycles],
  )

  const departmentOptions = useMemo(
    () => [{ value: '', label: 'Any department' }, ...((resolvedDepartments ?? []).map((department) => ({ value: department.id, label: department.name })))],
    [resolvedDepartments],
  )
  const locationOptions = useMemo(
    () => [{ value: '', label: 'Any location' }, ...((resolvedLocations ?? []).map((location) => ({ value: location.id, label: location.name })))],
    [resolvedLocations],
  )
  const employeeOptions = useMemo(
    () => [{ value: '', label: 'Any employee' }, ...((resolvedEmployees ?? []).map((employee) => ({ value: employee.id, label: employee.full_name, hint: employee.designation })))],
    [resolvedEmployees],
  )
  const employmentTypeOptions = useMemo(
    () => [{ value: '', label: 'Any employment type' }, ...EMPLOYMENT_TYPE_OPTIONS.map((value) => ({ value, label: startCase(value) }))],
    [],
  )
  const creditFrequencyOptions = useMemo(
    () => LEAVE_CREDIT_FREQUENCY_OPTIONS.map((value) => ({ value, label: startCase(value) })),
    [],
  )
  const carryForwardOptions = useMemo(
    () => [
      { value: 'NONE', label: 'No carry forward' },
      { value: 'CAPPED', label: 'Carry forward with cap' },
      { value: 'UNLIMITED', label: 'Unlimited carry forward' },
    ],
    [],
  )

  const isLoading = isCtMode
    ? isCtLoading
    : isCyclesLoading || (isEditing && isOrgPlanLoading)
  const isSaving =
    createMutation.isPending ||
    updateMutation.isPending ||
    createCtMutation.isPending ||
    updateCtMutation.isPending

  const savePlan = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})

    if (form.leave_types.length === 0) {
      toast.error('Add at least one leave type before saving this plan.')
      return
    }

    try {
      const payload = buildPayload(form)
      if (isEditing && id) {
        if (isCtMode && organisationId) {
          await updateCtMutation.mutateAsync({ planId: id, payload })
        } else {
          await updateMutation.mutateAsync(payload)
        }
        toast.success('Leave plan updated.')
      } else {
        if (isCtMode && organisationId) {
          await createCtMutation.mutateAsync(payload)
        } else {
          await createMutation.mutateAsync(payload)
        }
        toast.success('Leave plan created.')
      }
      navigate(`${basePath}/leave-plans`)
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
        <SkeletonTable rows={10} />
      </div>
    )
  }

  return (
    <form className="space-y-6" onSubmit={savePlan}>
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • Leave configuration' : 'Leave configuration'}
        title={isEditing ? 'Edit leave plan' : 'Create leave plan'}
        description="Build the plan step by step: define the policy, configure leave types, then validate applicability before saving."
        actions={
          <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/leave-plans`)}>
            Back to plans
          </button>
        }
      />

      <nav aria-label="Leave plan progress" className="rounded-[24px] border border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] px-5 py-4">
        <ol className="grid gap-3 md:grid-cols-3">
          {LEAVE_PLAN_STEP_LABELS.map((label, index) => {
            const step = (index + 1) as 1 | 2 | 3
            const isComplete = step < currentStep
            const isCurrent = step === currentStep
            return (
              <li key={label} className="flex items-center gap-3">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold ${
                    isComplete
                      ? 'border-[hsl(var(--brand))] bg-[hsl(var(--brand))] text-[hsl(var(--brand-foreground))]'
                      : isCurrent
                        ? 'border-[hsl(var(--brand))] text-[hsl(var(--brand))]'
                        : 'border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]'
                  }`}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isComplete ? '✓' : step}
                </div>
                <div>
                  <p className={`text-sm font-semibold ${isCurrent ? 'text-[hsl(var(--foreground-strong))]' : 'text-[hsl(var(--muted-foreground))]'}`}>
                    {label}
                  </p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">Step {step} of {LEAVE_PLAN_STEP_LABELS.length}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </nav>

      {currentStep === 1 ? (
      <SectionCard title="Plan basics" description="Anchor the plan to a leave cycle and define whether it is the default active policy.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="field-label" htmlFor="leave-plan-cycle">
              Leave cycle
            </label>
            <AppSelect
              id="leave-plan-cycle"
              value={form.leave_cycle_id}
              onValueChange={(value) => setForm((current) => ({ ...current, leave_cycle_id: value }))}
              options={cycleOptions}
              placeholder="Select leave cycle"
            />
            <FieldErrorText message={fieldErrors.leave_cycle_id} />
          </div>
          <div>
            <label className="field-label" htmlFor="leave-plan-priority">
              Priority
            </label>
            <input
              id="leave-plan-priority"
              type="number"
              min={0}
              className="field-input"
              value={form.priority}
              onChange={(event) => setForm((current) => ({ ...current, priority: Number(event.target.value || 0) }))}
            />
            <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">Lower priorities are evaluated first when multiple rules could apply.</p>
          </div>
          <div>
            <label className="field-label" htmlFor="leave-plan-name">
              Plan name
            </label>
            <input
              id="leave-plan-name"
              className="field-input"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
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
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </div>
        </div>
        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          <AppCheckbox
            checked={form.is_default}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))}
            label="Default plan"
            description="The default plan applies whenever no more specific applicability rule wins."
          />
          <AppCheckbox
            checked={form.is_active}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_active: checked }))}
            label="Active plan"
            description="Inactive plans stay visible for history but stop being used for new assignments."
          />
        </div>
      </SectionCard>
      ) : null}

      {currentStep === 2 ? (
      <SectionCard
        title="Leave types"
        description="Bundle multiple leave types into one policy and define accrual, balance, attachment, and request constraints for each one."
        action={
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setForm((current) => ({ ...current, leave_types: [...current.leave_types, createEmptyLeaveType()] }))}
          >
            Add leave type
          </button>
        }
      >
        <div className="space-y-4">
          {form.leave_types.map((leaveType, index) => (
            <div key={leaveType.id ?? `leave-type-${index}`} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">
                    {leaveType.name || `Leave type ${index + 1}`}
                  </p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Configure entitlement, accrual, carry forward, and request restrictions.
                  </p>
                </div>
                {form.leave_types.length > 1 ? (
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }
                  >
                    Remove
                  </button>
                ) : null}
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <div>
                  <label className="field-label" htmlFor={`leave-type-name-${index}`}>
                    Name
                  </label>
                  <input
                    id={`leave-type-name-${index}`}
                    className="field-input"
                    value={leaveType.name}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, name: event.target.value } : item,
                        ),
                      }))
                    }
                  />
                  <FieldErrorText message={fieldErrors[`leave_types.${index}.name`]} />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-code-${index}`}>
                    Code
                  </label>
                  <input
                    id={`leave-type-code-${index}`}
                    className="field-input"
                    value={leaveType.code}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, code: event.target.value.toUpperCase() } : item,
                        ),
                      }))
                    }
                  />
                  <FieldErrorText message={fieldErrors[`leave_types.${index}.code`]} />
                </div>
                <div className="xl:col-span-2">
                  <label className="field-label" htmlFor={`leave-type-description-${index}`}>
                    Description
                  </label>
                  <textarea
                    id={`leave-type-description-${index}`}
                    className="field-textarea"
                    value={leaveType.description}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, description: event.target.value } : item,
                        ),
                      }))
                    }
                  />
                </div>
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-4">
                <div>
                  <label className="field-label" htmlFor={`leave-type-entitlement-${index}`}>
                    Annual entitlement
                  </label>
                  <input
                    id={`leave-type-entitlement-${index}`}
                    type="number"
                    step="0.25"
                    className="field-input"
                    value={leaveType.annual_entitlement}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, annual_entitlement: event.target.value } : item,
                        ),
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="field-label">Credit frequency</label>
                  <AppSelect
                    value={leaveType.credit_frequency}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, credit_frequency: value } : item,
                        ),
                      }))
                    }
                    options={creditFrequencyOptions}
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-credit-day-${index}`}>
                    Credit day of period
                  </label>
                  <input
                    id={`leave-type-credit-day-${index}`}
                    type="number"
                    min={1}
                    max={31}
                    className="field-input"
                    value={leaveType.credit_day_of_period ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, credit_day_of_period: event.target.value === '' ? null : Number(event.target.value) }
                            : item,
                        ),
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-color-${index}`}>
                    Calendar color
                  </label>
                  <input
                    id={`leave-type-color-${index}`}
                    type="color"
                    className="field-input h-[3.25rem]"
                    value={leaveType.color}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, color: event.target.value } : item,
                        ),
                      }))
                    }
                  />
                </div>
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-4">
                <div>
                  <label className="field-label">Carry forward mode</label>
                  <AppSelect
                    value={leaveType.carry_forward_mode}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, carry_forward_mode: value } : item,
                        ),
                      }))
                    }
                    options={carryForwardOptions}
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-carry-cap-${index}`}>
                    Carry forward cap
                  </label>
                  <input
                    id={`leave-type-carry-cap-${index}`}
                    type="number"
                    step="0.25"
                    className="field-input"
                    value={leaveType.carry_forward_cap ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, carry_forward_cap: event.target.value === '' ? null : event.target.value } : item,
                        ),
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-max-balance-${index}`}>
                    Max balance
                  </label>
                  <input
                    id={`leave-type-max-balance-${index}`}
                    type="number"
                    step="0.25"
                    className="field-input"
                    value={leaveType.max_balance ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, max_balance: event.target.value === '' ? null : event.target.value } : item,
                        ),
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-max-consecutive-${index}`}>
                    Max consecutive days
                  </label>
                  <input
                    id={`leave-type-max-consecutive-${index}`}
                    type="number"
                    min={1}
                    className="field-input"
                    value={leaveType.max_consecutive_days ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, max_consecutive_days: event.target.value === '' ? null : Number(event.target.value) } : item,
                        ),
                      }))
                    }
                  />
                </div>
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-3">
                <div>
                  <label className="field-label" htmlFor={`leave-type-notice-${index}`}>
                    Minimum notice days
                  </label>
                  <input
                    id={`leave-type-notice-${index}`}
                    type="number"
                    min={0}
                    className="field-input"
                    value={leaveType.min_notice_days}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, min_notice_days: Number(event.target.value || 0) } : item,
                        ),
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="field-label" htmlFor={`leave-type-attachment-after-${index}`}>
                    Attachment required after days
                  </label>
                  <input
                    id={`leave-type-attachment-after-${index}`}
                    type="number"
                    step="0.25"
                    className="field-input"
                    value={leaveType.attachment_after_days ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, attachment_after_days: event.target.value === '' ? null : event.target.value } : item,
                        ),
                      }))
                    }
                  />
                </div>
                <div className="grid gap-3">
                  <AppCheckbox
                    checked={leaveType.is_active}
                    onCheckedChange={(checked) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, is_active: checked } : item,
                        ),
                      }))
                    }
                    label="Active leave type"
                  />
                  <AppCheckbox
                    checked={leaveType.prorate_on_join}
                    onCheckedChange={(checked) =>
                      setForm((current) => ({
                        ...current,
                        leave_types: current.leave_types.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, prorate_on_join: checked } : item,
                        ),
                      }))
                    }
                    label="Prorate entitlement on join"
                  />
                </div>
              </div>

              <div className="mt-5 grid gap-3 xl:grid-cols-3">
                <AppCheckbox
                  checked={leaveType.is_paid}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      leave_types: current.leave_types.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, is_paid: checked } : item,
                      ),
                    }))
                  }
                  label="Paid leave"
                />
                <AppCheckbox
                  checked={leaveType.is_loss_of_pay}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      leave_types: current.leave_types.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, is_loss_of_pay: checked } : item,
                      ),
                    }))
                  }
                  label="Loss of pay"
                />
                <AppCheckbox
                  checked={leaveType.allows_half_day}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      leave_types: current.leave_types.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, allows_half_day: checked } : item,
                      ),
                    }))
                  }
                  label="Allow half-day requests"
                />
                <AppCheckbox
                  checked={leaveType.requires_attachment}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      leave_types: current.leave_types.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, requires_attachment: checked } : item,
                      ),
                    }))
                  }
                  label="Require attachment"
                />
                <AppCheckbox
                  checked={leaveType.allow_past_request}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      leave_types: current.leave_types.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, allow_past_request: checked } : item,
                      ),
                    }))
                  }
                  label="Allow past-dated requests"
                />
                <AppCheckbox
                  checked={leaveType.allow_future_request}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      leave_types: current.leave_types.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, allow_future_request: checked } : item,
                      ),
                    }))
                  }
                  label="Allow future requests"
                />
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
      ) : null}

      {currentStep === 3 ? (
      <>
      <SectionCard
        title="Applicability rules"
        description="Prioritise targeted rules by department, location, employee, or workforce attributes. Empty filters behave as catch-all criteria."
        action={
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setForm((current) => ({ ...current, rules: [...current.rules, createEmptyRule()] }))}
          >
            Add rule
          </button>
        }
      >
        {form.rules.length === 0 ? (
          <div className="surface-muted rounded-[20px] px-4 py-4 text-sm text-[hsl(var(--muted-foreground))]">
            This plan currently has no targeted applicability rules. It will rely on the default-plan setting and priority ordering instead.
          </div>
        ) : (
          <div className="space-y-4">
            {form.rules.map((rule, index) => (
              <div key={rule.id ?? `leave-plan-rule-${index}`} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{rule.name || `Rule ${index + 1}`}</p>
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Use priority and matching filters to target specific employee cohorts.</p>
                  </div>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }
                  >
                    Remove
                  </button>
                </div>

                <div className="mt-4 grid gap-4 xl:grid-cols-3">
                  <div>
                    <label className="field-label" htmlFor={`rule-name-${index}`}>
                      Rule name
                    </label>
                    <input
                      id={`rule-name-${index}`}
                      className="field-input"
                      value={rule.name}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, name: event.target.value } : item,
                          ),
                        }))
                      }
                    />
                    <FieldErrorText message={fieldErrors[`rules.${index}.name`]} />
                  </div>
                  <div>
                    <label className="field-label" htmlFor={`rule-priority-${index}`}>
                      Priority
                    </label>
                    <input
                      id={`rule-priority-${index}`}
                      type="number"
                      min={0}
                      className="field-input"
                      value={rule.priority}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, priority: Number(event.target.value || 0) } : item,
                          ),
                        }))
                      }
                    />
                  </div>
                  <div className="flex items-end">
                    <AppCheckbox
                      checked={rule.is_active}
                      onCheckedChange={(checked) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, is_active: checked } : item,
                          ),
                        }))
                      }
                      label="Active rule"
                    />
                  </div>
                  <div>
                    <label className="field-label">Department</label>
                    <AppSelect
                      value={rule.department_id}
                      onValueChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, department_id: value } : item,
                          ),
                        }))
                      }
                      options={departmentOptions}
                    />
                  </div>
                  <div>
                    <label className="field-label">Location</label>
                    <AppSelect
                      value={rule.office_location_id}
                      onValueChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, office_location_id: value } : item,
                          ),
                        }))
                      }
                      options={locationOptions}
                    />
                  </div>
                  <div>
                    <label className="field-label">Specific employee</label>
                    <AppSelect
                      value={rule.specific_employee_id}
                      onValueChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, specific_employee_id: value } : item,
                          ),
                        }))
                      }
                      options={employeeOptions}
                    />
                  </div>
                  <div>
                    <label className="field-label">Employment type</label>
                    <AppSelect
                      value={rule.employment_type}
                      onValueChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, employment_type: value } : item,
                          ),
                        }))
                      }
                      options={employmentTypeOptions}
                    />
                  </div>
                  <div className="xl:col-span-2">
                    <label className="field-label" htmlFor={`rule-designation-${index}`}>
                      Designation
                    </label>
                    <input
                      id={`rule-designation-${index}`}
                      className="field-input"
                      value={rule.designation}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, designation: event.target.value } : item,
                          ),
                        }))
                      }
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Impact preview" description="Use this summary to sanity-check the policy before you activate or assign it.">
        <div className="grid gap-4 lg:grid-cols-4">
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Leave types</p>
            <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{form.leave_types.length}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Active rules</p>
            <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{form.rules.filter((rule) => rule.is_active).length}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Cycle</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {leaveCycles?.find((cycle) => cycle.id === form.leave_cycle_id)?.name || 'Not selected'}
            </p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {plan ? formatDateTime(plan.modified_at) : 'New draft'}
            </p>
          </div>
        </div>
      </SectionCard>
      </>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] px-5 py-4">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setCurrentStep((step) => Math.max(1, step - 1) as 1 | 2 | 3)}
          disabled={currentStep === 1}
        >
          Back
        </button>
        {currentStep < 3 ? (
          <button
            type="button"
            className="btn-primary"
            onClick={() => setCurrentStep((step) => Math.min(3, step + 1) as 1 | 2 | 3)}
          >
            Next
          </button>
        ) : (
          <button type="submit" className="btn-primary" disabled={isSaving}>
            {isSaving ? 'Saving...' : isEditing ? 'Save changes' : 'Create leave plan'}
          </button>
        )}
      </div>
    </form>
  )
}
