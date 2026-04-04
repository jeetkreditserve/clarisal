import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useApprovalWorkflows,
  useCompleteEmployeeOffboarding,
  useDeleteEmployee,
  useDepartments,
  useEmployeeDetail,
  useEmployeeDocumentDownload,
  useEmployeeDocumentRequests,
  useEmployeeDocuments,
  useEmployees,
  useEndEmployeeEmployment,
  useLocations,
  useMarkEmployeeJoined,
  useMarkEmployeeProbationComplete,
  useOrgFullAndFinalSettlements,
  useUpdateEmployeeOffboarding,
  useUpdateEmployeeOffboardingTask,
  useUpdateEmployee,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { startCase } from '@/lib/format'
import { getDocumentRequestStatusTone, getDocumentStatusTone, getEmployeeStatusTone } from '@/lib/status'
import type { EmploymentType } from '@/types/hr'

function getOffboardingTaskTone(status: string) {
  if (status === 'COMPLETED') return 'success'
  if (status === 'WAIVED') return 'info'
  if (status === 'IN_PROGRESS') return 'warning'
  return 'neutral'
}

export function EmployeeDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const employeeId = id ?? ''
  const { data: employee, isLoading } = useEmployeeDetail(employeeId)
  const { data: departments } = useDepartments()
  const { data: locations } = useLocations()
  const { data: approvalWorkflows } = useApprovalWorkflows()
  const { data: managerOptions } = useEmployees({ status: 'ACTIVE', page: 1 })
  const { data: documentRequests } = useEmployeeDocumentRequests(employeeId)
  const { data: documents } = useEmployeeDocuments(employeeId)
  const { data: fnfSettlements } = useOrgFullAndFinalSettlements()
  const updateMutation = useUpdateEmployee(employeeId)
  const markJoinedMutation = useMarkEmployeeJoined(employeeId)
  const endEmploymentMutation = useEndEmployeeEmployment(employeeId)
  const updateOffboardingMutation = useUpdateEmployeeOffboarding(employeeId)
  const updateOffboardingTaskMutation = useUpdateEmployeeOffboardingTask(employeeId)
  const completeOffboardingMutation = useCompleteEmployeeOffboarding(employeeId)
  const probationCompleteMutation = useMarkEmployeeProbationComplete(employeeId)
  const deleteEmployeeMutation = useDeleteEmployee(employeeId)
  const downloadDocumentMutation = useEmployeeDocumentDownload()

  const [draft, setDraft] = useState<Partial<{
    designation: string
    employment_type: EmploymentType
    date_of_joining: string
    department_id: string
    office_location_id: string
    leave_approval_workflow_id: string
    on_duty_approval_workflow_id: string
    attendance_regularization_approval_workflow_id: string
  }>>({})
  const [joinForm, setJoinForm] = useState({
    employee_code: '',
    date_of_joining: '',
    designation: '',
    reporting_to_employee_id: '',
  })
  const [endEmploymentForm, setEndEmploymentForm] = useState({
    status: 'RESIGNED' as 'RESIGNED' | 'RETIRED' | 'TERMINATED',
    date_of_exit: '',
    exit_reason: '',
    exit_notes: '',
  })

  const employmentTypeOptions = ['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'].map((type) => ({
    value: type,
    label: startCase(type),
  }))
  const departmentOptions = [
    { value: '', label: 'Unassigned department' },
    ...(departments?.filter((department) => department.is_active).map((department) => ({
      value: department.id,
      label: department.name,
    })) ?? []),
  ]
  const locationOptions = [
    { value: '', label: 'Unassigned location' },
    ...(locations?.filter((location) => location.is_active).map((location) => ({
      value: location.id,
      label: location.name,
    })) ?? []),
  ]
  const workflowOptionsForKind = (requestKind: 'LEAVE' | 'ON_DUTY' | 'ATTENDANCE_REGULARIZATION') => [
    { value: '', label: `Use ${requestKind.replace(/_/g, ' ').toLowerCase()} default or rule` },
    ...(
      approvalWorkflows?.filter((workflow) => {
        if (workflow.default_request_kind === requestKind) return true
        return workflow.rules.some((rule) => rule.request_kind === requestKind)
      }).map((workflow) => ({
        value: workflow.id,
        label: workflow.name,
        hint: workflow.default_request_kind === requestKind ? 'Default' : 'Custom',
      })) ?? []
    ),
  ]
  if (isLoading || !employee) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={6} />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const managerSelectOptions = [
    { value: '', label: 'Use self as manager' },
    { value: employee.id, label: 'Self-managed / top-level employee' },
    ...(managerOptions?.results
      .filter((manager) => manager.id !== employee.id)
      .map((manager) => ({
        value: manager.id,
        label: manager.full_name,
      })) ?? []),
  ]
  const terminalStatusOptions = ['RESIGNED', 'RETIRED', 'TERMINATED'].map((status) => ({
    value: status,
    label: startCase(status),
  }))
  const fnfSettlement = fnfSettlements?.find((settlement) => settlement.employee_id === employeeId) ?? null

  const formValues = {
    designation: draft.designation ?? employee.designation ?? '',
    employment_type: draft.employment_type ?? employee.employment_type,
    date_of_joining: draft.date_of_joining ?? employee.date_of_joining ?? '',
    department_id: draft.department_id ?? employee.department ?? '',
    office_location_id: draft.office_location_id ?? employee.office_location ?? '',
    leave_approval_workflow_id: draft.leave_approval_workflow_id ?? employee.leave_approval_workflow_id ?? '',
    on_duty_approval_workflow_id: draft.on_duty_approval_workflow_id ?? employee.on_duty_approval_workflow_id ?? '',
    attendance_regularization_approval_workflow_id:
      draft.attendance_regularization_approval_workflow_id ?? employee.attendance_regularization_approval_workflow_id ?? '',
  }

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await updateMutation.mutateAsync({
        designation: formValues.designation,
        employment_type: formValues.employment_type,
        date_of_joining: formValues.date_of_joining || null,
        department_id: formValues.department_id || null,
        office_location_id: formValues.office_location_id || null,
        leave_approval_workflow_id: formValues.leave_approval_workflow_id || null,
        on_duty_approval_workflow_id: formValues.on_duty_approval_workflow_id || null,
        attendance_regularization_approval_workflow_id: formValues.attendance_regularization_approval_workflow_id || null,
      })
      toast.success('Employee updated.')
      setDraft({})
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update employee.'))
    }
  }

  const handleMarkJoined = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await markJoinedMutation.mutateAsync({
        employee_code: joinForm.employee_code || employee.suggested_employee_code,
        date_of_joining: joinForm.date_of_joining || formValues.date_of_joining,
        designation: joinForm.designation || formValues.designation,
        reporting_to_employee_id: joinForm.reporting_to_employee_id || employee.id,
      })
      toast.success('Employee marked as joined.')
      setJoinForm({ employee_code: '', date_of_joining: '', designation: '', reporting_to_employee_id: '' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to mark employee as joined.'))
    }
  }

  const handleEndEmployment = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await endEmploymentMutation.mutateAsync(endEmploymentForm)
      toast.success('Employment ended.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to end employment.'))
    }
  }

  const handleOffboardingUpdate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!employee.offboarding) return
    try {
      await updateOffboardingMutation.mutateAsync({
        exit_reason: endEmploymentForm.exit_reason,
        exit_notes: endEmploymentForm.exit_notes,
      })
      toast.success('Offboarding notes updated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update offboarding notes.'))
    }
  }

  const handleTaskStatus = async (taskId: string, status: 'PENDING' | 'COMPLETED' | 'WAIVED') => {
    try {
      await updateOffboardingTaskMutation.mutateAsync({
        taskId,
        payload: { status },
      })
      toast.success('Offboarding task updated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update offboarding task.'))
    }
  }

  const handleCompleteOffboarding = async () => {
    try {
      await completeOffboardingMutation.mutateAsync()
      toast.success('Offboarding completed.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to complete offboarding.'))
    }
  }

  const handleProbationComplete = async () => {
    try {
      await probationCompleteMutation.mutateAsync()
      toast.success('Probation marked as complete.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to mark probation complete.'))
    }
  }

  const handleDelete = async () => {
    try {
      await deleteEmployeeMutation.mutateAsync()
      toast.success('Employee deleted.')
      navigate('/org/employees')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to delete employee.'))
    }
  }

  const handleDownload = async (documentId: string) => {
    try {
      const response = await downloadDocumentMutation.mutateAsync({ employeeId, documentId })
      window.open(response.url, '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to open document.'))
    }
  }

  return (
    <div className="space-y-6">
      <Link to="/org/employees" className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]">
        <ArrowLeft className="h-4 w-4" />
        Back to employees
      </Link>

      <PageHeader
        eyebrow="Employee detail"
        title={employee.full_name}
        description={`${employee.email} • ${employee.employee_code || 'Code assigned on join'}`}
        actions={
          <div className="flex items-center gap-3">
            <StatusBadge tone={getEmployeeStatusTone(employee.status)}>{employee.status}</StatusBadge>
            <StatusBadge tone={employee.onboarding_status === 'COMPLETE' ? 'success' : 'warning'}>
              {employee.onboarding_status}
            </StatusBadge>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Employment settings" description="Assignments stay editable while the employee progresses through invited, pending, active, and end-of-employment states.">
          <form onSubmit={handleSave} className="grid gap-4">
            <input className="field-input" value={formValues.designation} onChange={(event) => setDraft((current) => ({ ...current, designation: event.target.value }))} placeholder="Designation" />
            <div className="grid gap-4 md:grid-cols-2">
              <AppSelect
                value={formValues.employment_type}
                onValueChange={(value) =>
                  setDraft((current) => ({ ...current, employment_type: value as EmploymentType }))
                }
                options={employmentTypeOptions}
              />
              <AppDatePicker
                value={formValues.date_of_joining}
                onValueChange={(value) => setDraft((current) => ({ ...current, date_of_joining: value }))}
                placeholder="Select joining date"
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <AppSelect
                value={formValues.department_id}
                onValueChange={(value) => setDraft((current) => ({ ...current, department_id: value }))}
                options={departmentOptions}
              />
              <AppSelect
                value={formValues.office_location_id}
                onValueChange={(value) =>
                  setDraft((current) => ({ ...current, office_location_id: value }))
                }
                options={locationOptions}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <AppSelect
                value={formValues.leave_approval_workflow_id}
                onValueChange={(value) => setDraft((current) => ({ ...current, leave_approval_workflow_id: value }))}
                options={workflowOptionsForKind('LEAVE')}
                placeholder="Leave workflow"
              />
              <AppSelect
                value={formValues.on_duty_approval_workflow_id}
                onValueChange={(value) => setDraft((current) => ({ ...current, on_duty_approval_workflow_id: value }))}
                options={workflowOptionsForKind('ON_DUTY')}
                placeholder="On-duty workflow"
              />
            </div>
            <div className="grid gap-4 md:grid-cols-1">
              <AppSelect
                value={formValues.attendance_regularization_approval_workflow_id}
                onValueChange={(value) =>
                  setDraft((current) => ({ ...current, attendance_regularization_approval_workflow_id: value }))
                }
                options={workflowOptionsForKind('ATTENDANCE_REGULARIZATION')}
                placeholder="Attendance regularization workflow"
              />
            </div>
            <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
              Save employee changes
            </button>
          </form>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Date of joining</p>
              <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{employee.date_of_joining || 'Not set'}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Probation ends</p>
              <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{employee.probation_end_date || 'Not on probation'}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Exit date</p>
              <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{employee.date_of_exit || 'Active employment'}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Effective leave workflow</p>
              <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{employee.effective_approval_workflows.leave.workflow_name}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
                {employee.effective_approval_workflows.leave.source}
              </p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Effective on-duty workflow</p>
              <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{employee.effective_approval_workflows.on_duty.workflow_name}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
                {employee.effective_approval_workflows.on_duty.source}
              </p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Effective attendance workflow</p>
              <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">
                {employee.effective_approval_workflows.attendance_regularization.workflow_name}
              </p>
              <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
                {employee.effective_approval_workflows.attendance_regularization.source}
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            {employee.probation_end_date ? (
              <div className="surface-muted flex flex-wrap items-center justify-between gap-4 rounded-[24px] p-5">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">Probation review</p>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    Probation ends on {employee.probation_end_date}. Mark this complete once the employee clears review.
                  </p>
                </div>
                <ConfirmDialog
                  trigger={
                    <button type="button" className="btn-secondary text-sm" disabled={probationCompleteMutation.isPending}>
                      Mark probation complete
                    </button>
                  }
                  title="Mark probation complete?"
                  description={`This will clear the probation end date for ${employee.full_name} and log the event. This cannot be undone.`}
                  confirmLabel="Mark complete"
                  variant="primary"
                  onConfirm={handleProbationComplete}
                />
              </div>
            ) : null}

            {employee.status === 'PENDING' ? (
              <form onSubmit={handleMarkJoined} className="surface-muted grid gap-4 rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Mark employee as joined</p>
                <input className="field-input" placeholder={employee.suggested_employee_code} value={joinForm.employee_code} onChange={(event) => setJoinForm((current) => ({ ...current, employee_code: event.target.value }))} />
                <div className="grid gap-4 md:grid-cols-2">
                  <AppDatePicker
                    value={joinForm.date_of_joining}
                    onValueChange={(value) =>
                      setJoinForm((current) => ({ ...current, date_of_joining: value }))
                    }
                    placeholder="Select joining date"
                  />
                  <input className="field-input" placeholder={formValues.designation || 'Designation'} value={joinForm.designation} onChange={(event) => setJoinForm((current) => ({ ...current, designation: event.target.value }))} />
                </div>
                <AppSelect
                  value={joinForm.reporting_to_employee_id}
                  onValueChange={(value) =>
                    setJoinForm((current) => ({ ...current, reporting_to_employee_id: value }))
                  }
                  options={managerSelectOptions}
                />
                <button type="submit" className="btn-primary" disabled={markJoinedMutation.isPending}>
                  Mark as joined
                </button>
              </form>
            ) : null}

            {employee.status === 'ACTIVE' ? (
              <form onSubmit={handleEndEmployment} className="surface-muted grid gap-4 rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">End employment</p>
                <div className="grid gap-4 md:grid-cols-2">
                  <AppSelect
                    value={endEmploymentForm.status}
                    onValueChange={(value) =>
                      setEndEmploymentForm((current) => ({
                        ...current,
                        status: value as 'RESIGNED' | 'RETIRED' | 'TERMINATED',
                      }))
                    }
                    options={terminalStatusOptions}
                  />
                  <AppDatePicker
                    value={endEmploymentForm.date_of_exit}
                    onValueChange={(value) =>
                      setEndEmploymentForm((current) => ({ ...current, date_of_exit: value }))
                    }
                    placeholder="Select exit date"
                  />
                </div>
                <input
                  className="field-input"
                  value={endEmploymentForm.exit_reason}
                  onChange={(event) => setEndEmploymentForm((current) => ({ ...current, exit_reason: event.target.value }))}
                  placeholder="Exit reason summary"
                />
                <textarea
                  className="field-input min-h-[120px]"
                  value={endEmploymentForm.exit_notes}
                  onChange={(event) => setEndEmploymentForm((current) => ({ ...current, exit_notes: event.target.value }))}
                  placeholder="Exit notes, handover context, or settlement reminders"
                />
                <button type="submit" className="btn-danger" disabled={endEmploymentMutation.isPending}>
                  End employment
                </button>
              </form>
            ) : null}

            {employee.offboarding ? (
              <div className="surface-muted grid gap-5 rounded-[24px] p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">Offboarding checklist</p>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      Track exit tasks, payroll review, access removal, and final acknowledgements before closing the employee record.
                    </p>
                  </div>
                  <StatusBadge tone={employee.offboarding.status === 'COMPLETED' ? 'success' : 'warning'}>
                    {employee.offboarding.status}
                  </StatusBadge>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-[20px] border border-[hsl(var(--border))] bg-white/70 px-4 py-3">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Exit date</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">{employee.offboarding.date_of_exit}</p>
                  </div>
                  <div className="rounded-[20px] border border-[hsl(var(--border))] bg-white/70 px-4 py-3">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Required tasks</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">
                      {employee.offboarding.completed_required_task_count} / {employee.offboarding.required_task_count}
                    </p>
                  </div>
                  <div className="rounded-[20px] border border-[hsl(var(--border))] bg-white/70 px-4 py-3">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">Pending document follow-up</p>
                    <p className="mt-2 font-semibold text-[hsl(var(--foreground-strong))]">{employee.offboarding.pending_document_requests}</p>
                  </div>
                </div>

                <form onSubmit={handleOffboardingUpdate} className="grid gap-4">
                  <input
                    className="field-input"
                    value={endEmploymentForm.exit_reason || employee.offboarding.exit_reason}
                    onChange={(event) => setEndEmploymentForm((current) => ({ ...current, exit_reason: event.target.value }))}
                    placeholder="Exit reason summary"
                  />
                  <textarea
                    className="field-input min-h-[120px]"
                    value={endEmploymentForm.exit_notes || employee.offboarding.exit_notes}
                    onChange={(event) => setEndEmploymentForm((current) => ({ ...current, exit_notes: event.target.value }))}
                    placeholder="Capture handover notes, settlement reminders, or investigation context"
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <button type="submit" className="btn-secondary" disabled={updateOffboardingMutation.isPending}>
                      Save offboarding notes
                    </button>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={employee.offboarding.status === 'COMPLETED' || completeOffboardingMutation.isPending}
                      onClick={() => void handleCompleteOffboarding()}
                    >
                      Complete offboarding
                    </button>
                  </div>
                </form>

                <div className="space-y-3">
                  {employee.offboarding.tasks.map((task) => (
                    <div key={task.id} className="rounded-[20px] border border-[hsl(var(--border))] bg-white/70 px-4 py-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-[hsl(var(--foreground-strong))]">{task.title}</p>
                            <StatusBadge tone={getOffboardingTaskTone(task.status)}>{task.status}</StatusBadge>
                            {task.is_required ? <StatusBadge tone="warning">Required</StatusBadge> : null}
                          </div>
                          <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{task.description}</p>
                          <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
                            {startCase(task.owner)} • Due {task.due_date || employee.offboarding?.date_of_exit}
                          </p>
                          {task.completed_by_name ? (
                            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                              Completed by {task.completed_by_name}
                            </p>
                          ) : null}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {task.status !== 'COMPLETED' ? (
                            <button
                              type="button"
                              className="btn-secondary"
                              disabled={updateOffboardingTaskMutation.isPending}
                              onClick={() => void handleTaskStatus(task.id, 'COMPLETED')}
                            >
                              Mark done
                            </button>
                          ) : null}
                          {task.status !== 'WAIVED' ? (
                            <button
                              type="button"
                              className="btn-secondary"
                              disabled={updateOffboardingTaskMutation.isPending}
                              onClick={() => void handleTaskStatus(task.id, 'WAIVED')}
                            >
                              Waive
                            </button>
                          ) : null}
                          {task.status === 'COMPLETED' || task.status === 'WAIVED' ? (
                            <button
                              type="button"
                              className="btn-secondary"
                              disabled={updateOffboardingTaskMutation.isPending}
                              onClick={() => void handleTaskStatus(task.id, 'PENDING')}
                            >
                              Reopen
                            </button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {fnfSettlement ? (
                  <div className="surface-card mt-1 rounded-[28px] p-5">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">Full &amp; Final Settlement</p>
                      <StatusBadge
                        tone={
                          fnfSettlement.status === 'PAID'
                            ? 'success'
                            : fnfSettlement.status === 'APPROVED'
                              ? 'info'
                              : fnfSettlement.status === 'CANCELLED'
                                ? 'danger'
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
                ) : null}
              </div>
            ) : null}

            {(employee.status === 'INVITED' || employee.status === 'PENDING') ? (
              <div className="surface-muted rounded-[24px] p-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Delete employee record</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">Invited and pending employees can be deleted to release the consumed licence seat.</p>
                <ConfirmDialog
                  trigger={
                    <button type="button" className="btn-danger mt-4" disabled={deleteEmployeeMutation.isPending}>
                      Delete employee
                    </button>
                  }
                  title="Delete employee record?"
                  description="This permanently removes the invited or pending employee record and cannot be undone."
                  confirmLabel="Delete employee"
                  onConfirm={handleDelete}
                />
              </div>
            ) : null}
          </div>
        </SectionCard>

        <SectionCard title="Employee snapshot" description="Onboarding checklist, profile summary, and uploaded files.">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Phone</p>
              <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">{employee.profile.phone_personal || 'Not provided'}</p>
            </div>
            <div className="surface-muted rounded-[24px] p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Address</p>
              <p className="mt-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                {[employee.profile.address_line1, employee.profile.city, employee.profile.state, employee.profile.country].filter(Boolean).join(', ') || 'Not provided'}
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Requested documents</p>
              {documentRequests && documentRequests.length > 0 ? (
                documentRequests.map((request) => (
                  <div key={request.id} className="surface-muted rounded-[20px] px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{request.document_type.name}</p>
                      <StatusBadge tone={getDocumentRequestStatusTone(request.status)}>{request.status}</StatusBadge>
                    </div>
                    {request.rejection_note ? (
                      <p className="mt-2 text-sm text-[hsl(var(--danger))]">{request.rejection_note}</p>
                    ) : null}
                  </div>
                ))
              ) : (
                <EmptyState title="No requested documents" description="Assign onboarding documents from the employee invite or document checklist flow." />
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">Submitted files</p>
              {documents && documents.length > 0 ? (
                documents.map((document) => (
                  <div key={document.id} className="surface-muted flex items-center justify-between gap-3 rounded-[20px] px-4 py-3">
                    <div>
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{document.document_type}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">{document.file_name}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge tone={getDocumentStatusTone(document.status)}>{document.status}</StatusBadge>
                      <button className="btn-secondary" onClick={() => void handleDownload(document.id)}>
                        <Download className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState title="No submitted files yet" description="Uploaded documents will appear here after the employee starts their checklist." />
              )}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
