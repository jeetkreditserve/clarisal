import { Link } from 'react-router-dom'
import {
  Building2,
  CheckCircle2,
  Clock3,
  CreditCard,
  ShieldAlert,
  Users,
} from 'lucide-react'
import { useCtStats, useOrganisations } from '@/hooks/useCtOrganisations'
import { EmptyState } from '@/components/ui/EmptyState'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate } from '@/lib/format'
import { getOrganisationStatusTone } from '@/lib/status'

export function CTDashboardPage() {
  const { data: stats } = useCtStats()
  const { data: recent } = useOrganisations({ page: 1 })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Control Tower"
        title="Platform dashboard"
        description="Track organisation readiness, licence utilisation, and activation bottlenecks from one command surface."
        actions={
          <Link to="/ct/organisations/new" className="btn-primary">
            Create organisation
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          title="Total organisations"
          value={stats?.total_organisations ?? '...'}
          hint="All tenants provisioned on the platform."
          icon={Building2}
          tone="primary"
        />
        <MetricCard
          title="Active organisations"
          value={stats?.active_organisations ?? '...'}
          hint="Tenants with paid billing and active access."
          icon={CheckCircle2}
          tone="success"
        />
        <MetricCard
          title="Pending payment"
          value={stats?.pending_organisations ?? '...'}
          hint="Organisations waiting for manual payment confirmation."
          icon={Clock3}
          tone="warning"
        />
        <MetricCard
          title="Allocated licences"
          value={stats ? `${stats.allocated_licences}/${stats.total_licences}` : '...'}
          hint="Active and invited seats against purchased capacity."
          icon={CreditCard}
          tone="neutral"
        />
        <MetricCard
          title="Employees onboarded"
          value={stats?.total_employees ?? '...'}
          hint="Active employee accounts across organisations."
          icon={Users}
          tone="primary"
        />
        <MetricCard
          title="Suspended organisations"
          value={stats?.suspended_organisations ?? '...'}
          hint="Requires Control Tower intervention before usage resumes."
          icon={ShieldAlert}
          tone="danger"
        />
      </div>

      <SectionCard
        title="Recent organisations"
        description="Newest tenants and their current onboarding readiness."
        action={<Link to="/ct/organisations" className="btn-secondary">View all</Link>}
      >
        {!recent ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-16" />
            ))}
          </div>
        ) : recent.results.length === 0 ? (
          <EmptyState
            title="No organisations yet"
            description="Create the first organisation to start licence allocation and admin onboarding."
            action={<Link to="/ct/organisations/new" className="btn-primary">Create organisation</Link>}
            icon={Building2}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                  <th className="pb-3 pr-4 font-semibold">Organisation</th>
                  <th className="pb-3 pr-4 font-semibold">State</th>
                  <th className="pb-3 pr-4 font-semibold">Licences</th>
                  <th className="pb-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80">
                {recent.results.slice(0, 6).map((organisation) => (
                  <tr key={organisation.id} className="transition-colors hover:bg-slate-50/70">
                    <td className="py-4 pr-4">
                      <Link to={`/ct/organisations/${organisation.id}`} className="font-semibold text-slate-950 hover:text-[hsl(var(--primary))]">
                        {organisation.name}
                      </Link>
                      <p className="mt-1 text-xs text-slate-500">/{organisation.slug}</p>
                    </td>
                    <td className="py-4 pr-4">
                      <StatusBadge tone={getOrganisationStatusTone(organisation.status)}>{organisation.status}</StatusBadge>
                    </td>
                    <td className="py-4 pr-4 text-slate-600">{organisation.licence_count}</td>
                    <td className="py-4 text-slate-600">{formatDate(organisation.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  )
}
