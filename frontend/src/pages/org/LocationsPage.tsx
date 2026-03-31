import { useState } from 'react'
import { MapPin } from 'lucide-react'
import { toast } from 'sonner'
import { useCreateLocation, useDeactivateLocation, useLocations, useUpdateLocation } from '@/hooks/useOrgAdmin'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate } from '@/lib/format'
import { getErrorMessage } from '@/lib/errors'

const emptyForm = {
  name: '',
  address: '',
  city: '',
  state: '',
  country: '',
  pincode: '',
}

export function LocationsPage() {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)

  const { data, isLoading } = useLocations(includeInactive)
  const createMutation = useCreateLocation()
  const updateMutation = useUpdateLocation()
  const deactivateMutation = useDeactivateLocation()

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
      address: location.address,
      city: location.city,
      state: location.state,
      country: location.country,
      pincode: location.pincode,
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
      <PageHeader
        eyebrow="Master data"
        title="Office locations"
        description="Maintain the office sites employees can be assigned to."
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title={editingId ? 'Edit location' : 'Add location'} description="Capture a valid worksite or office assignment option.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            {(['name', 'city', 'state', 'country', 'pincode'] as const).map((field) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {field === 'pincode' ? 'Postal code' : field.charAt(0).toUpperCase() + field.slice(1)}
                </label>
                <input
                  id={field}
                  value={form[field]}
                  onChange={(event) => setForm((current) => ({ ...current, [field]: event.target.value }))}
                  className="field-input"
                  required={field === 'name'}
                />
              </div>
            ))}
            <div>
              <label className="field-label" htmlFor="address">
                Address
              </label>
              <textarea
                id="address"
                value={form.address}
                onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))}
                className="field-textarea"
              />
            </div>
            <div className="flex flex-wrap gap-3">
              {editingId ? <button type="button" onClick={resetForm} className="btn-secondary">Cancel</button> : null}
              <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingId ? 'Save changes' : 'Create location'}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard
          title="Location directory"
          description="Every location can be activated or deactivated without losing historical employee references."
          action={
            <label className="flex items-center gap-2 text-sm text-slate-600">
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
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-16" />
              ))}
            </div>
          ) : data && data.length > 0 ? (
            <div className="space-y-3">
              {data.map((location) => (
                <div key={location.id} className="flex flex-col gap-4 rounded-[24px] border border-slate-200 bg-slate-50 p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <MapPin className="h-4 w-4 text-cyan-700" />
                      <p className="font-semibold text-slate-950">{location.name}</p>
                      <StatusBadge tone={location.is_active ? 'success' : 'warning'}>
                        {location.is_active ? 'Active' : 'Inactive'}
                      </StatusBadge>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">
                      {[location.address, location.city, location.state, location.country, location.pincode].filter(Boolean).join(', ') || 'No address provided'}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-500">Updated {formatDate(location.updated_at)}</p>
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
            <p className="text-sm text-slate-500">No locations added yet.</p>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
