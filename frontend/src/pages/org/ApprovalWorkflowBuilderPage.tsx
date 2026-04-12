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
  useApprovalWorkflow,
  useApprovalWorkflowCatalog,
  useCreateApprovalWorkflow,
  useDepartments,
  useEmployees,
  useLeavePlans,
  useLocations,
  useSimulateApprovalWorkflow,
  useUpdateApprovalWorkflow,
} from '@/hooks/useOrgAdmin'
import {
  useCreateCtApprovalWorkflow,
  useCtOrgConfiguration,
  useCtOrgEmployees,
  useUpdateCtApprovalWorkflow,
} from '@/hooks/useCtOrganisations'
import {
  APPROVAL_APPROVER_TYPE_OPTIONS,
  APPROVAL_FALLBACK_TYPE_OPTIONS,
  APPROVAL_REQUEST_KIND_OPTIONS,
  APPROVAL_STAGE_MODE_OPTIONS,
  createDefaultApprovalWorkflow,
  EMPLOYMENT_TYPE_OPTIONS,
} from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'
import { formatDateTime, startCase } from '@/lib/format'
import type { ApprovalRequestKind, ApprovalWorkflowConfig, ApprovalWorkflowSimulationResult } from '@/types/hr'

interface WorkflowRuleForm {
  id?: string
  name: string
  request_kind: string
  priority: number
  is_active: boolean
  department_id: string | null
  office_location_id: string | null
  specific_employee_id: string | null
  employment_type: string
  designation: string
  leave_type_id: string | null
  min_amount: string | null
  max_amount: string | null
  grade: string
  band: string
  cost_centre: string
  legal_entity: string
}

interface WorkflowApproverForm {
  id?: string
  approver_type: string
  approver_employee_id?: string | null
  manager_level: number
  role_code: string
}

interface WorkflowStageForm {
  id?: string
  name: string
  sequence: number
  mode: string
  fallback_type: string
  fallback_employee_id?: string | null
  fallback_role_code: string
  reminder_after_hours?: number | null
  escalate_after_hours?: number | null
  escalation_target_type: string
  escalation_employee_id?: string | null
  escalation_role_code: string
  approvers: WorkflowApproverForm[]
}

interface WorkflowForm {
  name: string
  description: string
  is_default: boolean
  default_request_kind: string | null
  is_active: boolean
  rules: WorkflowRuleForm[]
  stages: WorkflowStageForm[]
}

interface SimulationForm {
  employee_id: string
  request_kind: ApprovalRequestKind
  amount: string
  grade: string
  band: string
  cost_centre: string
  legal_entity: string
  leave_type_id: string
}

const ROLE_APPROVER_TYPES = new Set(['HR_BUSINESS_PARTNER', 'PAYROLL_ADMIN', 'FINANCE_APPROVER', 'ROLE'])

function createEmptyRule(): WorkflowRuleForm {
  return {
    name: '',
    request_kind: 'LEAVE',
    priority: 100,
    is_active: true,
    department_id: null,
    office_location_id: null,
    specific_employee_id: null,
    employment_type: '',
    designation: '',
    leave_type_id: null,
    min_amount: null,
    max_amount: null,
    grade: '',
    band: '',
    cost_centre: '',
    legal_entity: '',
  }
}

function createEmptyStage(sequence: number): WorkflowStageForm {
  return {
    name: `Stage ${sequence}`,
    sequence,
    mode: 'ALL',
    fallback_type: 'NONE',
    fallback_employee_id: null,
    fallback_role_code: '',
    reminder_after_hours: null,
    escalate_after_hours: null,
    escalation_target_type: 'NONE',
    escalation_employee_id: null,
    escalation_role_code: '',
    approvers: [{ approver_type: 'PRIMARY_ORG_ADMIN', approver_employee_id: null, manager_level: 1, role_code: '' }],
  }
}

