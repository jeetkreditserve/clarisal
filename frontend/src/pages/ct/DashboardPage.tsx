import { useCtStats, useOrganisations } from '@/hooks/useCtOrganisations'
import { Link } from 'react-router-dom'
import { Building2, Users, Clock, CheckCircle } from 'lucide-react'
import type { CtDashboardStats } from '@/types/organisation'

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number | undefined; icon: typeof Building2; color: string
}) {
  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
      </div>
      <p className="mt-3 text-3xl font-bold text-foreground">
        {value === undefined ? (
          <span className="inline-block h-8 w-16 animate-pulse rounded bg-muted" />
        ) : value}
      </p>
    </div>
  )
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-blue-100 text-blue-800',
  ACTIVE: 'bg-green-100 text-green-800',
  SUSPENDED: 'bg-red-100 text-red-800',
}

export function CTDashboardPage() {
  const { data: stats } = useCtStats()
  const { data: recent } = useOrganisations({ page: 1 })

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">Platform overview</p>
        </div>
        <Link
          to="/ct/organisations/new"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          New Organisation
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Organisations" value={stats?.total_organisations} icon={Building2} color="bg-primary" />
        <StatCard label="Active" value={stats?.active_organisations} icon={CheckCircle} color="bg-green-500" />
        <StatCard label="Pending Payment" value={stats?.pending_organisations} icon={Clock} color="bg-yellow-500" />
        <StatCard label="Total Employees" value={stats?.total_employees} icon={Users} color="bg-purple-500" />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-medium text-foreground mb-4">Recent Organisations</h2>
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          {!recent ? (
            <div className="divide-y">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-4 w-48 animate-pulse rounded bg-muted" />
                  <div className="h-5 w-16 animate-pulse rounded bg-muted" />
                </div>
              ))}
            </div>
          ) : recent.results.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground text-sm">
              No organisations yet.{' '}
              <Link to="/ct/organisations/new" className="text-primary hover:underline">Create one</Link>.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Licences</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {recent.results.slice(0, 5).map((org) => (
                  <tr key={org.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <Link to={`/ct/organisations/${org.id}`} className="font-medium text-foreground hover:text-primary">
                        {org.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[org.status] ?? 'bg-gray-100 text-gray-800'}`}>
                        {org.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{org.licence_count}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
