import { Link } from 'react-router-dom'
import { ClipboardList, Users } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useMyApprovalInbox, useMyTeam, useMyTeamAttendance, useMyTeamLeave } from '@/hooks/useEmployeeSelf'
import { getApprovalActionTone, getAttendanceDayStatusTone, getEmployeeStatusTone } from '@/lib/status'

export function MyTeamPage() {
  const today = new Date().toISOString().slice(0, 10)
  const { data: team, isLoading } = useMyTeam()
  const { data: attendance } = useMyTeamAttendance(today)
  const { data: todayLeave } = useMyTeamLeave({ fromDate: today, toDate: today })
  const { data: approvals } = useMyApprovalInbox('my_team')

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonMetricCard key={index} />
          ))}
        </div>
        <SkeletonTable rows={4} />
      </div>
    )
  }

  if (!team?.length) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Manager self-service"
          title="My team"
          description="Review direct reports, keep leave and attendance in view, and jump into pending approvals without leaving employee mode."
        />
        <EmptyState
          title="You have no direct reports"
          description="When employees are assigned to you as their reporting manager, their leave, attendance, and approvals will surface here."
          icon={Users}
        />
      </div>
    )
  }

  const attendanceByEmployeeId = new Map(attendance?.map((item) => [item.employee_id, item]))
  const approvalsCount = approvals?.length ?? 0
  const deviationCount = team.reduce((sum, member) => sum + member.attendance_deviations_this_month, 0)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Manager self-service"
        title="My team"
        description="Track direct reports, isolate requests waiting on you, and keep today’s leave and attendance context visible in one place."
        actions={
          <>
            <Link to="/me/my-team/attendance" className="btn-primary">
              Review team attendance
            </Link>
            <Link to="/me/approvals" className="btn-secondary">
              Open approvals inbox
            </Link>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Direct reports" value={team.length} hint="Employees assigned to your reporting line." tone="primary" icon={Users} />
        <MetricCard title="Pending approvals" value={approvalsCount} hint={approvalsCount ? 'Requests currently waiting on you.' : 'No team approvals are pending.'} tone={approvalsCount ? 'warning' : 'success'} icon={ClipboardList} />
        <MetricCard title="Today on leave" value={todayLeave?.length ?? 0} hint="Direct reports with leave spanning today." tone="info" />
        <MetricCard title="Attendance deviations" value={deviationCount} hint="Open deviations logged this month." tone={deviationCount ? 'warning' : 'success'} />
      </div>

      <SectionCard title="Team cards" description="Use this as the manager’s quick-glance view for today’s status, open leave requests, and leave availability.">
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {team.map((member) => {
            const attendanceItem = attendanceByEmployeeId.get(member.id)
            return (
              <div key={member.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{member.name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {[member.designation, member.department].filter(Boolean).join(' • ') || 'Role details not assigned'}
                    </p>
                  </div>
                  <StatusBadge tone={getEmployeeStatusTone(member.status)}>{member.status}</StatusBadge>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <StatusBadge tone={attendanceItem ? getAttendanceDayStatusTone(attendanceItem.status) : 'neutral'}>
                    {attendanceItem?.status ?? 'No attendance'}
                  </StatusBadge>
                  <StatusBadge tone={member.pending_leave_requests ? 'warning' : 'success'}>
                    {member.pending_leave_requests} pending leave
                  </StatusBadge>
                  <StatusBadge tone={member.attendance_deviations_this_month ? 'warning' : 'success'}>
                    {member.attendance_deviations_this_month} deviations
                  </StatusBadge>
                </div>
                <div className="mt-4 space-y-2 text-sm text-[hsl(var(--muted-foreground))]">
                  {member.leave_balance_summary.slice(0, 2).map((balance) => (
                    <div key={balance.leave_type_id} className="flex items-center justify-between">
                      <span>{balance.leave_type_name}</span>
                      <span className="font-medium text-[hsl(var(--foreground-strong))]">{balance.available}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Today’s leave" description="Leave requests that include today across your direct reports.">
          {todayLeave?.length ? (
            <div className="space-y-3">
              {todayLeave.map((item) => (
                <div key={item.id} className="surface-muted rounded-[20px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-[hsl(var(--foreground-strong))]">{item.employee_name}</p>
                    <StatusBadge tone={item.status === 'APPROVED' ? 'success' : 'warning'}>{item.status}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {item.leave_type_name} • {item.start_date} to {item.end_date}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No direct reports are on leave today" description="Today’s approved or pending leave will surface here when it overlaps the current date." />
          )}
        </SectionCard>

        <SectionCard title="Pending approvals" description="Requests filtered to your team so you can act without hunting through the full inbox.">
          {approvals?.length ? (
            <div className="space-y-3">
              {approvals.map((action) => (
                <div key={action.id} className="surface-muted rounded-[20px] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-[hsl(var(--foreground-strong))]">{action.subject_label}</p>
                    <StatusBadge tone={getApprovalActionTone(action.status)}>{action.status}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {action.requester_name} • {action.request_kind.replace(/_/g, ' ')} • {action.stage_name}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No team approvals pending" description="Requests raised by your direct reports and routed to you will appear here." />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
