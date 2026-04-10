import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { AppSelect } from '@/components/ui/AppSelect'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCancelPayrollFiling, useCalculatePayrollRun, useCreateCompensationAssignment, useCreateCompensationTemplate, useCreateOrgArrear, useCreatePayrollRun, useCreatePayrollTdsChallan, useDownloadPayrollFiling, useEmployees, useFinalizePayrollRun, useGeneratePayrollFiling, useOrgArrears, usePayrollSummary, useRegeneratePayrollFiling, useRerunPayrollRun, useSubmitCompensationAssignment, useSubmitCompensationTemplate, useSubmitPayrollRun } from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'
import { getCompensationStatusTone, getPayrollRunStatusTone } from '@/lib/status'
import React, { useMemo, useState } from 'react'

const currentYear = new Date().getFullYear()
const PAYROLL_SECTION_OPTIONS = [
  { value: 'setup', label: 'Setup' },
  { value: 'compensation', label: 'Compensation' },
  { value: 'runs', label: 'Runs' },
  { value: 'filings', label: 'Filings' },
] as const

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function getFilingTone(status: string) {
  switch (status) {
    case 'GENERATED':
      return 'success' as const
    case 'BLOCKED':
      return 'danger' as const
    case 'SUPERSEDED':
      return 'warning' as const
    case 'CANCELLED':
      return 'neutral' as const
    default:
      return 'info' as const
  }
}

