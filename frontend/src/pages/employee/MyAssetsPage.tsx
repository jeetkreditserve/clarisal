import { BriefcaseBusiness } from 'lucide-react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useAcknowledgeMyAssetAssignment, useMyAssetAssignments } from '@/hooks/useEmployeeSelf'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, formatDateTime } from '@/lib/format'
import { getAssetAssignmentTone } from '@/lib/status'

export function MyAssetsPage() {
  const { data: assignments = [], isLoading } = useMyAssetAssignments()
  const acknowledgeMutation = useAcknowledgeMyAssetAssignment()

  const pendingAcknowledgementCount = assignments.filter((assignment) => assignment.status === 'ACTIVE' && !assignment.acknowledged_at).length

  const handleAcknowledge = async (assignmentId: string) => {
    try {
      await acknowledgeMutation.mutateAsync(assignmentId)
      toast.success('Asset acknowledgement recorded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to acknowledge this asset right now.'))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={4} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workplace"
        title="My assets"
        description="Track issued company equipment, confirm receipt, and keep return expectations visible before handovers or exit formalities."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <SectionCard title="Active custody" description="Assets currently assigned to you.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{assignments.filter((assignment) => assignment.status === 'ACTIVE').length}</p>
        </SectionCard>
        <SectionCard title="Pending acknowledgement" description="Items still waiting for your receipt confirmation.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{pendingAcknowledgementCount}</p>
        </SectionCard>
        <SectionCard title="Returned or closed" description="Assets already returned or otherwise resolved.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{assignments.filter((assignment) => assignment.status !== 'ACTIVE').length}</p>
        </SectionCard>
      </div>

      <SectionCard title="Issued assets" description="Each record shows the current acknowledgement state and expected return timing.">
        {assignments.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {assignments.map((assignment) => (
              <div key={assignment.id} className="rounded-[24px] border border-[hsl(var(--border))] bg-white/70 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{assignment.asset_name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {assignment.asset_tag || 'Unlabeled asset'} • {assignment.employee_code || 'Employee code not assigned'}
                    </p>
                  </div>
                  <StatusBadge tone={getAssetAssignmentTone(assignment.status)}>{assignment.status}</StatusBadge>
                </div>

                <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Issued at</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDateTime(assignment.assigned_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Expected return</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDate(assignment.expected_return_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Condition on issue</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{assignment.condition_on_issue}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Acknowledged</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">
                      {assignment.acknowledged_at ? formatDateTime(assignment.acknowledged_at) : 'Pending your confirmation'}
                    </dd>
                  </div>
                </dl>

                {assignment.notes ? <p className="mt-4 text-sm text-[hsl(var(--muted-foreground))]">{assignment.notes}</p> : null}

                {assignment.status === 'ACTIVE' && !assignment.acknowledged_at ? (
                  <div className="mt-4">
                    <ConfirmDialog
                      title="Confirm receipt of this asset?"
                      description="This records that you received the item in the stated condition and are responsible for returning it when asked."
                      confirmLabel="Confirm acknowledgement"
                      variant="primary"
                      onConfirm={() => handleAcknowledge(assignment.id)}
                      trigger={
                        <button type="button" className="btn-primary" disabled={acknowledgeMutation.isPending}>
                          Acknowledge receipt
                        </button>
                      }
                    />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={BriefcaseBusiness}
            title="No assets assigned"
            description="When company equipment is issued to you, it will appear here with acknowledgement and return details."
          />
        )}
      </SectionCard>
    </div>
  )
}
