import { Link } from 'react-router-dom'
import { CreditCard, MapPin, UserPlus, Users } from 'lucide-react'
import { useOrgDashboard } from '@/hooks/useOrgAdmin'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, startCase } from '@/lib/format'
import { ORG_ONBOARDING_STEPS } from '@/lib/status'

export function OrgDashboardPage() {
  const { data, isLoading } = useOrgDashboard()

  const currentStage = ORG_ONBOARDING_STEPS.find((step) => step.id === data?.onboarding_stage)

  return (
    <div className="space-y-6">
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

      {isLoading || !data ? (
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-32" />
            ))}
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <Skeleton className="h-80" />
            <Skeleton className="h-80" />
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
            <div className="flex flex-col gap-4 rounded-[24px] bg-slate-50 p-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm text-slate-500">Current stage</p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <StatusBadge tone="info">{startCase(data.onboarding_stage)}</StatusBadge>
                  <p className="text-sm text-slate-600">{currentStage?.description || 'Organisation lifecycle in progress.'}</p>
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
                  <p className="text-sm text-slate-500">No department distribution yet.</p>
                ) : (
                  data.by_department.map((department) => (
                    <div key={department.department_name}>
                      <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="font-medium text-slate-900">{department.department_name}</span>
                        <span className="text-slate-500">{department.count}</span>
                      </div>
                      <div className="h-3 rounded-full bg-slate-100">
                        <div
                          className="h-3 rounded-full bg-cyan-600"
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
                  <p className="text-sm text-slate-500">No location distribution yet.</p>
                ) : (
                  data.by_location.map((location) => (
                    <div key={location.location_name} className="flex items-center justify-between rounded-[20px] bg-slate-50 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <MapPin className="h-4 w-4 text-cyan-700" />
                        <span className="font-medium text-slate-900">{location.location_name}</span>
                      </div>
                      <span className="text-sm text-slate-500">{location.count}</span>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>
          </div>

          <SectionCard title="Recent joins" description="The newest employee records with joining dates.">
            {data.recent_joins.length === 0 ? (
              <p className="text-sm text-slate-500">No recent joins recorded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                      <th className="pb-3 pr-4 font-semibold">Employee</th>
                      <th className="pb-3 pr-4 font-semibold">Designation</th>
                      <th className="pb-3 font-semibold">Joining date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/80">
                    {data.recent_joins.map((employee) => (
                      <tr key={employee.id}>
                        <td className="py-4 pr-4">
                          <Link to={`/org/employees/${employee.id}`} className="font-semibold text-slate-950 hover:text-[hsl(var(--primary))]">
                            {employee.user__first_name} {employee.user__last_name}
                          </Link>
                          <p className="mt-1 text-xs text-slate-500">{employee.employee_code}</p>
                        </td>
                        <td className="py-4 pr-4 text-slate-600">{employee.designation || 'Not assigned'}</td>
                        <td className="py-4 text-slate-600">{formatDate(employee.date_of_joining)}</td>
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
