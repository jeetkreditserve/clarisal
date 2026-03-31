import { Link } from 'react-router-dom'
import { CreditCard, MapPin, UserPlus, Users } from 'lucide-react'
import { useOrgDashboard } from '@/hooks/useOrgAdmin'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { SkeletonMetricCard, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, startCase } from '@/lib/format'
import { ORG_ONBOARDING_STEPS } from '@/lib/status'

export function OrgDashboardPage() {
  const { data, isLoading } = useOrgDashboard()

  const currentStage = ORG_ONBOARDING_STEPS.find((step) => step.id === data?.onboarding_stage)

  return (
    <div className="space-y-6">
      {isLoading && !data ? (
        <SkeletonPageHeader />
      ) : (
        <PageHeader
          eyebrow="Organisation"
          title="People operations dashboard"
          description="Manage workforce setup, master data, and employee onboarding from a single operational view."
          actions={
            <>
              <Link to="/org/employees" className="btn-primary">
                Invite employee
              </Link>
              <Link to="/org/locations" className="btn-secondary">
                Manage master data
              </Link>
            </>
          }
        />
      )}

      {isLoading || !data ? (
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <SkeletonMetricCard key={index} />
            ))}
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <SkeletonTable rows={5} />
            <SkeletonTable rows={5} />
          </div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Total employees" value={data.total_employees} hint="All employee records in this organisation." icon={Users} tone="primary" />
            <MetricCard title="Active employees" value={data.active_employees} hint="Currently active and engaged employees." icon={UserPlus} tone="success" />
            <MetricCard title="Invited employees" value={data.invited_employees} hint="Employees who still need to activate their access." icon={Users} tone="info" />
            <MetricCard title="Licence usage" value={`${data.licence_used}/${data.licence_total}`} hint="Invited and active employees consume purchased seats." icon={CreditCard} tone="warning" />
          </div>

          <SectionCard title="Onboarding stage" description="Organisation readiness state derived from backend lifecycle transitions.">
            <div className="surface-muted flex flex-col gap-4 rounded-[24px] p-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">Current stage</p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <StatusBadge tone="info">{startCase(data.onboarding_stage)}</StatusBadge>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">{currentStage?.description || 'Organisation lifecycle in progress.'}</p>
                </div>
              </div>
              <div className="flex gap-3">
                <Link to="/org/locations" className="btn-secondary">
                  Locations
                </Link>
                <Link to="/org/departments" className="btn-secondary">
                  Departments
                </Link>
              </div>
            </div>
          </SectionCard>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Active employees by department" description="Department distribution for currently active staff.">
              <div className="space-y-4">
                {data.by_department.length === 0 ? (
                  <EmptyState
                    title="No department distribution yet"
                    description="Assign active employees to departments to unlock this workforce view."
                    icon={Users}
                  />
                ) : (
                  data.by_department.map((department) => (
                    <div key={department.department_name}>
                      <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="font-medium text-[hsl(var(--foreground-strong))]">{department.department_name}</span>
                        <span className="text-[hsl(var(--muted-foreground))]">{department.count}</span>
                      </div>
                      <div className="h-3 rounded-full bg-[hsl(var(--border)_/_0.55)]">
                        <div
                          className="h-3 rounded-full bg-[linear-gradient(90deg,hsl(var(--brand)),hsl(var(--brand-strong)))]"
                          style={{ width: `${Math.max((department.count / Math.max(data.active_employees, 1)) * 100, 10)}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title="Active employees by location" description="How the workforce is distributed across office sites.">
              <div className="space-y-4">
                {data.by_location.length === 0 ? (
                  <EmptyState
                    title="No location distribution yet"
                    description="Assign active employees to office locations to unlock this distribution summary."
                    icon={MapPin}
                  />
                ) : (
                  data.by_location.map((location) => (
                    <div key={location.location_name} className="surface-muted flex items-center justify-between rounded-[20px] px-4 py-3">
                      <div className="flex items-center gap-3">
                        <MapPin className="h-4 w-4 text-[hsl(var(--brand))]" />
                        <span className="font-medium text-[hsl(var(--foreground-strong))]">{location.location_name}</span>
                      </div>
                      <span className="text-sm text-[hsl(var(--muted-foreground))]">{location.count}</span>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>
          </div>

          <SectionCard title="Recent joins" description="The newest employee records with joining dates.">
            {data.recent_joins.length === 0 ? (
              <EmptyState
                title="No recent joins recorded yet"
                description="Employee joins will appear here as soon as your first hires are invited or activated."
                icon={UserPlus}
              />
            ) : (
              <div className="table-shell">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="table-head-row">
                      <th className="pb-3 pr-4 font-semibold">Employee</th>
                      <th className="pb-3 pr-4 font-semibold">Designation</th>
                      <th className="pb-3 font-semibold">Joining date</th>
                    </tr>
                  </thead>
                  <tbody className="table-body">
                    {data.recent_joins.map((employee) => (
                      <tr key={employee.id} className="table-row border-b border-[hsl(var(--border)_/_0.76)] last:border-b-0">
                        <td className="py-4 pr-4">
                          <Link to={`/org/employees/${employee.id}`} className="font-semibold text-[hsl(var(--foreground-strong))] hover:text-[hsl(var(--brand))]">
                            {employee.user__first_name} {employee.user__last_name}
                          </Link>
                          <p className="table-secondary mt-1 text-xs">{employee.employee_code}</p>
                        </td>
                        <td className="table-secondary py-4 pr-4">{employee.designation || 'Not assigned'}</td>
                        <td className="table-secondary py-4">{formatDate(employee.date_of_joining)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </>
      )}
    </div>
  )
}
