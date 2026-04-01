import { useState } from 'react'
import { toast } from 'sonner'

import { ApprovalDecisionDialog } from '@/components/ui/ApprovalDecisionDialog'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useApprovalInbox, useApprovalWorkflows, useApproveApprovalAction, useCreateApprovalWorkflow, useRejectApprovalAction } from '@/hooks/useOrgAdmin'
import { createDefaultApprovalWorkflow } from '@/lib/constants'
import { getErrorMessage } from '@/lib/errors'
import { getApprovalActionTone } from '@/lib/status'

export function ApprovalWorkflowsPage() {
  const { data: workflows, isLoading } = useApprovalWorkflows()
  const { data: inbox } = useApprovalInbox()
  const createMutation = useCreateApprovalWorkflow()
  const approveMutation = useApproveApprovalAction()
  const rejectMutation = useRejectApprovalAction()
  const [form, setForm] = useState(createDefaultApprovalWorkflow)

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createMutation.mutateAsync(form)
      toast.success('Approval workflow created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create approval workflow.'))
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
      <PageHeader eyebrow="Approvals" title="Approval workflows" description="Create the default workflow required for employee onboarding, then add more specific flows for departments, designations, or locations." />

      <div className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
        <SectionCard title="Create workflow" description="This lightweight builder creates a default workflow using the primary organisation admin as approver.">
          <form onSubmit={handleCreate} className="grid gap-4">
            <input className="field-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
            <textarea className="field-textarea" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input type="checkbox" checked={form.is_default} onChange={(event) => setForm((current) => ({ ...current, is_default: event.target.checked }))} />
              Default workflow
            </label>
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              Save workflow
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Configured workflows" description="Specific rule matching and multi-stage routing are supported by the backend; this screen focuses on the default setup and visibility.">
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
      </div>

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
    </div>
  )
}
