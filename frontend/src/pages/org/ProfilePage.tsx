import { useState } from 'react'
import { Building2, Landmark, Mail, Phone } from 'lucide-react'
import { toast } from 'sonner'

import {
  useCreateOrgAddress,
  useDeactivateOrgAddress,
  useOrgProfile,
  useUpdateOrgAddress,
  useUpdateOrgProfile,
} from '@/hooks/useOrgAdmin'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { AppDialog } from '@/components/ui/AppDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  getAddressCountryName,
  getAddressCountryOption,
  getAddressCountryRule,
  getBillingTaxLabel,
  getSubdivisionName,
  getSubdivisionOptions,
  resolveSubdivisionCode,
} from '@/lib/addressMetadata'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, startCase } from '@/lib/format'
import {
  COUNTRY_OPTIONS,
  CURRENCY_OPTIONS,
  DEFAULT_COUNTRY_OPTION,
  ORGANISATION_ENTITY_TYPE_OPTIONS,
  getCountryOption,
} from '@/lib/organisationMetadata'
import type { OrganisationAddress, OrganisationAddressType, OrganisationEntityType } from '@/types/organisation'

const mandatoryAddressTypes: OrganisationAddressType[] = ['REGISTERED', 'BILLING']
const COUNTRY_SELECT_OPTIONS = COUNTRY_OPTIONS.map((country) => ({
  value: country.code,
  label: country.name,
  hint: `${country.dialCode} • ${country.defaultCurrency}`,
  keywords: [country.dialCode, country.defaultCurrency],
}))
const CURRENCY_SELECT_OPTIONS = CURRENCY_OPTIONS.map((currency) => ({
  value: currency.code,
  label: currency.label,
}))
const ENTITY_TYPE_OPTIONS = ORGANISATION_ENTITY_TYPE_OPTIONS.map((option) => ({
  value: option.value,
  label: option.label,
}))
const ADDRESS_TYPE_OPTIONS = ['REGISTERED', 'BILLING', 'HEADQUARTERS', 'WAREHOUSE', 'CUSTOM'].map((type) => ({
  value: type,
  label: startCase(type),
}))

const createEmptyAddressForm = (countryCode = DEFAULT_COUNTRY_OPTION.code) => ({
  address_type: 'CUSTOM' as OrganisationAddressType,
  label: '',
  line1: '',
  line2: '',
  city: '',
  state: '',
  state_code: '',
  country: getAddressCountryName(countryCode),
  country_code: countryCode,
  pincode: '',
  gstin: '',
})