export function PayrollPage() {
  const { data, isLoading } = usePayrollSummary()
  const { data: employeesResponse } = useEmployees({ status: 'ACTIVE' })
  const createTemplateMutation = useCreateCompensationTemplate()
  const submitTemplateMutation = useSubmitCompensationTemplate()
  const createAssignmentMutation = useCreateCompensationAssignment()
  const createArrearMutation = useCreateOrgArrear()
  const submitAssignmentMutation = useSubmitCompensationAssignment()
  const createRunMutation = useCreatePayrollRun()
  const createTdsChallanMutation = useCreatePayrollTdsChallan()
  const calculateRunMutation = useCalculatePayrollRun()
  const submitRunMutation = useSubmitPayrollRun()
  const finalizeRunMutation = useFinalizePayrollRun()
  const rerunMutation = useRerunPayrollRun()
  const generateFilingMutation = useGeneratePayrollFiling()
  const regenerateFilingMutation = useRegeneratePayrollFiling()
  const cancelFilingMutation = useCancelPayrollFiling()
  const downloadFilingMutation = useDownloadPayrollFiling()
  const { data: arrears = [] } = useOrgArrears()

  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    basic_pay: '',
    employee_deduction: '',
  })
  const [assignmentForm, setAssignmentForm] = useState({
    employee_id: '',
    template_id: '',
    effective_from: `${currentYear}-04-01`,
  })
  const [arrearForm, setArrearForm] = useState({
    employee_id: '',
    for_period_year: String(currentYear),
    for_period_month: String(new Date().getMonth() || 12),
    reason: '',
    amount: '',
  })
  const [runForm, setRunForm] = useState({
    period_year: String(currentYear),
    period_month: String(new Date().getMonth() + 1),
    use_attendance_inputs: false,
  })
  const [filingForm, setFilingForm] = useState({
    filing_type: 'PF_ECR',
    period_year: String(currentYear),
    period_month: String(new Date().getMonth() + 1),
    fiscal_year: `${currentYear}-${currentYear + 1}`,
    quarter: 'Q1',
    artifact_format: 'PDF',
  })
  const [tdsChallanForm, setTdsChallanForm] = useState({
    fiscal_year: `${currentYear}-${currentYear + 1}`,
    period_year: String(currentYear),
    period_month: String(new Date().getMonth() + 1),
    deposit_date: `${currentYear}-${String(new Date().getMonth() + 1).padStart(2, '0')}-07`,
    bsr_code: '',
    challan_serial_number: '',
    tax_deposited: '',
    statement_receipt_number: '',
    notes: '',
  })
  const [activeSection, setActiveSection] = useState<(typeof PAYROLL_SECTION_OPTIONS)[number]['value']>('setup')

  const employeeOptions = useMemo(
    () =>
      (employeesResponse?.results ?? []).map((employee) => ({
        value: employee.id,
        label: employee.full_name,
        hint: employee.designation || employee.employee_code || undefined,
      })),
    [employeesResponse],
  )
  const templateOptions = useMemo(
    () =>
      (data?.compensation_templates ?? []).map((template) => ({
        value: template.id,
        label: template.name,
        hint: template.status,
      })),
    [data],
  )

  const handleCreateTemplate = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createTemplateMutation.mutateAsync({
        name: templateForm.name,
        description: templateForm.description,
        lines: [
          {
            component_code: 'BASIC',
            name: 'Basic Pay',
            component_type: 'EARNING',
            monthly_amount: templateForm.basic_pay,
            is_taxable: true,
          },
          {
            component_code: 'PF_EMPLOYEE',
            name: 'Employee PF',
            component_type: 'EMPLOYEE_DEDUCTION',
            monthly_amount: templateForm.employee_deduction,
            is_taxable: false,
          },
        ],
      })
      toast.success('Compensation template created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the compensation template. Check the salary-component values and try again.'))
    }
  }

  const handleCreateAssignment = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createAssignmentMutation.mutateAsync({
        employee_id: assignmentForm.employee_id,
        template_id: assignmentForm.template_id,
        effective_from: assignmentForm.effective_from,
      })
      toast.success('Compensation assignment created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the compensation assignment. Select an employee, an approved template, and an effective date.'))
    }
  }

  const handleCreateArrear = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createArrearMutation.mutateAsync({
        employee_id: arrearForm.employee_id,
        for_period_year: Number(arrearForm.for_period_year),
        for_period_month: Number(arrearForm.for_period_month),
        reason: arrearForm.reason,
        amount: arrearForm.amount,
      })
      toast.success('Arrear recorded.')
      setArrearForm((current) => ({
        ...current,
        employee_id: '',
        reason: '',
        amount: '',
      }))
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to record the arrear. Confirm the employee, payroll period, and amount.'))
    }
  }

  const handleCreateRun = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createRunMutation.mutateAsync({
        period_year: Number(runForm.period_year),
        period_month: Number(runForm.period_month),
        use_attendance_inputs: runForm.use_attendance_inputs,
      })
      toast.success('Payroll run created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the payroll run. Check the payroll period and try again.'))
    }
  }

  const handleSubmitTemplate = async (templateId: string) => {
    try {
      await submitTemplateMutation.mutateAsync(templateId)
      toast.success('Template submitted for approval.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to submit this template for approval. Review the template and try again.'))
    }
  }

  const handleSubmitAssignment = async (assignmentId: string) => {
    try {
      await submitAssignmentMutation.mutateAsync(assignmentId)
      toast.success('Salary assignment submitted for approval.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to submit this salary assignment for approval. Review the assignment and try again.'))
    }
  }

  const handleCalculateRun = async (runId: string) => {
    const toastId = toast.loading('Calculating payroll run...')
    try {
      await calculateRunMutation.mutateAsync(runId)
      toast.dismiss(toastId)
      toast.success('Payroll run calculated.')
    } catch (error) {
      toast.dismiss(toastId)
      toast.error(getErrorMessage(error, 'Unable to calculate this payroll run. Check salary assignments and payroll inputs, then try again.'))
    }
  }

  const handleSubmitRun = async (runId: string) => {
    try {
      await submitRunMutation.mutateAsync(runId)
      toast.success('Payroll run submitted for approval.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to submit this payroll run. Resolve all exceptions first, then try again.'))
    }
  }

  const handleFinalizeRun = async (runId: string) => {
    const toastId = toast.loading('Finalizing payroll run...')
    try {
      await finalizeRunMutation.mutateAsync(runId)
      toast.dismiss(toastId)
      toast.success('Payroll run finalized.')
    } catch (error) {
      toast.dismiss(toastId)
      toast.error(getErrorMessage(error, 'Unable to finalize this payroll run.'))
    }
  }

  const handleRerun = async (runId: string) => {
    try {
      await rerunMutation.mutateAsync(runId)
      toast.success('Payroll rerun created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the payroll rerun.'))
    }
  }

  const handleGenerateFiling = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload: Record<string, unknown> = {
      filing_type: filingForm.filing_type,
    }

    if (['PF_ECR', 'ESI_MONTHLY', 'PROFESSIONAL_TAX'].includes(filingForm.filing_type)) {
      payload.period_year = Number(filingForm.period_year)
      payload.period_month = Number(filingForm.period_month)
    }

    if (['FORM24Q', 'FORM16'].includes(filingForm.filing_type)) {
      payload.fiscal_year = filingForm.fiscal_year
    }

    if (filingForm.filing_type === 'FORM24Q') {
      payload.quarter = filingForm.quarter
    }

    if (filingForm.filing_type === 'FORM16') {
      payload.artifact_format = filingForm.artifact_format
    }

    try {
      const batch = await generateFilingMutation.mutateAsync(payload)
      if (batch.status === 'BLOCKED') {
        toast.error(batch.validation_errors[0] || 'The filing batch is blocked by missing statutory metadata.')
        return
      }
      toast.success('Statutory filing generated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to generate the statutory filing.'))
    }
  }

  const handleCreateTdsChallan = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createTdsChallanMutation.mutateAsync({
        fiscal_year: tdsChallanForm.fiscal_year,
        period_year: Number(tdsChallanForm.period_year),
        period_month: Number(tdsChallanForm.period_month),
        deposit_date: tdsChallanForm.deposit_date,
        bsr_code: tdsChallanForm.bsr_code,
        challan_serial_number: tdsChallanForm.challan_serial_number,
        tax_deposited: tdsChallanForm.tax_deposited,
        statement_receipt_number: tdsChallanForm.statement_receipt_number,
        notes: tdsChallanForm.notes,
      })
      toast.success('TDS challan recorded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to record the TDS challan.'))
    }
  }

  const handleDownloadFiling = async (filingId: string) => {
    try {
      const result = await downloadFilingMutation.mutateAsync(filingId)
      triggerDownload(result.blob, result.filename)
      toast.success('Statutory filing downloaded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to download the statutory filing.'))
    }
  }

  const handleRegenerateFiling = async (filingId: string) => {
    try {
      const batch = await regenerateFilingMutation.mutateAsync(filingId)
      if (batch.status === 'BLOCKED') {
        toast.error(batch.validation_errors[0] || 'The regenerated filing is blocked by missing statutory metadata.')
        return
      }
      toast.success('Statutory filing regenerated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to regenerate the statutory filing.'))
    }
  }

  const handleCancelFiling = async (filingId: string) => {
    try {
      await cancelFilingMutation.mutateAsync(filingId)
      toast.success('Statutory filing cancelled.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to cancel the statutory filing.'))
    }
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
    </div>
  )
}

type RunFormState = { period_year: string; period_month: string; use_attendance_inputs: boolean }

