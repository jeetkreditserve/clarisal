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
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
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
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)

  const { data, isLoading } = useLocations(includeInactive)
  const { data: organisation } = useOrgProfile()
  const createMutation = useCreateLocation()
  const updateMutation = useUpdateLocation()
  const deactivateMutation = useDeactivateLocation()

  const activeAddresses = organisation?.addresses.filter((address) => address.is_active) ?? []
  const addressOptions = activeAddresses.map((address) => ({
    value: address.id,
    label: `${address.label} • ${address.city}, ${address.state}`,
  }))

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
    setIsModalOpen(false)
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
    setIsModalOpen(true)
  }

  const handleDeactivate = async (id: string) => {
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
          description="Every office location links to an organisation address. Use modal-based create and edit actions to keep the page focused on the directory."
          actions={
            <button type="button" className="btn-primary" onClick={() => setIsModalOpen(true)}>
              Add location
            </button>
          }
        />
      )}

      <SectionCard
        title="Location directory"
        description="Inactive locations remain in history but cannot receive invited, pending, or active employees."
        action={
          <AppCheckbox
            id="locations-include-inactive"
            checked={includeInactive}
            onCheckedChange={setIncludeInactive}
            label="Show inactive"
          />
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
                    Modified {formatDate(location.modified_at)}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => handleEdit(location)} className="btn-secondary">
                    Edit
                  </button>
                  {location.is_active ? (
                    <ConfirmDialog
                      trigger={
                        <button type="button" className="btn-danger">
                          Deactivate
                        </button>
                      }
                      title="Deactivate location?"
                      description="Inactive locations stay in history but cannot be assigned to invited or active employees."
                      confirmLabel="Deactivate"
                      onConfirm={() => handleDeactivate(location.id)}
                    />
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No locations added yet"
            description="Create the first office location so invited and active employees can be assigned to a worksite."
            icon={MapPin}
          />
        )}
      </SectionCard>

      <AppDialog
        open={isModalOpen}
        onOpenChange={(open) => {
          setIsModalOpen(open)
          if (!open) {
            resetForm()
          }
        }}
        title={editingId ? 'Edit location' : 'Add location'}
        description="Choose an active organisation address first, then name the office location."
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" onClick={resetForm} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" form="location-form" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingId ? 'Save changes' : 'Create location'}
            </button>
          </div>
        }
      >
        <form id="location-form" onSubmit={handleSubmit} className="grid gap-4">
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
            <AppSelect
              id="location-address"
              value={form.organisation_address_id}
              onValueChange={(value) =>
                setForm((current) => ({ ...current, organisation_address_id: value }))
              }
              options={addressOptions}
              placeholder="Select an organisation address"
            />
            <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
              Need another address first?{' '}
              <Link to="/org/profile" className="font-semibold text-[hsl(var(--brand))] hover:underline">
                Manage organisation addresses
              </Link>
            </p>
          </div>
          <AppCheckbox
            id="location-remote"
            checked={form.is_remote}
            onCheckedChange={(checked) => setForm((current) => ({ ...current, is_remote: checked }))}
            label="Mark as remote office location"
          />
        </form>
      </AppDialog>
    </div>
  )
}
