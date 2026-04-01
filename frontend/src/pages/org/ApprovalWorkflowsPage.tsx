import { useState } from 'react'
import { toast } from 'sonner'

import { ApprovalDecisionDialog } from '@/components/ui/ApprovalDecisionDialog'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppDialog } from '@/components/ui/AppDialog'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useApprovalInbox,
  useApprovalWorkflows,
  useApproveApprovalAction,
  useCreateApprovalWorkflow,
  useRejectApprovalAction,
  useUpdateApprovalWorkflow,
} from '@/hooks/useOrgAdmin'
import { createDefaultApprovalWorkflow } from '@/lib/constants'
import { getErrorMessage } from '@/lib/errors'
import { getApprovalActionTone } from '@/lib/status'

export function ApprovalWorkflowsPage() {
  const { data: workflows, isLoading } = useApprovalWorkflows()
  const { data: inbox } = useApprovalInbox()
  const createMutation = useCreateApprovalWorkflow()
  const [editingId, setEditingId] = useState<string | null>(null)
  const updateMutation = useUpdateApprovalWorkflow(editingId ?? '')
  const approveMutation = useApproveApprovalAction()
  const rejectMutation = useRejectApprovalAction()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form, setForm] = useState(createDefaultApprovalWorkflow)

  const resetForm = () => {
    setEditingId(null)
    setForm(createDefaultApprovalWorkflow())
    setIsModalOpen(false)
  }

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingId) {
        await updateMutation.mutateAsync(form)
        toast.success('Approval workflow updated.')
      } else {
        await createMutation.mutateAsync(form)
        toast.success('Approval workflow created.')
      }
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save approval workflow.'))
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
        eyebrow="Approvals"
        title="Approval workflows"
        description="Create the default workflow required for employee onboarding, then add more specific flows for departments, designations, or locations."
        actions={
          <button type="button" className="btn-primary" onClick={() => setIsModalOpen(true)}>
            Add workflow
          </button>
        }
      />

      <SectionCard title="Configured workflows" description="Specific rule matching and multi-stage routing are supported by the backend. Create and edit actions now use the same modal flow.">
        <div className="space-y-4">
          {workflows?.map((workflow) => (
            <div key={workflow.id} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{workflow.name}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">{workflow.description || 'No description'}</p>
                </div>
                <div className="flex items-center gap-2">
                  {workflow.is_default ? <StatusBadge tone="success">Default</StatusBadge> : null}
                  <StatusBadge tone={workflow.is_active ? 'info' : 'neutral'}>{workflow.is_active ? 'Active' : 'Inactive'}</StatusBadge>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setEditingId(workflow.id)
                      setForm({
                        name: workflow.name,
                        description: workflow.description,
                        is_default: workflow.is_default,
                        is_active: workflow.is_active,
                        rules: workflow.rules.map((rule) => ({
                          id: rule.id,
                          name: rule.name,
                          request_kind: rule.request_kind,
                          priority: rule.priority,
                          is_active: rule.is_active,
                          department_id: rule.department,
                          office_location_id: rule.office_location,
                          specific_employee_id: rule.specific_employee,
                          employment_type: rule.employment_type,
                          designation: rule.designation,
                          leave_type_id: rule.leave_type,
                        })),
                        stages: workflow.stages.map((stage) => ({
                          id: stage.id,
                          name: stage.name,
                          sequence: stage.sequence,
                          mode: stage.mode,
                          fallback_type: stage.fallback_type,
                          fallback_employee_id: stage.fallback_employee_id,
                          approvers: stage.approvers.map((approver) => ({
                            id: approver.id,
                            approver_type: approver.approver_type,
                            approver_employee_id: approver.approver_employee_id,
                          })),
                        })),
                      })
                      setIsModalOpen(true)
                    }}
                  >
                    Edit
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Rules</p>
                  <div className="mt-2 space-y-2">
                    {workflow.rules.map((rule) => (
                      <div key={rule.id} className="surface-shell rounded-[16px] px-3 py-2 text-sm text-[hsl(var(--foreground-strong))]">
                        {rule.name} • {rule.request_kind.replace(/_/g, ' ')}
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Stages</p>
                  <div className="mt-2 space-y-2">
                    {workflow.stages.map((stage) => (
                      <div key={stage.id} className="surface-shell rounded-[16px] px-3 py-2 text-sm text-[hsl(var(--foreground-strong))]">
                        {stage.sequence}. {stage.name}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Approval inbox" description="Managers and org admins can action pending requests here unless licence expiry blocks approvals.">
        <div className="space-y-3">
          {inbox?.map((action) => (
            <div key={action.id} className="surface-muted flex flex-col gap-3 rounded-[22px] px-4 py-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">{action.subject_label}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{action.requester_name} • {action.stage_name}</p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge tone={getApprovalActionTone(action.status)}>{action.status}</StatusBadge>
                <ApprovalDecisionDialog
                  actionLabel={`Approve ${action.subject_label}`}
                  triggerClassName="btn-secondary"
                  triggerLabel="Approve"
                  title="Approve request"
                  description="Add an optional note for the requester or the audit trail before approving this request."
                  confirmLabel="Approve request"
                  submitErrorFallback="Unable to approve this request."
                  isPending={approveMutation.isPending}
                  onSubmit={(comment) => approveMutation.mutateAsync({ actionId: action.id, comment })}
                />
                <ApprovalDecisionDialog
                  actionLabel={`Reject ${action.subject_label}`}
                  triggerClassName="btn-danger"
                  triggerLabel="Reject"
                  title="Reject request"
                  description="Rejection notes are required so requesters understand what must change."
                  confirmLabel="Reject request"
                  confirmTone="danger"
                  isCommentRequired
                  submitErrorFallback="Unable to reject this request."
                  isPending={rejectMutation.isPending}
                  onSubmit={(comment) => rejectMutation.mutateAsync({ actionId: action.id, comment })}
                />
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
        title={editingId ? 'Edit workflow' : 'Create workflow'}
        description="This lightweight builder focuses on the workflow name, description, and default behavior."
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetForm}>
              Cancel
            </button>
            <button type="submit" form="approval-workflow-form" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingId ? 'Save changes' : 'Save workflow'}
            </button>
          </div>
        }
      >
        <form id="approval-workflow-form" onSubmit={handleCreate} className="grid gap-4">
          <input className="field-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Workflow name" />
          <textarea className="field-textarea" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
          <AppCheckbox
            checked={form.is_default}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_default: checked }))}
            label="Default workflow"
            description="A default workflow is mandatory before org admins can invite employees."
          />
        </form>
      </AppDialog>
    </div>
  )
}
