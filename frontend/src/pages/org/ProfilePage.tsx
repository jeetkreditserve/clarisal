import { useEffect, useState } from 'react'
import { Building2, Landmark } from 'lucide-react'
import { toast } from 'sonner'

import {
  useCreateOrgAddress,
  useDeactivateOrgAddress,
  useOrgProfile,
  useUpdateOrgAddress,
  useUpdateOrgProfile,
} from '@/hooks/useOrgAdmin'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, startCase } from '@/lib/format'
import type { OrganisationAddress, OrganisationAddressType } from '@/types/organisation'

const mandatoryAddressTypes: OrganisationAddressType[] = ['REGISTERED', 'BILLING']

const emptyAddressForm = {
  address_type: 'CUSTOM' as OrganisationAddressType,
  label: '',
  line1: '',
  line2: '',
  city: '',
  state: '',
  country: 'India',
  pincode: '',
  gstin: '',
}

export function OrgProfilePage() {
  const { data, isLoading } = useOrgProfile()
  const updateProfileMutation = useUpdateOrgProfile()
  const createAddressMutation = useCreateOrgAddress()
  const updateAddressMutation = useUpdateOrgAddress()
  const deactivateAddressMutation = useDeactivateOrgAddress()

  const [profileForm, setProfileForm] = useState({
    name: '',
    pan_number: '',
    email: '',
    phone: '',
    country_code: 'IN',
    currency: 'INR',
  })
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null)
  const [addressForm, setAddressForm] = useState(emptyAddressForm)

  useEffect(() => {
    if (!data) return
    setProfileForm({
      name: data.name,
      pan_number: data.pan_number ?? '',
      email: data.email,
      phone: data.phone,
      country_code: data.country_code,
      currency: data.currency,
    })
  }, [data])

  if (isLoading || !data) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={6} />
        <SkeletonTable rows={5} />
      </div>
    )
  }

  const handleProfileSave = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await updateProfileMutation.mutateAsync(profileForm)
      toast.success('Organisation profile updated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update organisation profile.'))
    }
  }

  const handleAddressEdit = (address: OrganisationAddress) => {
    setEditingAddressId(address.id)
    setAddressForm({
      address_type: address.address_type,
      label: address.label,
      line1: address.line1,
      line2: address.line2,
      city: address.city,
      state: address.state,
      country: address.country,
      pincode: address.pincode,
      gstin: address.gstin ?? '',
    })
  }

  const resetAddressForm = () => {
    setEditingAddressId(null)
    setAddressForm(emptyAddressForm)
  }

  const handleAddressSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      ...addressForm,
      label: mandatoryAddressTypes.includes(addressForm.address_type) ? undefined : addressForm.label,
      gstin: addressForm.gstin || null,
    }
    try {
      if (editingAddressId) {
        await updateAddressMutation.mutateAsync({ id: editingAddressId, payload })
        toast.success('Address updated.')
      } else {
        await createAddressMutation.mutateAsync(payload)
        toast.success('Address created.')
      }
      resetAddressForm()
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save address.'))
    }
  }

  const handleDeactivate = async (addressId: string) => {
    if (!window.confirm('Deactivate this address?')) return
    try {
      await deactivateAddressMutation.mutateAsync(addressId)
      toast.success('Address deactivated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to deactivate address.'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Organisation"
        title="Organisation profile"
        description="Maintain legal profile, PAN, and the shared address directory used by office locations."
      />

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <SectionCard title="Core profile" description="These details define the organisation identity used across onboarding and billing operations.">
          <form onSubmit={handleProfileSave} className="grid gap-4">
            {[
              ['name', 'Organisation name'],
              ['pan_number', 'PAN number'],
              ['email', 'Contact email'],
              ['phone', 'Contact phone'],
            ].map(([field, label]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  className="field-input"
                  value={profileForm[field as keyof typeof profileForm]}
                  onChange={(event) => setProfileForm((current) => ({ ...current, [field]: event.target.value }))}
                  required={field === 'name' || field === 'pan_number'}
                />
              </div>
            ))}
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="country_code">
                  Country code
                </label>
                <input
                  id="country_code"
                  className="field-input"
                  value={profileForm.country_code}
                  onChange={(event) => setProfileForm((current) => ({ ...current, country_code: event.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="currency">
                  Currency
                </label>
                <input
                  id="currency"
                  className="field-input"
                  value={profileForm.currency}
                  onChange={(event) => setProfileForm((current) => ({ ...current, currency: event.target.value }))}
                  required
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={updateProfileMutation.isPending}>
              Save organisation profile
            </button>
          </form>
        </SectionCard>

        <SectionCard
          title={editingAddressId ? 'Edit address' : 'Add address'}
          description="Registered and billing addresses are required. Additional headquarters, warehouse, or custom addresses can be added as needed."
        >
          <form onSubmit={handleAddressSubmit} className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="address_type">
                  Address type
                </label>
                <select
                  id="address_type"
                  className="field-select"
                  value={addressForm.address_type}
                  onChange={(event) =>
                    setAddressForm((current) => ({
                      ...current,
                      address_type: event.target.value as OrganisationAddressType,
                    }))
                  }
                >
                  {['REGISTERED', 'BILLING', 'HEADQUARTERS', 'WAREHOUSE', 'CUSTOM'].map((type) => (
                    <option key={type} value={type}>
                      {startCase(type)}
                    </option>
                  ))}
                </select>
              </div>
              {!mandatoryAddressTypes.includes(addressForm.address_type) ? (
                <div>
                  <label className="field-label" htmlFor="label">
                    Address label
                  </label>
                  <input
                    id="label"
                    className="field-input"
                    value={addressForm.label}
                    onChange={(event) => setAddressForm((current) => ({ ...current, label: event.target.value }))}
                    required
                  />
                </div>
              ) : null}
            </div>
            {[
              ['line1', 'Address line 1'],
              ['line2', 'Address line 2'],
              ['city', 'City'],
              ['state', 'State'],
              ['country', 'Country'],
              ['pincode', 'Pincode'],
              ['gstin', 'GSTIN'],
            ].map(([field, label]) => (
              <div key={field}>
                <label className="field-label" htmlFor={field}>
                  {label}
                </label>
                <input
                  id={field}
                  className="field-input"
                  value={addressForm[field as keyof typeof addressForm]}
                  onChange={(event) => setAddressForm((current) => ({ ...current, [field]: event.target.value }))}
                  required={['line1', 'city', 'state', 'pincode'].includes(field)}
                />
              </div>
            ))}
            <div className="flex flex-wrap gap-3">
              {editingAddressId ? (
                <button type="button" onClick={resetAddressForm} className="btn-secondary">
                  Cancel
                </button>
              ) : null}
              <button
                type="submit"
                className="btn-primary"
                disabled={createAddressMutation.isPending || updateAddressMutation.isPending}
              >
                {editingAddressId ? 'Save address' : 'Add address'}
              </button>
            </div>
          </form>
        </SectionCard>
      </div>

      <SectionCard title="Address directory" description="Office locations must link to one of these addresses.">
        {data.addresses.length > 0 ? (
          <div className="space-y-3">
            {data.addresses.map((address) => (
              <div key={address.id} className="surface-muted flex flex-col gap-4 rounded-[24px] p-5 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Landmark className="h-4 w-4 text-[hsl(var(--brand))]" />
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{address.label}</p>
                    </div>
                    <StatusBadge tone={address.is_active ? 'success' : 'warning'}>
                      {address.is_active ? 'Active' : 'Inactive'}
                    </StatusBadge>
                    <StatusBadge tone="info">{address.address_type_label}</StatusBadge>
                  </div>
                  <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                    {[address.line1, address.line2, address.city, address.state, address.country, address.pincode]
                      .filter(Boolean)
                      .join(', ')}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                    GSTIN {address.gstin || 'Not configured'} • Updated {formatDate(address.updated_at)}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => handleAddressEdit(address)} className="btn-secondary">
                    Edit
                  </button>
                  {address.is_active ? (
                    <button type="button" onClick={() => handleDeactivate(address.id)} className="btn-danger">
                      Deactivate
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No addresses configured yet"
            description="Add organisation addresses so office locations can be linked to a legal or operational site."
            icon={Building2}
          />
        )}
      </SectionCard>
    </div>
  )
}
