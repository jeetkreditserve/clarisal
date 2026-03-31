import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, Plus, Search } from 'lucide-react'
import { useOrganisations } from '@/hooks/useCtOrganisations'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, startCase } from '@/lib/format'
import { getOrganisationStatusTone } from '@/lib/status'
import type { OrganisationStatus } from '@/types/organisation'

const STATUSES: Array<OrganisationStatus | ''> = ['', 'PENDING', 'PAID', 'ACTIVE', 'SUSPENDED']

export function OrganisationsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<OrganisationStatus | ''>('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useOrganisations({
    search: search || undefined,
    status: statusFilter || undefined,
    page,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Tenants"
        title="Organisations"
        description={data ? `${data.count} organisations across all lifecycle states.` : 'Review tenant setup, payment state, and capacity.'}
        actions={
          <Link to="/ct/organisations/new" className="btn-primary">
            <Plus className="h-4 w-4" />
            New organisation
          </Link>
        }
      />

      <SectionCard title="Search and filter" description="Quickly narrow by name or lifecycle state.">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative max-w-xl flex-1">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search organisations..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            className="field-input pl-11"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value as OrganisationStatus | '')
            setPage(1)
          }}
          className="field-select max-w-xs"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? startCase(s) : 'All statuses'}
            </option>
          ))}
        </select>
        </div>
      </SectionCard>

      <SectionCard title="Organisation directory" description="Control Tower view of every customer organisation.">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-16" />
            ))}
          </div>
        ) : data?.results.length === 0 ? (
          <EmptyState
            title="No organisations found"
            description="Try a different search term or create a new organisation to begin onboarding."
            icon={Building2}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.16em] text-slate-500">
                  <th className="pb-3 pr-4 font-semibold">Organisation</th>
                  <th className="pb-3 pr-4 font-semibold">Status</th>
                  <th className="pb-3 pr-4 font-semibold">Billing</th>
                  <th className="pb-3 pr-4 font-semibold">Stage</th>
                  <th className="pb-3 pr-4 font-semibold">Licences</th>
                  <th className="pb-3 pr-4 font-semibold">Created</th>
                  <th className="pb-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80">
                {data?.results.map((organisation) => (
                  <tr key={organisation.id} className="transition-colors hover:bg-slate-50/80">
                    <td className="py-4 pr-4">
                      <p className="font-semibold text-slate-950">{organisation.name}</p>
                      <p className="mt-1 text-xs text-slate-500">/{organisation.slug}</p>
                    </td>
                    <td className="py-4 pr-4">
                      <StatusBadge tone={getOrganisationStatusTone(organisation.status)}>{organisation.status}</StatusBadge>
                    </td>
                    <td className="py-4 pr-4 text-slate-600">{startCase(organisation.billing_status)}</td>
                    <td className="py-4 pr-4 text-slate-600">{startCase(organisation.onboarding_stage)}</td>
                    <td className="py-4 pr-4 text-slate-600">{organisation.licence_count}</td>
                    <td className="py-4 pr-4 text-slate-600">{formatDate(organisation.created_at)}</td>
                    <td className="py-4 text-right">
                      <Link to={`/ct/organisations/${organisation.id}`} className="font-semibold text-[hsl(var(--primary))] hover:underline">
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {data && data.count > 20 && (
        <div className="surface-card flex items-center justify-between rounded-[24px] px-5 py-4 text-sm text-slate-600">
          <span>Page {page}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((previousPage) => Math.max(1, previousPage - 1))}
              disabled={!data.previous}
              className="btn-secondary disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((previousPage) => previousPage + 1)}
              disabled={!data.next}
              className="btn-secondary disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
