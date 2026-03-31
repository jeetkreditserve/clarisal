import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useApproveMyApprovalAction, useMyApprovalInbox, useRejectMyApprovalAction } from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
import { getApprovalActionTone } from '@/lib/status'

export function ApprovalsPage() {
  const { data, isLoading } = useMyApprovalInbox()
  const approveMutation = useApproveMyApprovalAction()
  const rejectMutation = useRejectMyApprovalAction()

  const handleApprove = async (actionId: string) => {
    const comment = window.prompt('Add an approval note (optional):', '') ?? ''
    try {
      await approveMutation.mutateAsync({ actionId, comment })
      toast.success('Approval recorded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to approve this request.'))
    }
  }

  const handleReject = async (actionId: string) => {
    const comment = window.prompt('Add a rejection note:', '')
    if (comment === null) return
    try {
      await rejectMutation.mutateAsync({ actionId, comment })
      toast.success('Rejection recorded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to reject this request.'))
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
      <PageHeader eyebrow="Approvals" title="Requests needing my action" description="Approve or reject leave and on-duty requests routed to you by the organisation workflow engine." />
      <SectionCard title="Approval inbox" description="Approvals are blocked automatically for the organisation when the licence expires.">
        {data && data.length > 0 ? (
          <div className="space-y-3">
            {data.map((action) => (
              <div key={action.id} className="surface-muted flex flex-col gap-3 rounded-[24px] px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{action.subject_label}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    {action.requester_name} • {action.request_kind.replaceAll('_', ' ')} • {action.stage_name}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge tone={getApprovalActionTone(action.status)}>{action.status}</StatusBadge>
                  <button className="btn-secondary" onClick={() => void handleApprove(action.id)}>
                    Approve
                  </button>
                  <button className="btn-danger" onClick={() => void handleReject(action.id)}>
                    Reject
                  </button>
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
