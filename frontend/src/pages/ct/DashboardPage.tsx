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
import { SkeletonMetricCard, SkeletonTable } from '@/components/ui/Skeleton'
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
        {stats ? (
          <>
            <MetricCard
              title="Total organisations"
              value={stats.total_organisations}
              hint="All tenants provisioned on the platform."
              icon={Building2}
              tone="primary"
            />
            <MetricCard
              title="Active organisations"
              value={stats.active_organisations}
              hint="Tenants with paid billing and active access."
              icon={CheckCircle2}
              tone="success"
            />
            <MetricCard
              title="Pending payment"
              value={stats.pending_organisations}
              hint="Organisations waiting for manual payment confirmation."
              icon={Clock3}
              tone="warning"
            />
            <MetricCard
              title="Allocated licences"
              value={`${stats.allocated_licences}/${stats.total_licences}`}
              hint="Active and invited seats against purchased capacity."
              icon={CreditCard}
              tone="neutral"
            />
            <MetricCard
              title="Employees onboarded"
              value={stats.total_employees}
              hint="Active employee accounts across organisations."
              icon={Users}
              tone="primary"
            />
            <MetricCard
              title="Suspended organisations"
              value={stats.suspended_organisations}
              hint="Requires Control Tower intervention before usage resumes."
              icon={ShieldAlert}
              tone="danger"
            />
          </>
        ) : (
          Array.from({ length: 6 }).map((_, index) => <SkeletonMetricCard key={index} />)
        )}
      </div>

      <SectionCard
        title="Recent organisations"
        description="Newest tenants and their current onboarding readiness."
        action={<Link to="/ct/organisations" className="btn-secondary">View all</Link>}
      >
        {!recent ? (
          <SkeletonTable rows={5} />
        ) : recent.results.length === 0 ? (
          <EmptyState
            title="No organisations yet"
            description="Create the first organisation to start licence allocation and admin onboarding."
            action={<Link to="/ct/organisations/new" className="btn-primary">Create organisation</Link>}
            icon={Building2}
          />
        ) : (
          <div className="table-shell">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Organisation</th>
                  <th className="pb-3 pr-4 font-semibold">State</th>
                  <th className="pb-3 pr-4 font-semibold">Active seats</th>
                  <th className="pb-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="table-body divide-y divide-[hsl(var(--border)_/_0.84)]">
                {recent.results.slice(0, 6).map((organisation) => (
                  <tr key={organisation.id} className="table-row">
                    <td className="py-4 pr-4">
                      <Link to={`/ct/organisations/${organisation.id}`} className="table-primary font-semibold hover:text-[hsl(var(--brand))]">
                        {organisation.name}
                      </Link>
                      <p className="table-secondary mt-1 text-xs">/{organisation.slug}</p>
                    </td>
                    <td className="py-4 pr-4">
                      <StatusBadge tone={getOrganisationStatusTone(organisation.status)}>{organisation.status}</StatusBadge>
                    </td>
                    <td className="table-secondary py-4 pr-4">{organisation.licence_count}</td>
                    <td className="table-secondary py-4">{formatDate(organisation.created_at)}</td>
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
