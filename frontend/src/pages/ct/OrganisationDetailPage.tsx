import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import {
  useOrganisation, useActivateOrganisation, useSuspendOrganisation,
  useOrgAdmins, useInviteOrgAdmin, useUpdateOrgLicences,
} from '@/hooks/useCtOrganisations'
import { cn } from '@/lib/utils'
import type { OrganisationStatus } from '@/types/organisation'

const STATUS_COLORS: Record<OrganisationStatus, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  PAID: 'bg-blue-100 text-blue-800',
  ACTIVE: 'bg-green-100 text-green-800',
  SUSPENDED: 'bg-red-100 text-red-800',
}

type Tab = 'info' | 'licences' | 'admins' | 'history'

function InviteAdminModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const [form, setForm] = useState({ email: '', first_name: '', last_name: '' })
  const [error, setError] = useState<string | null>(null)
  const { mutateAsync, isPending } = useInviteOrgAdmin(orgId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await mutateAsync(form)
      onClose()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } }
      setError(e.response?.data?.error ?? 'Failed to send invite.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-foreground mb-4">Invite Organisation Admin</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          {(['email', 'first_name', 'last_name'] as const).map((field) => (
            <div key={field}>
              <label className="block text-sm font-medium text-foreground mb-1.5 capitalize">
                {field.replace('_', ' ')}
              </label>
              <input
                type={field === 'email' ? 'email' : 'text'}
                required
                value={form[field]}
                onChange={(e) => setForm(f => ({ ...f, [field]: e.target.value }))}
                className="w-full rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          ))}
          {error && (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border px-4 py-2 text-sm">Cancel</button>
            <button
              type="submit" disabled={isPending}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
            >
              {isPending ? 'Sending…' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function OrganisationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('info')
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const { data: org, isLoading } = useOrganisation(id!)
  const { data: admins } = useOrgAdmins(id!)
  const { mutateAsync: activate } = useActivateOrganisation()
  const { mutateAsync: suspend } = useSuspendOrganisation()
  const { mutateAsync: updateLicences, isPending: updatingLicences } = useUpdateOrgLicences(id!)
  const [newLicenceCount, setNewLicenceCount] = useState<number | null>(null)

  if (isLoading || !org) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="h-48 w-full animate-pulse rounded bg-muted" />
      </div>
    )
  }

  const handleActivate = async () => {
    setActionError(null)
    try { await activate({ id: id! }) } catch { setActionError('Could not activate. Check org status.') }
  }

  const handleSuspend = async () => {
    if (!confirm('Suspend this organisation? Admins will lose access.')) return
    setActionError(null)
    try { await suspend({ id: id! }) } catch { setActionError('Could not suspend.') }
  }

  const handleLicenceUpdate = async () => {
    if (newLicenceCount === null) return
    await updateLicences(newLicenceCount)
    setNewLicenceCount(null)
  }

  const TABS: Array<{ id: Tab; label: string }> = [
    { id: 'info', label: 'Info' },
    { id: 'licences', label: 'Licences' },
    { id: 'admins', label: 'Admins' },
    { id: 'history', label: 'History' },
  ]

  return (
    <div>
      {showInviteModal && <InviteAdminModal orgId={id!} onClose={() => setShowInviteModal(false)} />}

      <button onClick={() => navigate(-1)} className="mb-4 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{org.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[org.status]}`}>
              {org.status}
            </span>
            <span className="text-sm text-muted-foreground">/{org.slug}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {org.status === 'PENDING' && (
            <button onClick={handleActivate}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">
              Mark Paid
            </button>
          )}
          {org.status === 'ACTIVE' && (
            <button onClick={handleSuspend}
              className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700">
              Suspend
            </button>
          )}
          {(org.status === 'PAID' || org.status === 'ACTIVE') && (
            <button onClick={() => setShowInviteModal(true)}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90">
              Invite Admin
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="mt-3 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
          {actionError}
        </div>
      )}

      <div className="mt-6 border-b">
        <div className="flex gap-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                tab === t.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        {tab === 'info' && (
          <div className="rounded-xl border bg-card p-6 shadow-sm space-y-3">
            {[
              ['Name', org.name],
              ['Email', org.email || '—'],
              ['Phone', org.phone || '—'],
              ['Address', org.address || '—'],
              ['Created by', org.created_by_email],
              ['Created', new Date(org.created_at).toLocaleDateString()],
            ].map(([label, value]) => (
              <div key={label} className="flex gap-4 py-2 border-b last:border-0">
                <span className="w-32 shrink-0 text-sm font-medium text-muted-foreground">{label}</span>
                <span className="text-sm text-foreground">{value}</span>
              </div>
            ))}
          </div>
        )}

        {tab === 'licences' && (
          <div className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-6">
              <div>
                <p className="text-sm text-muted-foreground">Total licences</p>
                <p className="text-3xl font-bold text-foreground">{org.licence_count}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number" min={1}
                value={newLicenceCount ?? org.licence_count}
                onChange={(e) => setNewLicenceCount(Number(e.target.value))}
                className="w-32 rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                onClick={handleLicenceUpdate}
                disabled={updatingLicences || newLicenceCount === null}
                className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {updatingLicences ? 'Saving…' : 'Update'}
              </button>
            </div>
          </div>
        )}

        {tab === 'admins' && (
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
            {!admins || admins.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                No admins yet.{' '}
                {(org.status === 'PAID' || org.status === 'ACTIVE') && (
                  <button onClick={() => setShowInviteModal(true)} className="text-primary hover:underline">
                    Invite one
                  </button>
                )}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Email</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {admins.map((admin) => (
                    <tr key={admin.id}>
                      <td className="px-4 py-3 font-medium">{admin.full_name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{admin.email}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${admin.is_active ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {admin.is_active ? 'Active' : 'Pending'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === 'history' && (
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
            {org.state_transitions.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">No state changes yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">From</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">To</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">By</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Note</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">When</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {org.state_transitions.map((t) => (
                    <tr key={t.id}>
                      <td className="px-4 py-3 text-muted-foreground">{t.from_status}</td>
                      <td className="px-4 py-3 font-medium">{t.to_status}</td>
                      <td className="px-4 py-3 text-muted-foreground">{t.transitioned_by_email}</td>
                      <td className="px-4 py-3 text-muted-foreground">{t.note || '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {new Date(t.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
