import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { AppSelect } from '@/components/ui/AppSelect'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCalculatePayrollRun,
  useCreateCompensationAssignment,
  useCreateCompensationTemplate,
  useCreatePayrollRun,
  useCreatePayrollTaxSlabSet,
  useEmployees,
  useFinalizePayrollRun,
  usePayrollSummary,
  useRerunPayrollRun,
  useSubmitCompensationAssignment,
  useSubmitCompensationTemplate,
  useSubmitPayrollRun,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'

const currentYear = new Date().getFullYear()

export function PayrollPage() {
  const { data, isLoading } = usePayrollSummary()
  const { data: employeesResponse } = useEmployees({ status: 'ACTIVE' })
  const createTaxSetMutation = useCreatePayrollTaxSlabSet()
  const createTemplateMutation = useCreateCompensationTemplate()
  const submitTemplateMutation = useSubmitCompensationTemplate()
  const createAssignmentMutation = useCreateCompensationAssignment()
  const submitAssignmentMutation = useSubmitCompensationAssignment()
  const createRunMutation = useCreatePayrollRun()
  const calculateRunMutation = useCalculatePayrollRun()
  const submitRunMutation = useSubmitPayrollRun()
  const finalizeRunMutation = useFinalizePayrollRun()
  const rerunMutation = useRerunPayrollRun()

  const [taxForm, setTaxForm] = useState({
    name: 'FY Default Copy',
    fiscal_year: `${currentYear}-${currentYear + 1}`,
    slab_one_limit: '300000',
    slab_two_limit: '700000',
    slab_two_rate: '10',
    slab_three_rate: '20',
  })
  const [templateForm, setTemplateForm] = useState({
    name: 'Standard Monthly',
    description: '',
    basic_pay: '50000',
    employee_deduction: '1800',
  })
  const [assignmentForm, setAssignmentForm] = useState({
    employee_id: '',
    template_id: '',
    effective_from: `${currentYear}-04-01`,
  })
  const [runForm, setRunForm] = useState({
    period_year: String(currentYear),
    period_month: String(new Date().getMonth() + 1),
  })

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

  const handleCreateTaxSet = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createTaxSetMutation.mutateAsync({
        name: taxForm.name,
        country_code: 'IN',
        fiscal_year: taxForm.fiscal_year,
        is_active: true,
        slabs: [
          { min_income: '0', max_income: taxForm.slab_one_limit, rate_percent: '0' },
          { min_income: taxForm.slab_one_limit, max_income: taxForm.slab_two_limit, rate_percent: taxForm.slab_two_rate },
          { min_income: taxForm.slab_two_limit, max_income: null, rate_percent: taxForm.slab_three_rate },
        ],
      })
      toast.success('Tax slab set created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the tax slab set.'))
    }
  }

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
      toast.error(getErrorMessage(error, 'Unable to create the compensation template.'))
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
      toast.error(getErrorMessage(error, 'Unable to create the compensation assignment.'))
    }
  }

  const handleCreateRun = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createRunMutation.mutateAsync({
        period_year: Number(runForm.period_year),
        period_month: Number(runForm.period_month),
      })
      toast.success('Payroll run created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the payroll run.'))
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

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Payroll"
        title="Payroll control room"
        description="Manage tax slabs, compensation templates, employee salary assignments, payroll runs, and payslip publication from one place."
      />

      <div className="grid gap-4 xl:grid-cols-4">
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
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Org tax slabs" description="Create org-specific copies of the active tax master or additional slab sets for alternate payroll scenarios.">
          <form onSubmit={handleCreateTaxSet} className="grid gap-4 md:grid-cols-2">
            <input className="field-input" value={taxForm.name} onChange={(event) => setTaxForm((current) => ({ ...current, name: event.target.value }))} placeholder="Slab set name" />
            <input className="field-input" value={taxForm.fiscal_year} onChange={(event) => setTaxForm((current) => ({ ...current, fiscal_year: event.target.value }))} placeholder="2026-2027" />
            <input className="field-input" value={taxForm.slab_one_limit} onChange={(event) => setTaxForm((current) => ({ ...current, slab_one_limit: event.target.value }))} placeholder="First slab upper limit" />
            <input className="field-input" value={taxForm.slab_two_limit} onChange={(event) => setTaxForm((current) => ({ ...current, slab_two_limit: event.target.value }))} placeholder="Second slab upper limit" />
            <input className="field-input" value={taxForm.slab_two_rate} onChange={(event) => setTaxForm((current) => ({ ...current, slab_two_rate: event.target.value }))} placeholder="Second slab rate" />
            <input className="field-input" value={taxForm.slab_three_rate} onChange={(event) => setTaxForm((current) => ({ ...current, slab_three_rate: event.target.value }))} placeholder="Top slab rate" />
            <div className="md:col-span-2">
              <button type="submit" className="btn-primary" disabled={createTaxSetMutation.isPending}>
                Save tax slab set
              </button>
            </div>
          </form>
          <div className="mt-5 space-y-3">
            {data.tax_slab_sets.map((set) => (
              <div key={set.id} className="surface-shell rounded-[18px] px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{set.name}</p>
                  <StatusBadge tone={set.source_set_id ? 'info' : 'success'}>{set.source_set_id ? 'Seeded copy' : 'Masterless copy'}</StatusBadge>
                </div>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{set.fiscal_year} • {set.slabs.length} slabs</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Compensation templates" description="Define the reusable salary structure and then submit the template through approval when it is ready for production use.">
          <form onSubmit={handleCreateTemplate} className="grid gap-4 md:grid-cols-2">
            <input className="field-input" value={templateForm.name} onChange={(event) => setTemplateForm((current) => ({ ...current, name: event.target.value }))} placeholder="Template name" />
            <input className="field-input" value={templateForm.description} onChange={(event) => setTemplateForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
            <input className="field-input" value={templateForm.basic_pay} onChange={(event) => setTemplateForm((current) => ({ ...current, basic_pay: event.target.value }))} placeholder="Basic pay" />
            <input className="field-input" value={templateForm.employee_deduction} onChange={(event) => setTemplateForm((current) => ({ ...current, employee_deduction: event.target.value }))} placeholder="Employee deduction" />
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
                      <StatusBadge tone={template.status === 'APPROVED' ? 'success' : template.status === 'REJECTED' ? 'danger' : 'warning'}>
                        {template.status}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{template.lines.length} lines • Modified {formatDateTime(template.modified_at)}</p>
                  </div>
                  {template.status !== 'PENDING_APPROVAL' && template.status !== 'APPROVED' ? (
                    <button type="button" className="btn-secondary" onClick={() => submitTemplateMutation.mutate(template.id)}>
                      Submit approval
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Salary assignments" description="Assign approved structures to employees with an effective date, then submit salary revisions into the approval queue.">
          <form onSubmit={handleCreateAssignment} className="grid gap-4">
            <AppSelect value={assignmentForm.employee_id} onValueChange={(value) => setAssignmentForm((current) => ({ ...current, employee_id: value }))} options={employeeOptions} placeholder="Select employee" />
            <AppSelect value={assignmentForm.template_id} onValueChange={(value) => setAssignmentForm((current) => ({ ...current, template_id: value }))} options={templateOptions} placeholder="Select template" />
            <input className="field-input" type="date" value={assignmentForm.effective_from} onChange={(event) => setAssignmentForm((current) => ({ ...current, effective_from: event.target.value }))} />
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
                      <StatusBadge tone={assignment.status === 'APPROVED' ? 'success' : assignment.status === 'REJECTED' ? 'danger' : 'warning'}>
                        {assignment.status}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {assignment.template_name} • Effective {assignment.effective_from} • Version {assignment.version}
                    </p>
                  </div>
                  {assignment.status !== 'PENDING_APPROVAL' && assignment.status !== 'APPROVED' ? (
                    <button type="button" className="btn-secondary" onClick={() => submitAssignmentMutation.mutate(assignment.id)}>
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

        <SectionCard title="Payroll processing" description="Create a run, calculate results, submit for approval, finalize, and trigger reruns when corrections are needed.">
          <form onSubmit={handleCreateRun} className="grid gap-4 md:grid-cols-2">
            <input className="field-input" value={runForm.period_year} onChange={(event) => setRunForm((current) => ({ ...current, period_year: event.target.value }))} placeholder="Year" />
            <input className="field-input" value={runForm.period_month} onChange={(event) => setRunForm((current) => ({ ...current, period_month: event.target.value }))} placeholder="Month" />
            <div className="md:col-span-2">
              <button type="submit" className="btn-primary" disabled={createRunMutation.isPending}>
                Create payroll run
              </button>
            </div>
          </form>
          <div className="mt-5 space-y-3">
            {data.pay_runs.length ? data.pay_runs.map((run) => (
              <div key={run.id} className="surface-shell rounded-[18px] px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{run.name}</p>
                      <StatusBadge tone={run.status === 'FINALIZED' ? 'success' : run.status === 'REJECTED' ? 'danger' : 'info'}>
                        {run.status}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {run.items.length} items • {run.run_type} • {run.period_month}/{run.period_year}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {run.status === 'DRAFT' || run.status === 'REJECTED' ? (
                      <button type="button" className="btn-secondary" onClick={() => calculateRunMutation.mutate(run.id)}>
                        Calculate
                      </button>
                    ) : null}
                    {run.status === 'CALCULATED' ? (
                      <button type="button" className="btn-secondary" onClick={() => submitRunMutation.mutate(run.id)}>
                        Submit
                      </button>
                    ) : null}
                    {run.status === 'APPROVED' ? (
                      <button type="button" className="btn-secondary" onClick={() => finalizeRunMutation.mutate(run.id)}>
                        Finalize
                      </button>
                    ) : null}
                    {run.status === 'FINALIZED' ? (
                      <button type="button" className="btn-secondary" onClick={() => rerunMutation.mutate(run.id)}>
                        Rerun
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            )) : (
              <EmptyState title="No payroll runs yet" description="Create the first pay run once templates and assignments are in place." />
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}