function mapWorkflowToForm(workflow: ApprovalWorkflowConfig): WorkflowForm {
  return {
    name: workflow.name,
    description: workflow.description,
    is_default: workflow.is_default,
    default_request_kind: workflow.default_request_kind,
    is_active: workflow.is_active,
    rules: workflow.rules.map((rule) => ({
      id: rule.id,
      name: rule.name,
      request_kind: rule.request_kind,
      priority: rule.priority,
      is_active: rule.is_active,
      department_id: rule.department ?? '',
      office_location_id: rule.office_location ?? '',
      specific_employee_id: rule.specific_employee ?? '',
      employment_type: rule.employment_type,
      designation: rule.designation,
      leave_type_id: rule.leave_type ?? '',
      min_amount: rule.min_amount,
      max_amount: rule.max_amount,
      grade: rule.grade,
      band: rule.band,
      cost_centre: rule.cost_centre,
      legal_entity: rule.legal_entity,
    })),
    stages: workflow.stages.map((stage) => ({
      id: stage.id,
      name: stage.name,
      sequence: stage.sequence,
      mode: stage.mode,
      fallback_type: stage.fallback_type,
      fallback_employee_id: stage.fallback_employee_id,
      fallback_role_code: stage.fallback_role_code,
      reminder_after_hours: stage.reminder_after_hours,
      escalate_after_hours: stage.escalate_after_hours,
      escalation_target_type: stage.escalation_target_type,
      escalation_employee_id: stage.escalation_employee_id,
      escalation_role_code: stage.escalation_role_code,
      approvers: stage.approvers.map((approver) => ({
        id: approver.id,
        approver_type: approver.approver_type,
        approver_employee_id: approver.approver_employee_id,
        manager_level: approver.manager_level,
        role_code: approver.role_code,
      })),
    })),
  }
}

function buildPayload(form: WorkflowForm) {
  return {
    ...form,
    default_request_kind: form.is_default ? form.default_request_kind || null : null,
    rules: form.rules.map((rule) => ({
      ...(rule.id ? { id: rule.id } : {}),
      ...rule,
      department_id: rule.department_id || null,
      office_location_id: rule.office_location_id || null,
      specific_employee_id: rule.specific_employee_id || null,
      leave_type_id: rule.request_kind === 'LEAVE' ? rule.leave_type_id || null : null,
      min_amount: rule.min_amount || null,
      max_amount: rule.max_amount || null,
      grade: rule.grade,
      band: rule.band,
      cost_centre: rule.cost_centre,
      legal_entity: rule.legal_entity,
    })),
    stages: form.stages.map((stage, index) => ({
      ...(stage.id ? { id: stage.id } : {}),
      ...stage,
      sequence: index + 1,
      fallback_employee_id: stage.fallback_employee_id || null,
      fallback_role_code: stage.fallback_type === 'ROLE' ? stage.fallback_role_code : '',
      reminder_after_hours: stage.reminder_after_hours || null,
      escalate_after_hours: stage.escalate_after_hours || null,
      escalation_target_type: stage.escalation_target_type,
      escalation_employee_id: stage.escalation_target_type === 'SPECIFIC_EMPLOYEE' ? stage.escalation_employee_id || null : null,
      escalation_role_code: stage.escalation_target_type === 'ROLE' ? stage.escalation_role_code : '',
      approvers: stage.approvers.map((approver) => ({
        ...(approver.id ? { id: approver.id } : {}),
        approver_type: approver.approver_type,
        approver_employee_id: approver.approver_type === 'SPECIFIC_EMPLOYEE' ? approver.approver_employee_id || null : null,
        manager_level: approver.manager_level,
        role_code: approver.approver_type === 'ROLE' ? approver.role_code : '',
      })),
    })),
  }
}