export function OrgProfilePage() {
  const { data, isLoading } = useOrgProfile()
  const updateProfileMutation = useUpdateOrgProfile()
  const createAddressMutation = useCreateOrgAddress()
  const updateAddressMutation = useUpdateOrgAddress()
  const deactivateAddressMutation = useDeactivateOrgAddress()

  const [profileDraft, setProfileDraft] = useState<Partial<{
    name: string
    pan_number: string
    country_code: string
    currency: string
    entity_type: OrganisationEntityType
  }>>({})
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null)
  const [isAddressModalOpen, setIsAddressModalOpen] = useState(false)
  const [addressForm, setAddressForm] = useState(() => createEmptyAddressForm())
  const [hasCurrencyManualOverride, setHasCurrencyManualOverride] = useState(false)

  if (isLoading || !data) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={5} />
        <SkeletonTable rows={5} />
      </div>
    )
  }

  const profileForm = {
    name: profileDraft.name ?? data.name,
    pan_number: profileDraft.pan_number ?? data.pan_number ?? '',
    country_code: profileDraft.country_code ?? data.country_code,
    currency: profileDraft.currency ?? data.currency,
    entity_type: profileDraft.entity_type ?? data.entity_type,
  }
  const selectedCountry = getCountryOption(profileForm.country_code) ?? DEFAULT_COUNTRY_OPTION
  const addressCountry = getAddressCountryOption(addressForm.country_code || addressForm.country) ?? selectedCountry
  const addressRule = getAddressCountryRule(addressCountry.code)
  const addressSubdivisions = getSubdivisionOptions(addressCountry.code)

  const setAddressCountry = (countryCode: string) => {
    setAddressForm((current) => ({
      ...current,
      country_code: countryCode,
      country: getAddressCountryName(countryCode),
      state: '',
      state_code: '',
      pincode: '',
    }))
  }

  const setAddressState = (stateCode: string) => {
    setAddressForm((current) => ({
      ...current,
      state_code: stateCode,
      state: getSubdivisionName(addressCountry.code, stateCode, ''),
    }))
  }

  const handleCountryChange = (nextCountryCode: string) => {
    setProfileDraft((current) => {
      const previousCountry = getCountryOption(current.country_code ?? data.country_code) ?? DEFAULT_COUNTRY_OPTION
      const currentCurrency = current.currency ?? data.currency
      const nextCountry = getCountryOption(nextCountryCode) ?? DEFAULT_COUNTRY_OPTION
      const shouldAutoUpdateCurrency = !hasCurrencyManualOverride || currentCurrency === previousCountry.defaultCurrency

      return {
        ...current,
        country_code: nextCountryCode,
        currency: shouldAutoUpdateCurrency ? nextCountry.defaultCurrency : currentCurrency,
      }
    })
    if (!hasCurrencyManualOverride || profileForm.currency === selectedCountry.defaultCurrency) {
      setHasCurrencyManualOverride(false)
    }
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

  const openCreateAddressModal = () => {
    setEditingAddressId(null)
    setAddressForm(createEmptyAddressForm(selectedCountry.code))
    setIsAddressModalOpen(true)
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
      state_code: address.state_code,
      country: address.country,
      country_code: address.country_code,
      pincode: address.pincode,
      gstin: address.gstin ?? '',
    })
    setIsAddressModalOpen(true)
  }

  const resetAddressForm = () => {
    setEditingAddressId(null)
    setAddressForm(createEmptyAddressForm(selectedCountry.code))
    setIsAddressModalOpen(false)
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

  const handleDeactivate = async (address: OrganisationAddress) => {
    if (mandatoryAddressTypes.includes(address.address_type)) return
    try {
      await deactivateAddressMutation.mutateAsync(address.id)
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
        description="Maintain the legal profile and address directory used across onboarding, billing, and workspace configuration."
      />

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <SectionCard
          title="Core profile"
          description="These details define the legal identity used across the organisation workspace."
        >
          <form onSubmit={handleProfileSave} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="name">
                Organisation name
              </label>
              <input
                id="name"
                className="field-input"
                value={profileForm.name}
                onChange={(event) => setProfileDraft((current) => ({ ...current, name: event.target.value }))}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="pan_number">
                PAN number
              </label>
              <input
                id="pan_number"
                className="field-input"
                value={profileForm.pan_number}
                onChange={(event) => setProfileDraft((current) => ({ ...current, pan_number: event.target.value }))}
                required
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="field-label" htmlFor="country_code">
                  Country
                </label>
                <AppSelect
                  id="country_code"
                  value={profileForm.country_code}
                  onValueChange={handleCountryChange}
                  options={COUNTRY_SELECT_OPTIONS}
                  placeholder="Select country"
                />
              </div>
              <div>
                <label className="field-label" htmlFor="currency">
                  Currency
                </label>
                <AppSelect
                  id="currency"
                  value={profileForm.currency}
                  onValueChange={(value) => {
                    setProfileDraft((current) => ({ ...current, currency: value }))
                    setHasCurrencyManualOverride(true)
                  }}
                  options={CURRENCY_SELECT_OPTIONS}
                  placeholder="Select currency"
                />
              </div>
            </div>
            <div>
              <label className="field-label" htmlFor="entity_type">
                Organisation entity type
              </label>
              <AppSelect
                id="entity_type"
                value={profileForm.entity_type}
                onValueChange={(value) =>
                  setProfileDraft((current) => ({
                    ...current,
                    entity_type: value as OrganisationEntityType,
                  }))
                }
                options={ENTITY_TYPE_OPTIONS}
                placeholder="Select entity type"
              />
            </div>
            <button type="submit" className="btn-primary" disabled={updateProfileMutation.isPending}>
              Save organisation profile
            </button>
          </form>
        </SectionCard>

        <SectionCard
          title="Bootstrap admin"
          description="This is the primary organisation admin captured during Control Tower onboarding."
        >
          {data.bootstrap_admin ? (
            <div className="space-y-4">
              <div className="surface-muted rounded-[24px] p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                  Primary admin
                </p>
                <p className="mt-3 text-xl font-semibold text-[hsl(var(--foreground-strong))]">
                  {data.bootstrap_admin.full_name}
                </p>
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                      <Mail className="h-4 w-4 text-[hsl(var(--brand))]" />
                      Email
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {data.bootstrap_admin.email}
                    </p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-[hsl(var(--foreground-strong))]">
                      <Phone className="h-4 w-4 text-[hsl(var(--brand))]" />
                      Phone
                    </div>
                    <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                      {data.bootstrap_admin.phone || 'Not provided'}
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <StatusBadge tone="info">{data.bootstrap_admin.status.replace(/_/g, ' ')}</StatusBadge>
                  {data.bootstrap_admin.invitation_sent_at ? (
                    <span className="text-xs uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                      Invited {formatDate(data.bootstrap_admin.invitation_sent_at)}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No bootstrap admin found"
              description="Control Tower assigns the primary organisation admin during organisation creation."
              icon={Mail}
            />
          )}
        </SectionCard>
      </div>

      <SectionCard
        title="Address directory"
        description="Registered and billing addresses stay active permanently. Additional operational addresses can be added, edited, or deactivated here."
        action={
          <button type="button" className="btn-primary" onClick={openCreateAddressModal}>
            Add address
          </button>
        }
      >
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
                    {getBillingTaxLabel(address.country_code)} {address.gstin || 'Not configured'} • Modified {formatDate(address.modified_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={() => handleAddressEdit(address)} className="btn-secondary">
                    Edit
                  </button>
                  {!mandatoryAddressTypes.includes(address.address_type) && address.is_active ? (
                    <ConfirmDialog
                      trigger={
                        <button type="button" className="btn-danger">
                          Deactivate
                        </button>
                      }
                      title="Deactivate address?"
                      description="This address will remain in history but will no longer be available for active configuration."
                      confirmLabel="Deactivate"
                      onConfirm={() => handleDeactivate(address)}
                    />
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No addresses configured yet"
            description="Add organisation addresses so office locations can be linked to legal or operational sites."
            icon={Building2}
          />
        )}
      </SectionCard>

      <AppDialog
        open={isAddressModalOpen}
        onOpenChange={(open) => {
          setIsAddressModalOpen(open)
          if (!open) {
            resetAddressForm()
          }
        }}
        title={editingAddressId ? 'Edit address' : 'Add address'}
        description="Use the same modal to maintain registered, billing, and operational organisation addresses."
        footer={
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className="btn-secondary" onClick={resetAddressForm}>
              Cancel
            </button>
            <button
              type="submit"
              form="org-address-form"
              className="btn-primary"
              disabled={createAddressMutation.isPending || updateAddressMutation.isPending}
            >
              {editingAddressId ? 'Save address' : 'Add address'}
            </button>
          </div>
        }
      >
        <form id="org-address-form" onSubmit={handleAddressSubmit} className="grid gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="address_type">
                Address type
              </label>
              <AppSelect
                id="address_type"
                value={addressForm.address_type}
                onValueChange={(value) =>
                  setAddressForm((current) => ({
                    ...current,
                    address_type: value as OrganisationAddressType,
                  }))
                }
                options={ADDRESS_TYPE_OPTIONS}
                placeholder="Select address type"
              />
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
          <div>
            <label className="field-label" htmlFor="line1">
              Address line 1
            </label>
            <input
              id="line1"
              className="field-input"
              value={addressForm.line1}
              onChange={(event) => setAddressForm((current) => ({ ...current, line1: event.target.value }))}
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="line2">
              Address line 2
            </label>
            <input
              id="line2"
              className="field-input"
              value={addressForm.line2}
              onChange={(event) => setAddressForm((current) => ({ ...current, line2: event.target.value }))}
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="address-country">
                Country
              </label>
              <AppSelect
                id="address-country"
                value={addressCountry.code}
                onValueChange={setAddressCountry}
                options={COUNTRY_SELECT_OPTIONS}
                placeholder="Select country"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="city">
                City
              </label>
              <input
                id="city"
                className="field-input"
                value={addressForm.city}
                onChange={(event) => setAddressForm((current) => ({ ...current, city: event.target.value }))}
                required
              />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="address-state">
                {addressRule.subdivisionLabel}
              </label>
              {addressSubdivisions.length > 0 ? (
                <AppSelect
                  id="address-state"
                  value={resolveSubdivisionCode(addressCountry.code, addressForm.state, addressForm.state_code)}
                  onValueChange={setAddressState}
                  options={addressSubdivisions.map((option) => ({
                    value: option.code,
                    label: option.label,
                    hint: option.taxRegionCode ? `Tax region ${option.taxRegionCode}` : undefined,
                  }))}
                  placeholder={`Select ${addressRule.subdivisionLabel.toLowerCase()}`}
                />
              ) : (
                <input
                  id="address-state"
                  className="field-input"
                  value={addressForm.state}
                  onChange={(event) => setAddressForm((current) => ({ ...current, state: event.target.value }))}
                  required
                />
              )}
            </div>
            <div>
              <label className="field-label" htmlFor="pincode">
                {addressRule.postalLabel}
              </label>
              <input
                id="pincode"
                className="field-input"
                value={addressForm.pincode}
                placeholder={addressRule.postalPlaceholder}
                onChange={(event) => setAddressForm((current) => ({ ...current, pincode: event.target.value }))}
                required={addressRule.postalRequired !== false}
              />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="gstin">
              {getBillingTaxLabel(addressCountry.code)}
            </label>
            <input
              id="gstin"
              className="field-input"
              value={addressForm.gstin}
              onChange={(event) => setAddressForm((current) => ({ ...current, gstin: event.target.value }))}
              required={addressForm.address_type === 'BILLING' && addressCountry.code === 'IN'}
            />
            <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
              {addressRule.taxHelperText || 'Capture the billing tax registration for invoicing and statutory use.'}
            </p>
          </div>
        </form>
      </AppDialog>
    </div>
  )
}
