import { Link } from 'react-router-dom'
import { FileClock, FileWarning, ShieldCheck, UserRound } from 'lucide-react'

import { MonthCalendar } from '@/components/ui/MonthCalendar'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useMyDashboard, useMyProfile } from '@/hooks/useEmployeeSelf'
import { getApprovalActionTone, getOnboardingStatusTone } from '@/lib/status'

const DASHBOARD_NOTICE_LIMIT = 3

export function EmployeeDashboardPage() {
  const { data: dashboard, isLoading } = useMyDashboard()
  const { data: profile } = useMyProfile()

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Self-service"
        title="My dashboard"
        description="Track onboarding progress, notices, approvals, and the current month calendar for leave, on-duty, and holidays."
        actions={
          <>
            <Link to="/me/onboarding" className="btn-primary">
              Continue onboarding
            </Link>
            <Link to="/me/leave" className="btn-secondary">
              Request leave
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
          <SectionCard title="Quick actions" description="Jump straight into the most common self-service actions without hunting through the sidebar.">
            <div className="flex flex-wrap gap-3">
            <Link to="/me/leave" className="btn-primary">
              Request leave
            </Link>
            <Link to="/me/attendance" className="btn-secondary">
              Mark attendance
            </Link>
            <Link to="/me/payslips" className="btn-secondary">
              View payslips
            </Link>
              <Link to="/me/profile" className="btn-secondary">
                Update profile
              </Link>
              <Link to="/me/documents" className="btn-secondary">
                Upload documents
              </Link>
              <Link to="/me/od" className="btn-secondary">
                Submit on-duty
              </Link>
              <Link to="/me/approvals" className="btn-secondary">
                Review approvals
              </Link>
            </div>
          </SectionCard>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Profile completion" value={`${dashboard.profile_completion.percent}%`} hint={`Employee code ${dashboard.employee_code || 'Pending assignment'}`} icon={UserRound} tone="primary" />
            <MetricCard title="Pending documents" value={dashboard.pending_documents} hint="Files waiting for admin review." icon={FileClock} tone="warning" />
            <MetricCard title="Verified documents" value={dashboard.verified_documents} hint="Approved by your organisation." icon={ShieldCheck} tone="success" />
            <MetricCard title="Rejected documents" value={dashboard.rejected_documents} hint="Upload corrected copies where needed." icon={FileWarning} tone="danger" />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Onboarding snapshot" description="Complete the remaining items until your record is fully ready.">
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone={getOnboardingStatusTone(dashboard.onboarding_status)}>{dashboard.onboarding_status}</StatusBadge>
                {dashboard.profile_completion.completed_sections.map((section) => (
                  <StatusBadge key={section} tone="success">
                    {section.replace(/_/g, ' ')}
                  </StatusBadge>
                ))}
                {dashboard.profile_completion.missing_sections.map((section) => (
                  <StatusBadge key={section} tone="warning">
                    {section.replace(/_/g, ' ')}
                  </StatusBadge>
                ))}
              </div>
              <div className="surface-muted mt-5 rounded-[24px] p-5 text-sm text-[hsl(var(--muted-foreground))]">
                <p className="font-medium text-[hsl(var(--foreground-strong))]">Current profile</p>
                <p className="mt-1">{profile?.employee.full_name || 'Employee'}</p>
                <p className="mt-4 font-medium text-[hsl(var(--foreground-strong))]">Employee email</p>
                <p className="mt-1">{profile?.employee.email}</p>
              </div>
            </SectionCard>

            <SectionCard title="Approvals and notices" description="Requests waiting on you, plus the latest organisation notices.">
              <div className="space-y-3">
                {dashboard.approvals.items.length > 0 ? (
                  dashboard.approvals.items.map((item) => (
                    <div key={item.action_id} className="surface-muted rounded-[20px] px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium text-[hsl(var(--foreground-strong))]">{item.label}</p>
                        <StatusBadge tone={getApprovalActionTone('PENDING')}>Pending</StatusBadge>
                      </div>
                      <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                        {item.request_kind.replace(/_/g, ' ')} • {item.stage_name}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">No approvals are waiting on you right now.</p>
                )}
                {dashboard.notices.slice(0, DASHBOARD_NOTICE_LIMIT).map((notice) => (
                  <div key={notice.id} className="surface-muted rounded-[20px] px-4 py-3">
                    <p className="font-medium text-[hsl(var(--foreground-strong))]">{notice.title}</p>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{notice.body}</p>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <SectionCard title="Month calendar" description="Leave, on-duty, and holiday entries are merged into a single calendar view.">
              <MonthCalendar month={dashboard.calendar} />
            </SectionCard>

            <SectionCard title="Events and leave balances" description="Upcoming celebrations plus your current leave availability.">
              <div className="flex flex-wrap gap-2">
                {dashboard.events.map((event) => (
                  <StatusBadge key={`${event.kind}-${event.date}`} tone="info">
                    {event.kind.replace(/_/g, ' ')} • {event.label}
                  </StatusBadge>
                ))}
              </div>
              <div className="mt-5 space-y-3">
                {dashboard.leave_balances.map((balance) => (
                  <div key={balance.leave_type_id} className="surface-muted rounded-[20px] px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-[hsl(var(--foreground-strong))]">{balance.leave_type_name}</p>
                      <span className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">{balance.available}</span>
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      Credited {balance.credited} • Pending {balance.pending}
                    </p>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>
        </>
      )}
    </div>
  )
}