export function ApprovalWorkflowBuilderPage() {
  const navigate = useNavigate()
  const { id, organisationId } = useParams()
  const isEditing = Boolean(id)
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const { data: orgWorkflow, isLoading } = useApprovalWorkflow(id ?? '', !isCtMode)
  const { data: departments } = useDepartments(true, !isCtMode)
  const { data: locations } = useLocations(true, !isCtMode)
  const { data: employees } = useEmployees({ page: 1 }, !isCtMode)
  const { data: leavePlans } = useLeavePlans(!isCtMode)
  const { data: catalog } = useApprovalWorkflowCatalog(!isCtMode)
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const { data: ctEmployees } = useCtOrgEmployees(organisationId ?? '', { page: 1 }, isCtMode)
  const createMutation = useCreateApprovalWorkflow()
  const updateMutation = useUpdateApprovalWorkflow(id ?? '')
  const createCtMutation = useCreateCtApprovalWorkflow(organisationId ?? '')
  const updateCtMutation = useUpdateCtApprovalWorkflow(organisationId ?? '')
  const simulationMutation = useSimulateApprovalWorkflow()
  const [form, setForm] = useState<WorkflowForm>(createDefaultApprovalWorkflow() as unknown as WorkflowForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [simulationForm, setSimulationForm] = useState<SimulationForm>({
    employee_id: '',
    request_kind: 'LEAVE',
    amount: '',
    grade: '',
    band: '',
    cost_centre: '',
    legal_entity: '',
    leave_type_id: '',
  })
  const [simulationResult, setSimulationResult] = useState<ApprovalWorkflowSimulationResult | null>(null)
  const workflow = isCtMode ? configuration?.approval_workflows.find((item) => item.id === id) : orgWorkflow
  const resolvedDepartments = isCtMode ? configuration?.departments : departments
  const resolvedLocations = isCtMode ? configuration?.locations : locations
  const resolvedEmployees = isCtMode ? ctEmployees?.results : employees?.results
  const resolvedLeavePlans = isCtMode ? configuration?.leave_plans : leavePlans

  useEffect(() => {
    if (workflow) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm(mapWorkflowToForm(workflow))
    } else if (!isEditing) {
      setForm(createDefaultApprovalWorkflow() as unknown as WorkflowForm)
    }
  }, [workflow, isEditing])

  const departmentOptions = useMemo(
    () => [{ value: '', label: 'Any department' }, ...(resolvedDepartments ?? []).map((department) => ({ value: department.id, label: department.name }))],
    [resolvedDepartments],
  )
  const locationOptions = useMemo(
    () => [{ value: '', label: 'Any location' }, ...(resolvedLocations ?? []).map((location) => ({ value: location.id, label: location.name }))],
    [resolvedLocations],
  )
  const employeeOptions = useMemo(
    () => [{ value: '', label: 'Select employee' }, ...(resolvedEmployees ?? []).map((employee) => ({ value: employee.id, label: employee.full_name, hint: employee.designation }))],
    [resolvedEmployees],
  )
  const employmentTypeOptions = useMemo(
    () => [{ value: '', label: 'Any employment type' }, ...EMPLOYMENT_TYPE_OPTIONS.map((value) => ({ value, label: startCase(value) }))],
    [],
  )
  const catalogKindMap = useMemo(
    () => new Map((catalog?.request_kinds ?? []).map((item) => [item.kind, item])),
    [catalog],
  )
  const requestKindMeta = (kind: string) => catalogKindMap.get(kind as ApprovalRequestKind)
  const supportsLeaveTypeRules = (kind: string) => requestKindMeta(kind)?.supports_leave_type_rules ?? kind === 'LEAVE'
  const supportsAmountRules = (kind: string) =>
    requestKindMeta(kind)?.supports_amount_rules ?? ['EXPENSE_CLAIM', 'PAYROLL_PROCESSING', 'SALARY_REVISION', 'PROMOTION'].includes(kind)
  const requestKindOptions = useMemo(
    () =>
      (catalog?.request_kinds ?? APPROVAL_REQUEST_KIND_OPTIONS.map((kind) => ({
        kind,
        label: startCase(kind),
        module: 'Core',
      }))).map((item) => ({ value: item.kind, label: item.label, hint: item.module })),
    [catalog],
  )
  const approverTypeOptions = useMemo(
    () => (catalog?.approver_types ?? APPROVAL_APPROVER_TYPE_OPTIONS).map((value) => ({ value, label: startCase(value) })),
    [catalog],
  )
  const fallbackTypeOptions = useMemo(
    () => (catalog?.fallback_types ?? APPROVAL_FALLBACK_TYPE_OPTIONS).map((value) => ({ value, label: startCase(value) })),
    [catalog],
  )
  const stageModeOptions = useMemo(
    () => (catalog?.stage_modes ?? APPROVAL_STAGE_MODE_OPTIONS).map((value) => ({ value, label: startCase(value) })),
    [catalog],
  )
  const leaveTypeOptions = useMemo(
    () => [
      { value: '', label: 'Any leave type' },
      ...(resolvedLeavePlans ?? []).flatMap((plan) =>
        plan.leave_types.map((leaveType) => ({
          value: leaveType.id,
          label: leaveType.name,
          hint: plan.name,
        })),
      ),
    ],
    [resolvedLeavePlans],
  )

  const runSimulation = async () => {
    if (!simulationForm.employee_id) {
      toast.error('Select an employee before previewing approvers.')
      return
    }
    try {
      const result = await simulationMutation.mutateAsync({
        employee_id: simulationForm.employee_id,
        request_kind: simulationForm.request_kind,
        amount: simulationForm.amount || undefined,
        leave_type_id: simulationForm.leave_type_id || undefined,
        grade: simulationForm.grade,
        band: simulationForm.band,
        cost_centre: simulationForm.cost_centre,
        legal_entity: simulationForm.legal_entity,
      })
      setSimulationResult(result)
    } catch (error) {
      setSimulationResult(null)
      toast.error(getErrorMessage(error, 'Unable to preview approvers.'))
    }
  }

  const saveWorkflow = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      const payload = buildPayload(form)
      if (isEditing && id) {
        if (isCtMode && organisationId) {
          await updateCtMutation.mutateAsync({ workflowId: id, payload })
        } else {
          await updateMutation.mutateAsync(payload)
        }
        toast.success('Workflow updated.')
      } else {
        if (isCtMode && organisationId) {
          await createCtMutation.mutateAsync(payload)
        } else {
          await createMutation.mutateAsync(payload)
        }
        toast.success('Workflow created.')
      }
      navigate(`${basePath}/approval-workflows?tab=workflows`)
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to save approval workflow.'))
      }
    }
  }

  if (isEditing && (isCtMode ? isCtLoading : isLoading)) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={10} />
      </div>
    )
  }

  return (
    <form className="space-y-6" onSubmit={saveWorkflow}>
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • Approvals' : 'Approvals'}
        title={isEditing ? 'Edit workflow' : 'Create workflow'}
        description="Build multi-stage approval routing with request rules, fallback behavior, and approver definitions that are actually visible to admins."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/approval-workflows?tab=workflows`)}>
              Back to approvals
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={
                createMutation.isPending ||
                updateMutation.isPending ||
                createCtMutation.isPending ||
                updateCtMutation.isPending
              }
            >
              {isEditing ? 'Save changes' : 'Create workflow'}
            </button>
          </>
        }
      />

      <SectionCard title="Workflow basics" description="Set the default workflow and keep naming clear so admins understand where this routing will apply.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="field-label" htmlFor="workflow-name">
              Workflow name
            </label>
            <input
              id="workflow-name"
              className="field-input"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
            <FieldErrorText message={fieldErrors.name} />
          </div>
          <div>
            <label className="field-label" htmlFor="workflow-description">
              Description
            </label>
            <textarea
              id="workflow-description"
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
            label="Default workflow"
            description="Defaults now apply to one request type at a time."
          />
          <AppCheckbox
            checked={form.is_active}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_active: checked }))}
            label="Active workflow"
            description="Inactive workflows remain visible but should no longer receive fresh routing."
          />
        </div>
        {form.is_default ? (
          <div className="mt-5 max-w-md">
            <label className="field-label" htmlFor="workflow-default-request-kind">
              Default request kind
            </label>
            <AppSelect
              value={form.default_request_kind ?? ''}
              onValueChange={(value) => setForm((current) => ({ ...current, default_request_kind: value }))}
              options={requestKindOptions}
              placeholder="Select request kind"
            />
            <FieldErrorText message={fieldErrors.default_request_kind} />
          </div>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Routing rules"
        description="Match workflows by request kind, leave type, department, location, employee, or workforce attributes."
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
        <div className="space-y-4">
          {form.rules.map((rule, index) => (
            <div key={rule.id ?? `workflow-rule-${index}`} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{rule.name || `Rule ${index + 1}`}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Each rule can target one cohort or stay generic as a fallback rule.</p>
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
                  <label className="field-label">Rule name</label>
                  <input
                    className="field-input"
                    value={rule.name}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, name: event.target.value } : item)),
                      }))
                    }
                  />
                  <FieldErrorText message={fieldErrors[`rules.${index}.name`]} />
                </div>
                <div>
                  <label className="field-label">Request kind</label>
                  <AppSelect
                    value={rule.request_kind}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) =>
                          itemIndex === index
                            ? {
                                ...item,
                                request_kind: value,
                                leave_type_id: supportsLeaveTypeRules(value) ? item.leave_type_id : null,
                                min_amount: supportsAmountRules(value) ? item.min_amount : null,
                                max_amount: supportsAmountRules(value) ? item.max_amount : null,
                              }
                            : item,
                        ),
                      }))
                    }
                    options={requestKindOptions}
                  />
                </div>
                <div>
                  <label className="field-label">Priority</label>
                  <input
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
                <div>
                  <label className="field-label">Department</label>
                  <AppSelect
                    value={rule.department_id ?? ''}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, department_id: value } : item)),
                      }))
                    }
                    options={departmentOptions}
                  />
                </div>
                <div>
                  <label className="field-label">Location</label>
                  <AppSelect
                    value={rule.office_location_id ?? ''}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, office_location_id: value } : item)),
                      }))
                    }
                    options={locationOptions}
                  />
                </div>
                <div>
                  <label className="field-label">Specific employee</label>
                  <AppSelect
                    value={rule.specific_employee_id ?? ''}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, specific_employee_id: value } : item)),
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
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, employment_type: value } : item)),
                      }))
                    }
                    options={employmentTypeOptions}
                  />
                </div>
                <div>
                  <label className="field-label">Designation</label>
                  <input
                    className="field-input"
                    value={rule.designation}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, designation: event.target.value } : item)),
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="field-label">Leave type</label>
                  <AppSelect
                    value={rule.leave_type_id ?? ''}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, leave_type_id: value } : item)),
                      }))
                    }
                    options={leaveTypeOptions}
                    disabled={!supportsLeaveTypeRules(rule.request_kind)}
                  />
                </div>
                {supportsAmountRules(rule.request_kind) ? (
                  <>
                    <div>
                      <label className="field-label">Minimum amount</label>
                      <input
                        className="field-input"
                        inputMode="decimal"
                        value={rule.min_amount ?? ''}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            rules: current.rules.map((item, itemIndex) =>
                              itemIndex === index ? { ...item, min_amount: event.target.value || null } : item,
                            ),
                          }))
                        }
                        placeholder="Optional"
                      />
                    </div>
                    <div>
                      <label className="field-label">Maximum amount</label>
                      <input
                        className="field-input"
                        inputMode="decimal"
                        value={rule.max_amount ?? ''}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            rules: current.rules.map((item, itemIndex) =>
                              itemIndex === index ? { ...item, max_amount: event.target.value || null } : item,
                            ),
                          }))
                        }
                        placeholder="Optional"
                      />
                    </div>
                  </>
                ) : null}
                {(['grade', 'band', 'cost_centre', 'legal_entity'] as const).map((fieldName) => (
                  <div key={fieldName}>
                    <label className="field-label">{startCase(fieldName)}</label>
                    <input
                      className="field-input"
                      value={rule[fieldName]}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          rules: current.rules.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, [fieldName]: event.target.value } : item,
                          ),
                        }))
                      }
                      placeholder="Any"
                    />
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <AppCheckbox
                  checked={rule.is_active}
                  onCheckedChange={(checked) =>
                    setForm((current) => ({
                      ...current,
                      rules: current.rules.map((item, itemIndex) => (itemIndex === index ? { ...item, is_active: checked } : item)),
                    }))
                  }
                  label="Active rule"
                />
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Approval stages"
        description="Define stage order, stage mode, fallback behavior, and approvers for each level of the workflow."
        action={
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              setForm((current) => ({
                ...current,
                stages: [...current.stages, createEmptyStage(current.stages.length + 1)],
              }))
            }
          >
            Add stage
          </button>
        }
      >
        <div className="space-y-4">
          {form.stages.map((stage, stageIndex) => (
            <div key={stage.id ?? `workflow-stage-${stageIndex}`} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{stage.sequence}. {stage.name || `Stage ${stageIndex + 1}`}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Approvers inside a stage follow the selected ALL or ANY completion mode.</p>
                </div>
                {form.stages.length > 1 ? (
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages
                          .filter((_, itemIndex) => itemIndex !== stageIndex)
                          .map((item, itemIndex) => ({ ...item, sequence: itemIndex + 1 })),
                      }))
                    }
                  >
                    Remove stage
                  </button>
                ) : null}
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-4">
                <div>
                  <label className="field-label">Stage name</label>
                  <input
                    className="field-input"
                    value={stage.name}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) => (itemIndex === stageIndex ? { ...item, name: event.target.value } : item)),
                      }))
                    }
                  />
                  <FieldErrorText message={fieldErrors[`stages.${stageIndex}.name`]} />
                </div>
                <div>
                  <label className="field-label">Sequence</label>
                  <input type="number" className="field-input" value={stageIndex + 1} disabled />
                </div>
                <div>
                  <label className="field-label">Stage mode</label>
                  <AppSelect
                    value={stage.mode}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) => (itemIndex === stageIndex ? { ...item, mode: value } : item)),
                      }))
                    }
                    options={stageModeOptions}
                  />
                </div>
                <div>
                  <label className="field-label">Fallback</label>
                  <AppSelect
                    value={stage.fallback_type}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) =>
                          itemIndex === stageIndex
                            ? {
                                ...item,
                                fallback_type: value,
                                fallback_employee_id: value === 'SPECIFIC_EMPLOYEE' ? item.fallback_employee_id : null,
                                fallback_role_code: value === 'ROLE' ? item.fallback_role_code : '',
                              }
                            : item,
                        ),
                      }))
                    }
                    options={fallbackTypeOptions}
                  />
                </div>
                {stage.fallback_type === 'ROLE' ? (
                  <div>
                    <label className="field-label">Fallback role code</label>
                    <input
                      className="field-input"
                      value={stage.fallback_role_code}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === stageIndex ? { ...item, fallback_role_code: event.target.value } : item,
                          ),
                        }))
                      }
                      placeholder="ORG_HR_ADMIN"
                    />
                  </div>
                ) : null}
                {stage.fallback_type === 'SPECIFIC_EMPLOYEE' ? (
                  <div className="xl:col-span-2">
                    <label className="field-label">Fallback employee</label>
                    <AppSelect
                      value={stage.fallback_employee_id ?? ''}
                      onValueChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === stageIndex ? { ...item, fallback_employee_id: value } : item,
                          ),
                        }))
                      }
                      options={employeeOptions}
                    />
                  </div>
                ) : null}
                <div>
                  <label className="field-label">Reminder after hours</label>
                  <input
                    type="number"
                    className="field-input"
                    value={stage.reminder_after_hours ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) =>
                          itemIndex === stageIndex
                            ? {
                                ...item,
                                reminder_after_hours: event.target.value ? Number(event.target.value) : null,
                              }
                            : item,
                        ),
                      }))
                    }
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="field-label">Escalate after hours</label>
                  <input
                    type="number"
                    className="field-input"
                    value={stage.escalate_after_hours ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) =>
                          itemIndex === stageIndex
                            ? {
                                ...item,
                                escalate_after_hours: event.target.value ? Number(event.target.value) : null,
                              }
                            : item,
                        ),
                      }))
                    }
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="field-label">Escalation target</label>
                  <AppSelect
                    value={stage.escalation_target_type}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) =>
                          itemIndex === stageIndex
                            ? {
                                ...item,
                                escalation_target_type: value,
                                escalation_employee_id: value === 'SPECIFIC_EMPLOYEE' ? item.escalation_employee_id : null,
                                escalation_role_code: value === 'ROLE' ? item.escalation_role_code : '',
                              }
                            : item,
                        ),
                      }))
                    }
                    options={fallbackTypeOptions}
                  />
                </div>
                {stage.escalation_target_type === 'SPECIFIC_EMPLOYEE' ? (
                  <div>
                    <label className="field-label">Escalation employee</label>
                    <AppSelect
                      value={stage.escalation_employee_id ?? ''}
                      onValueChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === stageIndex ? { ...item, escalation_employee_id: value } : item,
                          ),
                        }))
                      }
                      options={employeeOptions}
                    />
                  </div>
                ) : null}
                {stage.escalation_target_type === 'ROLE' ? (
                  <div>
                    <label className="field-label">Escalation role code</label>
                    <input
                      className="field-input"
                      value={stage.escalation_role_code}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          stages: current.stages.map((item, itemIndex) =>
                            itemIndex === stageIndex ? { ...item, escalation_role_code: event.target.value } : item,
                          ),
                        }))
                      }
                      placeholder="ORG_HR_ADMIN"
                    />
                  </div>
                ) : null}
              </div>

              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Approvers</p>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        stages: current.stages.map((item, itemIndex) =>
                          itemIndex === stageIndex
                            ? {
                                ...item,
                                approvers: [...item.approvers, { approver_type: 'SPECIFIC_EMPLOYEE', approver_employee_id: null, manager_level: 1, role_code: '' }],
                              }
                            : item,
                        ),
                      }))
                    }
                  >
                    Add approver
                  </button>
                </div>
                {stage.approvers.map((approver, approverIndex) => (
                  <div key={approver.id ?? `stage-${stageIndex}-approver-${approverIndex}`} className="surface-shell rounded-[18px] p-4">
                    <div className="grid gap-4 xl:grid-cols-3">
                      <div>
                        <label className="field-label">Approver type</label>
                        <AppSelect
                          value={approver.approver_type}
                          onValueChange={(value) =>
                            setForm((current) => ({
                              ...current,
                              stages: current.stages.map((stageItem, stageItemIndex) =>
                                stageItemIndex === stageIndex
                                  ? {
                                      ...stageItem,
                                      approvers: stageItem.approvers.map((approverItem, approverItemIndex) =>
                                        approverItemIndex === approverIndex
                                          ? {
                                              ...approverItem,
                                              approver_type: value,
                                              approver_employee_id: value === 'SPECIFIC_EMPLOYEE' ? approverItem.approver_employee_id : null,
                                              role_code: ROLE_APPROVER_TYPES.has(value) ? approverItem.role_code : '',
                                            }
                                          : approverItem,
                                      ),
                                    }
                                  : stageItem,
                              ),
                            }))
                          }
                          options={approverTypeOptions}
                        />
                      </div>
                      <div>
                        <label className="field-label">Specific employee</label>
                        <AppSelect
                          value={approver.approver_employee_id ?? ''}
                          onValueChange={(value) =>
                            setForm((current) => ({
                              ...current,
                              stages: current.stages.map((stageItem, stageItemIndex) =>
                                stageItemIndex === stageIndex
                                  ? {
                                      ...stageItem,
                                      approvers: stageItem.approvers.map((approverItem, approverItemIndex) =>
                                        approverItemIndex === approverIndex
                                          ? { ...approverItem, approver_employee_id: value }
                                          : approverItem,
                                      ),
                                    }
                                  : stageItem,
                              ),
                            }))
                          }
                          options={employeeOptions}
                          disabled={approver.approver_type !== 'SPECIFIC_EMPLOYEE'}
                        />
                      </div>
                      <div>
                        <label className="field-label">Manager level</label>
                        <input
                          type="number"
                          min={1}
                          className="field-input"
                          value={approver.manager_level}
                          disabled={approver.approver_type !== 'NTH_LEVEL_MANAGER'}
                          onChange={(event) =>
                            setForm((current) => ({
                              ...current,
                              stages: current.stages.map((stageItem, stageItemIndex) =>
                                stageItemIndex === stageIndex
                                  ? {
                                      ...stageItem,
                                      approvers: stageItem.approvers.map((approverItem, approverItemIndex) =>
                                        approverItemIndex === approverIndex
                                          ? { ...approverItem, manager_level: Number(event.target.value || 1) }
                                          : approverItem,
                                      ),
                                    }
                                  : stageItem,
                              ),
                            }))
                          }
                        />
                      </div>
                      <div>
                        <label className="field-label">Role code</label>
                        <input
                          className="field-input"
                          value={approver.role_code}
                          disabled={!ROLE_APPROVER_TYPES.has(approver.approver_type)}
                          onChange={(event) =>
                            setForm((current) => ({
                              ...current,
                              stages: current.stages.map((stageItem, stageItemIndex) =>
                                stageItemIndex === stageIndex
                                  ? {
                                      ...stageItem,
                                      approvers: stageItem.approvers.map((approverItem, approverItemIndex) =>
                                        approverItemIndex === approverIndex
                                          ? { ...approverItem, role_code: event.target.value }
                                          : approverItem,
                                      ),
                                    }
                                  : stageItem,
                              ),
                            }))
                          }
                          placeholder="Optional for seeded roles"
                        />
                      </div>
                      <div className="flex items-end justify-end">
                        {stage.approvers.length > 1 ? (
                          <button
                            type="button"
                            className="btn-danger"
                            onClick={() =>
                              setForm((current) => ({
                                ...current,
                                stages: current.stages.map((stageItem, stageItemIndex) =>
                                  stageItemIndex === stageIndex
                                    ? {
                                        ...stageItem,
                                        approvers: stageItem.approvers.filter((_, approverItemIndex) => approverItemIndex !== approverIndex),
                                      }
                                    : stageItem,
                                ),
                              }))
                            }
                          >
                            Remove approver
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Workflow preview" description="This quick view helps you catch routing mistakes before employees start hitting the workflow.">
        <div className="grid gap-4 xl:grid-cols-4">
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Rules</p>
            <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{form.rules.length}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Stages</p>
            <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{form.stages.length}</p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Default coverage</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {form.is_default ? startCase(form.default_request_kind ?? 'UNSET') : 'Custom only'}
            </p>
          </div>
          <div className="surface-muted rounded-[20px] px-4 py-4">
            <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
            <p className="mt-2 text-lg font-semibold text-[hsl(var(--foreground-strong))]">
              {workflow ? formatDateTime(workflow.modified_at) : 'New draft'}
            </p>
          </div>
        </div>
      </SectionCard>

      {!isCtMode ? (
        <SectionCard title="Approver preview" description="Check the active workflow path for a real employee before publishing changes.">
          <div className="grid gap-4 xl:grid-cols-3">
            <div>
              <label className="field-label">Employee</label>
              <AppSelect
                value={simulationForm.employee_id}
                onValueChange={(value) => setSimulationForm((current) => ({ ...current, employee_id: value }))}
                options={employeeOptions}
                searchable
              />
            </div>
            <div>
              <label className="field-label">Request kind</label>
              <AppSelect
                value={simulationForm.request_kind}
                onValueChange={(value) => setSimulationForm((current) => ({ ...current, request_kind: value as ApprovalRequestKind }))}
                options={requestKindOptions}
                searchable
              />
            </div>
            {supportsAmountRules(simulationForm.request_kind) ? (
              <div>
                <label className="field-label">Amount</label>
                <input
                  className="field-input"
                  inputMode="decimal"
                  value={simulationForm.amount}
                  onChange={(event) => setSimulationForm((current) => ({ ...current, amount: event.target.value }))}
                  placeholder="Optional"
                />
              </div>
            ) : null}
            {supportsLeaveTypeRules(simulationForm.request_kind) ? (
              <div>
                <label className="field-label">Leave type</label>
                <AppSelect
                  value={simulationForm.leave_type_id}
                  onValueChange={(value) => setSimulationForm((current) => ({ ...current, leave_type_id: value }))}
                  options={leaveTypeOptions}
                />
              </div>
            ) : null}
            {(['grade', 'band', 'cost_centre', 'legal_entity'] as const).map((fieldName) => (
              <div key={fieldName}>
                <label className="field-label">{startCase(fieldName)}</label>
                <input
                  className="field-input"
                  value={simulationForm[fieldName]}
                  onChange={(event) => setSimulationForm((current) => ({ ...current, [fieldName]: event.target.value }))}
                  placeholder="Optional"
                />
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-end">
            <button type="button" className="btn-secondary" disabled={simulationMutation.isPending} onClick={() => void runSimulation()}>
              {simulationMutation.isPending ? 'Previewing...' : 'Preview approvers'}
            </button>
          </div>
          {simulationResult ? (
            <div className="mt-5 space-y-3">
              <div className="surface-muted rounded-[18px] px-4 py-3">
                <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">{simulationResult.workflow_name}</p>
                <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">{simulationResult.source}</p>
              </div>
              {simulationResult.stages.map((stage) => (
                <div key={`${stage.sequence}-${stage.name}`} className="surface-shell rounded-[18px] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-medium text-[hsl(var(--foreground-strong))]">
                      {stage.sequence}. {stage.name}
                    </p>
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">{stage.mode}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {stage.approvers.map((approver) => (
                      <span key={approver.user_id} className="rounded-full bg-[hsl(var(--brand)/0.12)] px-3 py-1 text-sm text-[hsl(var(--foreground-strong))]">
                        {approver.name}
                      </span>
                    ))}
                    {stage.approvers.length === 0 ? (
                      <span className="text-sm text-[hsl(var(--danger))]">No approver resolved.</span>
                    ) : null}
                  </div>
                  {stage.warnings.length ? (
                    <ul className="mt-3 list-disc pl-5 text-sm text-[hsl(var(--warning))]">
                      {stage.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </SectionCard>
      ) : null}
    </form>
  )
}
