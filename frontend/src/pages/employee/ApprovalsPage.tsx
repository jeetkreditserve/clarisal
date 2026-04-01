import { toast } from 'sonner'

import { ApprovalDecisionDialog } from '@/components/ui/ApprovalDecisionDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useApproveMyApprovalAction, useMyApprovalInbox, useRejectMyApprovalAction } from '@/hooks/useEmployeeSelf'
import { getApprovalActionTone } from '@/lib/status'

export function ApprovalsPage() {
  const { data, isLoading } = useMyApprovalInbox()
  const approveMutation = useApproveMyApprovalAction()
  const rejectMutation = useRejectMyApprovalAction()

  const handleApprove = async (actionId: string, comment: string) => {
    await approveMutation.mutateAsync({ actionId, comment })
    toast.success('Approval recorded.')
  }

  const handleReject = async (actionId: string, comment: string) => {
    await rejectMutation.mutateAsync({ actionId, comment })
    toast.success('Rejection recorded.')
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
      <PageHeader eyebrow="Approvals" title="Requests needing my action" description="Approve or reject leave and on-duty requests routed to you by the organisation workflow engine." />
      <SectionCard title="Approval inbox" description="Approvals are blocked automatically for the organisation when the licence expires.">
        {data && data.length > 0 ? (
          <div className="space-y-3">
            {data.map((action) => (
              <div key={action.id} className="surface-muted flex flex-col gap-3 rounded-[24px] px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{action.subject_label}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    {action.requester_name} • {action.request_kind.replace(/_/g, ' ')} • {action.stage_name}
                  </p>
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
                    onSubmit={(comment) => handleApprove(action.id, comment)}
                  />
                  <ApprovalDecisionDialog
                    actionLabel={`Reject ${action.subject_label}`}
                    triggerClassName="btn-danger"
                    triggerLabel="Reject"
                    title="Reject request"
                    description="Rejection notes are required so the requester understands what must change."
                    confirmLabel="Reject request"
                    confirmTone="danger"
                    isCommentRequired
                    submitErrorFallback="Unable to reject this request."
                    isPending={rejectMutation.isPending}
                    onSubmit={(comment) => handleReject(action.id, comment)}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No approvals pending" description="Requests that need your action will appear here." />
        )}
      </SectionCard>
    </div>
  )
}