interface RunsSectionProps {
  data: NonNullable<NonNullable<ReturnType<typeof usePayrollSummary>['data']>>
  runForm: RunFormState
  setRunForm: React.Dispatch<React.SetStateAction<RunFormState>>
  createRunMutation: ReturnType<typeof useCreatePayrollRun>
  calculateRunMutation: ReturnType<typeof useCalculatePayrollRun>
  submitRunMutation: ReturnType<typeof useSubmitPayrollRun>
  finalizeRunMutation: ReturnType<typeof useFinalizePayrollRun>
  rerunMutation: ReturnType<typeof useRerunPayrollRun>
  onCreateRun: (event: React.FormEvent) => Promise<void>
  onCalculateRun: (runId: string) => Promise<void>
  onSubmitRun: (runId: string) => Promise<void>
  onFinalizeRun: (runId: string) => Promise<void>
  onRerun: (runId: string) => Promise<void>
}

function RunsSection({
  data,
  runForm,
  setRunForm,
  createRunMutation,
  calculateRunMutation,
  submitRunMutation,
  finalizeRunMutation,
  rerunMutation,
  onCreateRun,
  onCalculateRun,
  onSubmitRun,
  onFinalizeRun,
  onRerun,
}: RunsSectionProps) {
  const summarizeRunExceptions = (run: { exception_count?: number }) => ({ count: run.exception_count ?? 0 })

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <SectionCard title="Run readiness" description="Create and process runs only after setup and compensation sections are in place.">
        <div className="space-y-3 text-sm text-[hsl(var(--muted-foreground))]">
          <p>1. Confirm at least one approved salary assignment exists.</p>
          <p>2. Decide whether this run should use attendance-linked payable days before you create it.</p>
          <p>3. Use calculate first, then resolve every exception before submitting for approval.</p>
          <p>4. Finalization is irreversible for the current preview snapshot and will publish payslips.</p>
        </div>
      </SectionCard>

      <SectionCard title="Payroll processing" description="Create a run, calculate results, submit for approval, finalize, and trigger reruns when corrections are needed. Do not treat this as full statutory payroll sign-off yet.">
        <form onSubmit={onCreateRun} className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor="payroll-run-year">Period year</label>
            <input id="payroll-run-year" className="field-input" value={runForm.period_year} onChange={(event) => setRunForm((current) => ({ ...current, period_year: event.target.value }))} placeholder="Year" />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-run-month">Period month</label>
            <input id="payroll-run-month" className="field-input" value={runForm.period_month} onChange={(event) => setRunForm((current) => ({ ...current, period_month: event.target.value }))} placeholder="Month" />
          </div>
          <label className="md:col-span-2 flex items-start gap-3 rounded-[18px] border border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface-subtle))] px-4 py-3 text-sm text-[hsl(var(--foreground-strong))]">
            <input
              type="checkbox"
              checked={runForm.use_attendance_inputs}
              onChange={(event) => setRunForm((current) => ({ ...current, use_attendance_inputs: event.target.checked }))}
              className="mt-1"
            />
            <span>
              Use attendance and leave inputs for payable days.
              <span className="block text-[hsl(var(--muted-foreground))]">
                Leave this off unless attendance for the payroll period has been reviewed and is ready to drive LOP deductions.
              </span>
            </span>
          </label>
          <div className="md:col-span-2">
            <button type="submit" className="btn-primary" disabled={createRunMutation.isPending}>
              Create payroll run
            </button>
          </div>
        </form>
        <div className="mt-5 space-y-3">
          {data.pay_runs.length ? data.pay_runs.map((run) => {
            const exceptionSummary = summarizeRunExceptions(run)
            const attendanceSummary = run.attendance_snapshot

            return (
              <div key={run.id} className="surface-shell rounded-[18px] px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{run.name}</p>
                      <StatusBadge tone={getPayrollRunStatusTone(run.status)}>
                        {run.status}
                      </StatusBadge>
                      {exceptionSummary.count ? <StatusBadge tone="warning">{exceptionSummary.count} exceptions</StatusBadge> : null}
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {(run.employee_count ?? 0)} employees • {run.run_type} • {run.period_month}/{run.period_year}
                    </p>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      Attendance-linked payable days: {run.use_attendance_inputs ? 'enabled' : 'not applied'}
                    </p>
                    {attendanceSummary?.attendance_source && run.use_attendance_inputs ? (
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        Attendance snapshot: {attendanceSummary.total_attendance_paid_days} paid days • {attendanceSummary.total_lop_days} LOP days • {attendanceSummary.total_overtime_minutes} overtime minutes
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {run.status === 'DRAFT' || run.status === 'REJECTED' || run.status === 'CALCULATED' ? (
                      <button type="button" className="btn-secondary" onClick={() => void onCalculateRun(run.id)}>
                        {run.status === 'CALCULATED' ? 'Recalculate' : 'Calculate'}
                      </button>
                    ) : null}
                    {run.status === 'CALCULATED' && !exceptionSummary.count ? (
                      <button type="button" className="btn-secondary" onClick={() => void onSubmitRun(run.id)}>
                        Submit
                      </button>
                    ) : null}
                    {run.status === 'APPROVED' ? (
                      <ConfirmDialog
                        trigger={
                          <button type="button" className="btn-secondary">
                            Finalize
                          </button>
                        }
                        title="Finalize payroll run?"
                        description="This will publish payslips from the current limited-scope payroll snapshot."
                        confirmLabel="Finalize"
                        variant="primary"
                        onConfirm={() => onFinalizeRun(run.id)}
                      />
                    ) : null}
                    {run.status === 'FINALIZED' ? (
                      <ConfirmDialog
                        trigger={
                          <button type="button" className="btn-secondary">
                            Rerun
                          </button>
                        }
                        title="Create payroll rerun?"
                        description="Use this only for correction testing while payroll remains in preview scope."
                        confirmLabel="Create rerun"
                        variant="primary"
                        onConfirm={() => onRerun(run.id)}
                      />
                    ) : null}
                    <Link
                      to={`/org/payroll/runs/${run.id}`}
                      className="btn-secondary text-xs"
                    >
                      View Details →
                    </Link>
                  </div>
                </div>
                {exceptionSummary.count ? (
                  <div className="mt-4 rounded-[18px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-4 py-3 text-sm text-[hsl(var(--foreground-strong))]">
                    <p className="font-medium">This run cannot move forward until the exceptions are fixed.</p>
                    <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                      <Link to={`/org/payroll/runs/${run.id}`} className="underline hover:text-[hsl(var(--foreground))]">
                        View {exceptionSummary.count} exception{exceptionSummary.count !== 1 ? 's' : ''} in run details
                      </Link>
                    </p>
                  </div>
                ) : null}
              </div>
            )
          }) : (
            <EmptyState title="No payroll runs yet" description="Create the first pay run once templates and assignments are in place." />
          )}
        </div>
      </SectionCard>
    </div>
  )
}

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Payroll"
        title="Payroll control room"
        description="Preview tax slabs, compensation templates, employee salary assignments, payroll runs, and payslip publication from one place."
      />

      <div className="rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
        <p className="font-semibold">Payroll now covers statutory runs and filing exports.</p>
        <p className="mt-1 text-[hsl(var(--muted-foreground))]">
          Use this workspace to generate finalized payroll runs, statutory filings, and employee-facing tax documents from the same control room.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-5">
        <div className="surface-muted rounded-[22px] px-5 py-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Tax slab sets</p>
          <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{data.tax_slab_sets.length}</p>
        </div>
        <div className="surface-muted rounded-[22px] px-5 py-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Templates</p>
          <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{data.compensation_templates.length}</p>
        </div>
        <div className="surface-muted rounded-[22px] px-5 py-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Assignments</p>
          <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{data.compensation_assignments.length}</p>
        </div>
        <div className="surface-muted rounded-[22px] px-5 py-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Payslips</p>
          <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{data.payslip_count}</p>
        </div>
        <div className="surface-muted rounded-[22px] px-5 py-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Filing batches</p>
          <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{data.statutory_filing_batches.length}</p>
        </div>
      </div>

      <SectionCard
        title="Payroll workspace sections"
        description="Work through payroll preview in three parts: setup, compensation, then run processing."
      >
        <div className="md:hidden">
          <AppSelect value={activeSection} onValueChange={(value) => setActiveSection(value as typeof activeSection)} options={PAYROLL_SECTION_OPTIONS.map((option) => ({ value: option.value, label: option.label }))} />
        </div>
        <div className="hidden md:flex md:flex-wrap md:gap-2">
          {PAYROLL_SECTION_OPTIONS.map((section) => (
            <button
              key={section.value}
              type="button"
              onClick={() => setActiveSection(section.value)}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
                activeSection === section.value
                  ? 'border-[hsl(var(--brand)_/_0.35)] bg-[hsl(var(--brand)_/_0.12)] text-[hsl(var(--foreground-strong))]'
                  : 'border-[hsl(var(--border)_/_0.84)] bg-[hsl(var(--surface))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]'
              }`}
            >
              {section.label}
            </button>
          ))}
        </div>
      </SectionCard>

      {activeSection === 'setup' ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title="Income tax masters" description="Statutory tax slab masters are managed by the Control Tower. Contact your CT admin to add or update slabs for a new financial year.">
            <div className="space-y-3">
              {data.tax_slab_sets.map((set) => (
                <div key={set.id} className="surface-shell rounded-[18px] px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{set.name}</p>
                    <StatusBadge tone="info">{set.is_old_regime ? 'Old Regime' : 'New Regime'}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{set.fiscal_year} • {set.slabs.length} slabs</p>
                </div>
              ))}
              {data.tax_slab_sets.length === 0 ? (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">No income tax masters seeded yet. Ask your CT admin to run the seed command.</p>
              ) : null}
            </div>
          </SectionCard>

          <SectionCard title="Setup guidance" description="Use this section first so payroll preview has the baseline tax and policy inputs it needs.">
            <div className="space-y-3 text-sm text-[hsl(var(--muted-foreground))]">
              <p>1. Confirm the correct fiscal-year slab set before assigning salary structures.</p>
              <p>2. Treat this as preview tax setup only until statutory payroll is completed for India.</p>
              <p>3. Move to the compensation section once the active slab set matches your intended payroll scenario.</p>
            </div>
          </SectionCard>
        </div>
      ) : null}

      {activeSection === 'compensation' ? (
        <CompensationSection
          data={data}
          employeesResponse={employeesResponse}
          arrears={arrears}
          templateForm={templateForm}
          setTemplateForm={setTemplateForm}
          assignmentForm={assignmentForm}
          setAssignmentForm={setAssignmentForm}
          arrearForm={arrearForm}
          setArrearForm={setArrearForm}
          createTemplateMutation={createTemplateMutation}
          createAssignmentMutation={createAssignmentMutation}
          createArrearMutation={createArrearMutation}
          onCreateTemplate={handleCreateTemplate}
          onCreateAssignment={handleCreateAssignment}
          onCreateArrear={handleCreateArrear}
          onSubmitTemplate={handleSubmitTemplate}
          onSubmitAssignment={handleSubmitAssignment}
        />
      ) : null}

      {activeSection === 'runs' ? (
        <RunsSection
          data={data}
          runForm={runForm}
          setRunForm={setRunForm}
          createRunMutation={createRunMutation}
          calculateRunMutation={calculateRunMutation}
          submitRunMutation={submitRunMutation}
          finalizeRunMutation={finalizeRunMutation}
          rerunMutation={rerunMutation}
          onCreateRun={handleCreateRun}
          onCalculateRun={handleCalculateRun}
          onSubmitRun={handleSubmitRun}
          onFinalizeRun={handleFinalizeRun}
          onRerun={handleRerun}
        />
      ) : null}

      {activeSection === 'filings' ? (
        <FilingsSection
          data={data}
          filingForm={filingForm}
          setFilingForm={setFilingForm}
          tdsChallanForm={tdsChallanForm}
          setTdsChallanForm={setTdsChallanForm}
          createTdsChallanMutation={createTdsChallanMutation}
          generateFilingMutation={generateFilingMutation}
          regenerateFilingMutation={regenerateFilingMutation}
          cancelFilingMutation={cancelFilingMutation}
          downloadFilingMutation={downloadFilingMutation}
          onGenerateFiling={handleGenerateFiling}
          onCreateTdsChallan={handleCreateTdsChallan}
          onDownloadFiling={handleDownloadFiling}
          onRegenerateFiling={handleRegenerateFiling}
          onCancelFiling={handleCancelFiling}
        />
      ) : null}
    </div>
  )
}

type TemplateFormState = { name: string; description: string; basic_pay: string; employee_deduction: string }
type AssignmentFormState = { employee_id: string; template_id: string; effective_from: string }
type ArrearFormState = { employee_id: string; for_period_year: string; for_period_month: string; reason: string; amount: string }
type FilingFormState = { filing_type: string; period_year: string; period_month: string; fiscal_year: string; quarter: string; artifact_format: string }
type TdsChallanFormState = { fiscal_year: string; period_year: string; period_month: string; deposit_date: string; bsr_code: string; challan_serial_number: string; tax_deposited: string; statement_receipt_number: string; notes: string }

interface CompensationSectionProps {
  data: NonNullable<NonNullable<ReturnType<typeof usePayrollSummary>['data']>>
  employeesResponse: ReturnType<typeof useEmployees>['data']
  arrears: NonNullable<NonNullable<ReturnType<typeof useOrgArrears>['data']>>
  templateForm: TemplateFormState
  setTemplateForm: React.Dispatch<React.SetStateAction<TemplateFormState>>
  assignmentForm: AssignmentFormState
  setAssignmentForm: React.Dispatch<React.SetStateAction<AssignmentFormState>>
  arrearForm: ArrearFormState
  setArrearForm: React.Dispatch<React.SetStateAction<ArrearFormState>>
  createTemplateMutation: ReturnType<typeof useCreateCompensationTemplate>
  createAssignmentMutation: ReturnType<typeof useCreateCompensationAssignment>
  createArrearMutation: ReturnType<typeof useCreateOrgArrear>
  onCreateTemplate: (event: React.FormEvent) => Promise<void>
  onCreateAssignment: (event: React.FormEvent) => Promise<void>
  onCreateArrear: (event: React.FormEvent) => Promise<void>
  onSubmitTemplate: (templateId: string) => Promise<void>
  onSubmitAssignment: (assignmentId: string) => Promise<void>
}

function CompensationSection({
  data,
  employeesResponse,
  arrears,
  templateForm,
  setTemplateForm,
  assignmentForm,
  setAssignmentForm,
  arrearForm,
  setArrearForm,
  createTemplateMutation,
  createAssignmentMutation,
  createArrearMutation,
  onCreateTemplate,
  onCreateAssignment,
  onCreateArrear,
  onSubmitTemplate,
  onSubmitAssignment,
}: CompensationSectionProps) {
  const employeeOptions = useMemo(
    () =>
      (employeesResponse?.results ?? []).map((employee) => ({
        value: employee.id,
        label: employee.full_name,
        hint: employee.designation || employee.employee_code || undefined,
      })),
    [employeesResponse],
  )
  const templateOptions = useMemo(
    () =>
      (data?.compensation_templates ?? []).map((template) => ({
        value: template.id,
        label: template.name,
        hint: template.status,
      })),
    [data],
  )

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <SectionCard title="Compensation templates" description="Define the reusable salary structure and submit the template through approval when it is ready for controlled payroll preview use.">
        <div className="mb-4 rounded-[18px] border border-[hsl(var(--info)_/_0.24)] bg-[hsl(var(--info)_/_0.1)] px-4 py-3 text-sm text-[hsl(var(--foreground-strong))]">
          <p className="font-medium">CTC context</p>
          <p className="mt-1 text-[hsl(var(--muted-foreground))]">
            Treat each template as a monthly salary-structure preview. In Indian payroll terms, this is the reusable monthly component breakup that later rolls into annual CTC and net-pay calculations.
          </p>
        </div>
        <form onSubmit={onCreateTemplate} className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor="payroll-template-name">Template name</label>
            <input id="payroll-template-name" className="field-input" value={templateForm.name} onChange={(event) => setTemplateForm((current) => ({ ...current, name: event.target.value }))} placeholder="Template name" />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-template-description">Description</label>
            <input id="payroll-template-description" className="field-input" value={templateForm.description} onChange={(event) => setTemplateForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-template-basic-pay">Basic pay</label>
            <input id="payroll-template-basic-pay" className="field-input" value={templateForm.basic_pay} onChange={(event) => setTemplateForm((current) => ({ ...current, basic_pay: event.target.value }))} placeholder="Basic pay" />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-template-employee-deduction">Employee deduction</label>
            <input id="payroll-template-employee-deduction" className="field-input" value={templateForm.employee_deduction} onChange={(event) => setTemplateForm((current) => ({ ...current, employee_deduction: event.target.value }))} placeholder="Employee deduction" />
          </div>
          <div className="md:col-span-2">
            <button type="submit" className="btn-primary" disabled={createTemplateMutation.isPending}>
              Create template
            </button>
          </div>
        </form>
        <div className="mt-5 space-y-3">
          {data.compensation_templates.map((template) => (
            <div key={template.id} className="surface-shell rounded-[18px] px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{template.name}</p>
                    <StatusBadge tone={getCompensationStatusTone(template.status)}>
                      {template.status}
                    </StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{template.lines.length} lines • Modified {formatDateTime(template.modified_at)}</p>
                </div>
                {template.status !== 'PENDING_APPROVAL' && template.status !== 'APPROVED' ? (
                  <button type="button" className="btn-secondary" onClick={() => void onSubmitTemplate(template.id)}>
                    Submit approval
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Salary assignments" description="Assign approved structures to employees with an effective date, then submit salary revisions into the approval queue. Review carefully because downstream payroll remains limited-scope.">
        <form onSubmit={onCreateAssignment} className="grid gap-4">
          <div>
            <label className="field-label" htmlFor="payroll-assignment-employee">Employee</label>
            <AppSelect id="payroll-assignment-employee" value={assignmentForm.employee_id} onValueChange={(value) => setAssignmentForm((current) => ({ ...current, employee_id: value }))} options={employeeOptions} placeholder="Select employee" />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-assignment-template">Template</label>
            <AppSelect id="payroll-assignment-template" value={assignmentForm.template_id} onValueChange={(value) => setAssignmentForm((current) => ({ ...current, template_id: value }))} options={templateOptions} placeholder="Select template" />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-assignment-effective-from">Effective from</label>
            <AppDatePicker id="payroll-assignment-effective-from" value={assignmentForm.effective_from} onValueChange={(value) => setAssignmentForm((current) => ({ ...current, effective_from: value }))} placeholder="Select effective date" />
          </div>
          <button type="submit" className="btn-primary" disabled={createAssignmentMutation.isPending}>
            Create assignment
          </button>
        </form>
        <div className="mt-5 space-y-3">
          {data.compensation_assignments.length ? data.compensation_assignments.map((assignment) => (
            <div key={assignment.id} className="surface-shell rounded-[18px] px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{assignment.employee_name}</p>
                    <StatusBadge tone={getCompensationStatusTone(assignment.status)}>
                      {assignment.status}
                    </StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {assignment.template_name} • Effective {assignment.effective_from} • Version {assignment.version}
                  </p>
                </div>
                {assignment.status !== 'PENDING_APPROVAL' && assignment.status !== 'APPROVED' ? (
                  <button type="button" className="btn-secondary" onClick={() => void onSubmitAssignment(assignment.id)}>
                    Submit approval
                  </button>
                ) : null}
              </div>
            </div>
          )) : (
            <EmptyState title="No salary assignments yet" description="Assign a compensation template to at least one employee before calculating payroll." />
          )}
        </div>
      </SectionCard>

      <SectionCard title="Arrears adjustments" description="Record underpayments from prior periods so they flow into the next payroll calculation.">
        <form onSubmit={onCreateArrear} className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <label className="field-label" htmlFor="payroll-arrear-employee">Employee</label>
            <AppSelect
              id="payroll-arrear-employee"
              value={arrearForm.employee_id}
              onValueChange={(value) => setArrearForm((current) => ({ ...current, employee_id: value }))}
              options={employeeOptions}
              placeholder="Select employee"
            />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-arrear-year">For period year</label>
            <input
              id="payroll-arrear-year"
              className="field-input"
              value={arrearForm.for_period_year}
              onChange={(event) => setArrearForm((current) => ({ ...current, for_period_year: event.target.value }))}
              placeholder="Year"
            />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-arrear-month">For period month</label>
            <input
              id="payroll-arrear-month"
              className="field-input"
              value={arrearForm.for_period_month}
              onChange={(event) => setArrearForm((current) => ({ ...current, for_period_month: event.target.value }))}
              placeholder="Month"
            />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-arrear-reason">Reason</label>
            <input
              id="payroll-arrear-reason"
              className="field-input"
              value={arrearForm.reason}
              onChange={(event) => setArrearForm((current) => ({ ...current, reason: event.target.value }))}
              placeholder="Reason"
            />
          </div>
          <div>
            <label className="field-label" htmlFor="payroll-arrear-amount">Amount</label>
            <input
              id="payroll-arrear-amount"
              className="field-input"
              value={arrearForm.amount}
              onChange={(event) => setArrearForm((current) => ({ ...current, amount: event.target.value }))}
              placeholder="Amount"
            />
          </div>
          <div className="md:col-span-2">
            <button type="submit" className="btn-primary" disabled={createArrearMutation.isPending}>
              Record arrear
            </button>
          </div>
        </form>
        <div className="mt-5 space-y-3">
          {arrears.length ? arrears.map((arrear) => (
            <div key={arrear.id} className="surface-shell rounded-[18px] px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{arrear.employee_name}</p>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {arrear.reason} • {arrear.for_period_month}/{arrear.for_period_year}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">₹{arrear.amount}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
                    {arrear.is_included_in_payslip ? 'Included in payslip' : 'Pending payroll run'}
                  </p>
                </div>
              </div>
            </div>
          )) : (
            <EmptyState title="No arrears recorded" description="Record manual arrears here when pay from a prior period needs to be recovered in the next run." />
          )}
        </div>
      </SectionCard>
    </div>
  )
}

interface FilingsSectionProps {
  data: NonNullable<NonNullable<ReturnType<typeof usePayrollSummary>['data']>>
  filingForm: FilingFormState
  setFilingForm: React.Dispatch<React.SetStateAction<FilingFormState>>
  tdsChallanForm: TdsChallanFormState
  setTdsChallanForm: React.Dispatch<React.SetStateAction<TdsChallanFormState>>
  createTdsChallanMutation: ReturnType<typeof useCreatePayrollTdsChallan>
  generateFilingMutation: ReturnType<typeof useGeneratePayrollFiling>
  regenerateFilingMutation: ReturnType<typeof useRegeneratePayrollFiling>
  cancelFilingMutation: ReturnType<typeof useCancelPayrollFiling>
  downloadFilingMutation: ReturnType<typeof useDownloadPayrollFiling>
  onGenerateFiling: (event: React.FormEvent) => Promise<void>
  onCreateTdsChallan: (event: React.FormEvent) => Promise<void>
  onDownloadFiling: (filingId: string) => Promise<void>
  onRegenerateFiling: (filingId: string) => Promise<void>
  onCancelFiling: (filingId: string) => Promise<void>
}

function FilingsSection({
  data,
  filingForm,
  setFilingForm,
  tdsChallanForm,
  setTdsChallanForm,
  createTdsChallanMutation,
  generateFilingMutation,
  regenerateFilingMutation,
  cancelFilingMutation,
  downloadFilingMutation,
  onGenerateFiling,
  onCreateTdsChallan,
  onDownloadFiling,
  onRegenerateFiling,
  onCancelFiling,
}: FilingsSectionProps) {
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div className="space-y-6">
        <SectionCard title="Generate statutory filing" description="Create a persisted filing batch from finalized payroll data. Blockers are surfaced immediately so the batch never downloads partial statutory rows.">
          <form onSubmit={onGenerateFiling} className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="field-label">Filing type</span>
              <select
                className="field-input"
                value={filingForm.filing_type}
                onChange={(event) =>
                  setFilingForm((current) => ({
                    ...current,
                    filing_type: event.target.value,
                  }))
                }
              >
                <option value="PF_ECR">PF ECR</option>
                <option value="ESI_MONTHLY">ESI monthly</option>
                <option value="PROFESSIONAL_TAX">Professional tax</option>
                <option value="FORM24Q">Form 24Q</option>
                <option value="FORM16">Form 16</option>
              </select>
            </label>

            {['PF_ECR', 'ESI_MONTHLY', 'PROFESSIONAL_TAX'].includes(filingForm.filing_type) ? (
              <>
                <label className="grid gap-2">
                  <span className="field-label">Period year</span>
                  <input
                    className="field-input"
                    value={filingForm.period_year}
                    onChange={(event) => setFilingForm((current) => ({ ...current, period_year: event.target.value }))}
                    placeholder="2026"
                  />
                </label>
                <label className="grid gap-2">
                  <span className="field-label">Period month</span>
                  <input
                    className="field-input"
                    value={filingForm.period_month}
                    onChange={(event) => setFilingForm((current) => ({ ...current, period_month: event.target.value }))}
                    placeholder="4"
                  />
                </label>
              </>
            ) : null}

            {['FORM24Q', 'FORM16'].includes(filingForm.filing_type) ? (
              <label className="grid gap-2">
                <span className="field-label">Fiscal year</span>
                <input
                  className="field-input"
                  value={filingForm.fiscal_year}
                  onChange={(event) => setFilingForm((current) => ({ ...current, fiscal_year: event.target.value }))}
                  placeholder="2026-2027"
                />
              </label>
            ) : null}

            {filingForm.filing_type === 'FORM24Q' ? (
              <label className="grid gap-2">
                <span className="field-label">Quarter</span>
                <select
                  className="field-input"
                  value={filingForm.quarter}
                  onChange={(event) => setFilingForm((current) => ({ ...current, quarter: event.target.value }))}
                >
                  <option value="Q1">Q1</option>
                  <option value="Q2">Q2</option>
                  <option value="Q3">Q3</option>
                  <option value="Q4">Q4</option>
                </select>
              </label>
            ) : null}

            {filingForm.filing_type === 'FORM16' ? (
              <label className="grid gap-2">
                <span className="field-label">Artifact format</span>
                <select
                  className="field-input"
                  value={filingForm.artifact_format}
                  onChange={(event) => setFilingForm((current) => ({ ...current, artifact_format: event.target.value }))}
                >
                  <option value="PDF">PDF</option>
                  <option value="XML">XML</option>
                </select>
              </label>
            ) : null}

            <div className="md:col-span-2">
              <button type="submit" className="btn-primary" disabled={generateFilingMutation.isPending}>
                {generateFilingMutation.isPending ? 'Generating…' : 'Generate filing'}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard title="Record TDS challan" description="Form 24Q and filing-grade Form 16 exports use these monthly deposit records for BSR code, challan serial, and statement receipt metadata.">
          <form onSubmit={onCreateTdsChallan} className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="field-label">Fiscal year</span>
              <input
                className="field-input"
                value={tdsChallanForm.fiscal_year}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, fiscal_year: event.target.value }))}
                placeholder="2026-2027"
              />
            </label>
            <label className="grid gap-2">
              <span className="field-label">Period year</span>
              <input
                className="field-input"
                value={tdsChallanForm.period_year}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, period_year: event.target.value }))}
                placeholder="2026"
              />
            </label>
            <label className="grid gap-2">
              <span className="field-label">Period month</span>
              <input
                className="field-input"
                value={tdsChallanForm.period_month}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, period_month: event.target.value }))}
                placeholder="4"
              />
            </label>
            <div className="grid gap-2">
              <span className="field-label">Deposit date</span>
              <AppDatePicker
                id="tds-challan-deposit-date"
                value={tdsChallanForm.deposit_date}
                onValueChange={(value) => setTdsChallanForm((current) => ({ ...current, deposit_date: value }))}
                placeholder="Select deposit date"
              />
            </div>
            <label className="grid gap-2">
              <span className="field-label">BSR code</span>
              <input
                className="field-input"
                value={tdsChallanForm.bsr_code}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, bsr_code: event.target.value }))}
                placeholder="0510032"
              />
            </label>
            <label className="grid gap-2">
              <span className="field-label">Challan serial</span>
              <input
                className="field-input"
                value={tdsChallanForm.challan_serial_number}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, challan_serial_number: event.target.value }))}
                placeholder="00004"
              />
            </label>
            <label className="grid gap-2">
              <span className="field-label">Tax deposited</span>
              <input
                className="field-input"
                value={tdsChallanForm.tax_deposited}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, tax_deposited: event.target.value }))}
                placeholder="3500.00"
              />
            </label>
            <label className="grid gap-2">
              <span className="field-label">Statement receipt number</span>
              <input
                className="field-input"
                value={tdsChallanForm.statement_receipt_number}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, statement_receipt_number: event.target.value }))}
                placeholder="Optional until 24Q is filed"
              />
            </label>
            <label className="grid gap-2 md:col-span-2">
              <span className="field-label">Notes</span>
              <input
                className="field-input"
                value={tdsChallanForm.notes}
                onChange={(event) => setTdsChallanForm((current) => ({ ...current, notes: event.target.value }))}
                placeholder="Optional reconciliation note"
              />
            </label>
            <div className="md:col-span-2">
              <button type="submit" className="btn-secondary" disabled={createTdsChallanMutation.isPending}>
                {createTdsChallanMutation.isPending ? 'Recording…' : 'Record TDS challan'}
              </button>
            </div>
          </form>

          <div className="mt-5 space-y-3">
            {data.tds_challans.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">No TDS challans recorded yet for this organisation.</p>
            ) : (
              data.tds_challans.map((challan) => (
                <div key={challan.id} className="surface-shell rounded-[16px] px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">
                        {challan.period_month}/{challan.period_year} • {challan.quarter}
                      </p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        BSR {challan.bsr_code} • Challan {challan.challan_serial_number} • Deposit {challan.deposit_date}
                      </p>
                    </div>
                    <div className="text-right text-sm text-[hsl(var(--foreground-strong))]">
                      <p>INR {challan.tax_deposited}</p>
                      <p className="text-[hsl(var(--muted-foreground))]">{challan.statement_receipt_number || 'Receipt pending'}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Generated batches" description="Reproducible filing batches stay versioned. Regenerating a scope supersedes the older batch instead of silently mutating it.">
        <div className="space-y-3">
          {data.statutory_filing_batches.length === 0 ? (
            <EmptyState
              title="No filing batches yet"
              description="Generate PF, ESI, PT, 24Q, or Form 16 batches after you finalize the source payroll run or fiscal period."
            />
          ) : (
            data.statutory_filing_batches.map((batch) => (
              <div key={batch.id} className="surface-shell rounded-[18px] px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{batch.filing_type}</p>
                      <StatusBadge tone={getFilingTone(batch.status)}>{batch.status}</StatusBadge>
                      <StatusBadge tone="info">{batch.artifact_format}</StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {batch.period_year && batch.period_month
                        ? `${batch.period_month}/${batch.period_year}`
                        : batch.quarter
                          ? `${batch.quarter} • ${batch.fiscal_year}`
                          : batch.fiscal_year || 'Ad-hoc scope'}
                    </p>
                    <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                      {batch.generated_at ? `Generated ${formatDateTime(batch.generated_at)}` : 'Not generated yet'}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {batch.status === 'GENERATED' ? (
                      <button type="button" className="btn-secondary" onClick={() => void onDownloadFiling(batch.id)}>
                        Download
                      </button>
                    ) : null}
                    {batch.status !== 'CANCELLED' ? (
                      <button type="button" className="btn-secondary" onClick={() => void onRegenerateFiling(batch.id)}>
                        Regenerate
                      </button>
                    ) : null}
                    {batch.status !== 'CANCELLED' ? (
                      <button type="button" className="btn-secondary" onClick={() => void onCancelFiling(batch.id)}>
                        Cancel
                      </button>
                    ) : null}
                  </div>
                </div>
                {batch.validation_errors.length > 0 ? (
                  <div className="mt-3 rounded-[16px] border border-[hsl(var(--danger)_/_0.24)] bg-[hsl(var(--danger)_/_0.08)] px-3 py-3 text-sm text-[hsl(var(--foreground-strong))]">
                    <p className="font-medium">Validation blockers</p>
                    <ul className="mt-2 list-disc pl-5 text-[hsl(var(--muted-foreground))]">
                      {batch.validation_errors.slice(0, 3).map((error) => (
                        <li key={error}>{error}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      </SectionCard>
    </div>
  )
}
