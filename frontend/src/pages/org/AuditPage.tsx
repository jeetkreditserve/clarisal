import { AuditTimeline } from '@/components/ui/AuditTimeline'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useOrgAuditLogs } from '@/hooks/useOrgAdmin'

export function OrgAuditPage() {
  const { data, isLoading } = useOrgAuditLogs()

  if (isLoading) {
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
        eyebrow="Audit"
        title="Audit timeline"
        description="Review organisation-level activity across profile changes, configuration updates, invitations, and lifecycle operations."
      />

      <SectionCard title="Timeline" description="Newest events appear first.">
        <AuditTimeline
          entries={data?.results ?? []}
          emptyTitle="No audit events have been recorded yet."
          emptyDescription="Organisation-level activity will appear here once admins start making changes."
        />
      </SectionCard>
    </div>
  )
}
