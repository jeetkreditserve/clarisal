import { Link } from 'react-router-dom'
import { FileClock, FileWarning, ShieldCheck, UserRound } from 'lucide-react'
import { useMyDashboard, useMyProfile } from '@/hooks/useEmployeeSelf'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { startCase } from '@/lib/format'

export function EmployeeDashboardPage() {
  const { data: dashboard, isLoading } = useMyDashboard()
  const { data: profile } = useMyProfile()

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Self-service"
        title="My dashboard"
        description="Track your profile completion, document review state, and required onboarding sections."
        actions={
          <>
            <Link to="/me/profile" className="btn-primary">
              Complete profile
            </Link>
            <Link to="/me/documents" className="btn-secondary">
              Upload documents
            </Link>
          </>
        }
      />

      {isLoading || !dashboard ? (
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <SkeletonMetricCard key={index} />
            ))}
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <SkeletonTable rows={4} />
            <SkeletonTable rows={4} />
          </div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Profile completion" value={`${dashboard.profile_completion.percent}%`} hint={`Employee code ${dashboard.employee_code}`} icon={UserRound} tone="primary" />
            <MetricCard title="Pending documents" value={dashboard.pending_documents} hint="Waiting for organisation review." icon={FileClock} tone="warning" />
            <MetricCard title="Verified documents" value={dashboard.verified_documents} hint="Documents approved by your administrator." icon={ShieldCheck} tone="success" />
            <MetricCard title="Rejected documents" value={dashboard.rejected_documents} hint="Review notes and upload corrected copies." icon={FileWarning} tone="danger" />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Completed sections" description="The sections you have already finished.">
              <div className="flex flex-wrap gap-2">
                {dashboard.profile_completion.completed_sections.length > 0 ? (
                  dashboard.profile_completion.completed_sections.map((section) => (
                    <StatusBadge key={section} tone="success">
                      {startCase(section)}
                    </StatusBadge>
                  ))
                ) : (
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">No profile sections completed yet.</p>
                )}
              </div>
            </SectionCard>

            <SectionCard title="Still required" description="Finish these sections to reach a complete employee record.">
              <div className="flex flex-wrap gap-2">
                {dashboard.profile_completion.missing_sections.map((section) => (
                  <StatusBadge key={section} tone="warning">
                    {startCase(section)}
                  </StatusBadge>
                ))}
              </div>
              <div className="surface-muted mt-5 rounded-[24px] p-5 text-sm text-[hsl(var(--muted-foreground))]">
                <p className="font-medium text-[hsl(var(--foreground-strong))]">Current name</p>
                <p className="mt-1">{profile?.employee.full_name || 'Employee'}</p>
                <p className="mt-4 font-medium text-[hsl(var(--foreground-strong))]">Organisation</p>
                <p className="mt-1">{profile?.employee.email}</p>
              </div>
            </SectionCard>
          </div>
        </>
      )}
    </div>
  )
}
