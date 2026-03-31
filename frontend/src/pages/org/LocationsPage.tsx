import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import { toast } from 'sonner'

import {
  useCreateLocation,
  useDeactivateLocation,
  useLocations,
  useOrgProfile,
  useUpdateLocation,
} from '@/hooks/useOrgAdmin'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = {
  name: '',
  organisation_address_id: '',
  is_remote: false,
}

export function LocationsPage() {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)

  const { data, isLoading } = useLocations(includeInactive)
  const { data: organisation } = useOrgProfile()
  const createMutation = useCreateLocation()
  const updateMutation = useUpdateLocation()
  const deactivateMutation = useDeactivateLocation()

  const activeAddresses = organisation?.addresses.filter((address) => address.is_active) ?? []

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, payload: form })
        toast.success('Location updated.')
      } else {
        await createMutation.mutateAsync(form)
        toast.success('Location created.')
      }
      resetForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save location.'))
    }
  }

  const handleEdit = (location: NonNullable<typeof data>[number]) => {
    setEditingId(location.id)
    setForm({
      name: location.name,
      organisation_address_id: location.organisation_address_id ?? '',
      is_remote: location.is_remote,
    })
  }

  const handleDeactivate = async (id: string) => {
    if (!window.confirm('Deactivate this location?')) return
    try {
      await deactivateMutation.mutateAsync(id)
      toast.success('Location deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate location.'))
    }
  }

  return (
    <div className="space-y-6">
      {isLoading && !data ? (
        <SkeletonPageHeader />
      ) : (
        <PageHeader
          eyebrow="Master data"
          title="Office locations"
          description="Every office location must link to an organisation address. Employees can only be assigned to office locations."
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard
          title={editingId ? 'Edit location' : 'Add location'}
          description="Choose an active organisation address first, then name the office location."
        >
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="location-name">
                Location name
              </label>
              <input
                id="location-name"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                className="field-input"
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="location-address">
                Linked address
              </label>
              <select
                id="location-address"
                className="field-select"
                value={form.organisation_address_id}
                onChange={(event) => setForm((current) => ({ ...current, organisation_address_id: event.target.value }))}
                required
              >
                <option value="">Select an organisation address</option>
                {activeAddresses.map((address) => (
                  <option key={address.id} value={address.id}>
                    {address.label} • {address.city}, {address.state}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
                Need another address first? <Link to="/org/profile" className="font-semibold text-[hsl(var(--brand))] hover:underline">Manage organisation addresses</Link>
              </p>
            </div>
            <label className="flex items-center gap-3 rounded-[18px] border border-[hsl(var(--border)_/_0.9)] px-4 py-3 text-sm text-[hsl(var(--foreground))]">
              <input
                type="checkbox"
                checked={form.is_remote}
                onChange={(event) => setForm((current) => ({ ...current, is_remote: event.target.checked }))}
              />
              Mark as remote office location
            </label>
            <div className="flex flex-wrap gap-3">
              {editingId ? (
                <button type="button" onClick={resetForm} className="btn-secondary">
                  Cancel
                </button>
              ) : null}
              <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingId ? 'Save changes' : 'Create location'}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard
          title="Location directory"
          description="Inactive locations remain in history but cannot receive invited, pending, or active employees."
          action={
            <label className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => setIncludeInactive(event.target.checked)}
              />
              Show inactive
            </label>
          }
        >
          {isLoading ? (
            <SkeletonTable rows={5} />
          ) : data && data.length > 0 ? (
            <div className="space-y-3">
              {data.map((location) => (
                <div key={location.id} className="surface-muted flex flex-col gap-4 rounded-[24px] p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-[hsl(var(--brand))]" />
                        <p className="font-semibold text-[hsl(var(--foreground-strong))]">{location.name}</p>
                      </div>
                      <StatusBadge tone={location.is_active ? 'success' : 'warning'}>
                        {location.is_active ? 'Active' : 'Inactive'}
                      </StatusBadge>
                      {location.is_remote ? <StatusBadge tone="info">Remote</StatusBadge> : null}
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {location.organisation_address
                        ? `${location.organisation_address.label} • ${[location.address, location.city, location.state, location.country, location.pincode].filter(Boolean).join(', ')}`
                        : 'No linked address'}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                      Updated {formatDate(location.updated_at)}
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <button type="button" onClick={() => handleEdit(location)} className="btn-secondary">
                      Edit
                    </button>
                    {location.is_active ? (
                      <button type="button" onClick={() => handleDeactivate(location.id)} className="btn-danger">
                        Deactivate
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No locations added yet"
              description="Create the first office location so invited and active employees can be assigned to a real worksite."
              icon={MapPin}
            />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
