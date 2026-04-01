import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppSelect } from '@/components/ui/AppSelect'
import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { useCreateOrganisation } from '@/hooks/useCtOrganisations'
import type { OrganisationAddressInput } from '@/lib/api/organisations'
import {
  getAddressCountryName,
  getAddressCountryOption,
  getAddressCountryRule,
  getBillingTaxLabel,
  getSubdivisionName,
  getSubdivisionOptions,
  isBillingTaxRequired,
  resolveCountryCode,
  resolveSubdivisionCode,
  validateBillingTaxIdentifier,
  validatePostalCodeForCountry,
} from '@/lib/addressMetadata'
import { getErrorMessage } from '@/lib/errors'
import {
  COUNTRY_OPTIONS,
  CURRENCY_OPTIONS,
  DEFAULT_COUNTRY_CODE,
  DEFAULT_COUNTRY_OPTION,
  ORGANISATION_ENTITY_TYPE_OPTIONS,
  getCountryOption,
  validatePhoneForCountry,
} from '@/lib/organisationMetadata'
import type { OrganisationEntityType } from '@/types/organisation'

type AddressFormState = OrganisationAddressInput & {
  country_code: string
  state_code: string
}

type AddressFieldKey = keyof AddressFormState

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

const emptyAddress = (
  address_type: 'REGISTERED' | 'BILLING',
  countryCode = DEFAULT_COUNTRY_CODE,
): AddressFormState => ({
  address_type,
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

const syncAddressCountry = (address: AddressFormState, previousCountryCode: string, nextCountryCode: string) => {
  if (!address.country_code || address.country_code === previousCountryCode) {
    return {
      ...address,
      state: '',
      state_code: '',
      country: getAddressCountryName(nextCountryCode),
      country_code: nextCountryCode,
      pincode: '',
    }
  }
  return address
}

const buildBillingAddress = (
  registeredAddress: AddressFormState,
  billingDraft: AddressFormState,
  useRegisteredAddress: boolean,
): AddressFormState => {
  if (!useRegisteredAddress) {
    return billingDraft
  }
  return {
    ...registeredAddress,
    address_type: 'BILLING',
  }
}

export function NewOrganisationPage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending } = useCreateOrganisation()
  const [form, setForm] = useState<{
    name: string
    pan_number: string
    phone: string
    email: string
    country_code: string
    currency: string
    entity_type: OrganisationEntityType
    addresses: {
      REGISTERED: AddressFormState
      BILLING: AddressFormState
    }
  }>({
    name: '',
    pan_number: '',
    phone: '',
    email: '',
    country_code: DEFAULT_COUNTRY_CODE,
    currency: DEFAULT_COUNTRY_OPTION.defaultCurrency,
    entity_type: 'PRIVATE_LIMITED',
    addresses: {
      REGISTERED: emptyAddress('REGISTERED'),
      BILLING: emptyAddress('BILLING'),
    },
  })
  const [billingSameAsRegistered, setBillingSameAsRegistered] = useState(false)
  const [hasCurrencyManualOverride, setHasCurrencyManualOverride] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const selectedCountry = getCountryOption(form.country_code) ?? DEFAULT_COUNTRY_OPTION
  const effectiveBillingAddress = buildBillingAddress(
    form.addresses.REGISTERED,
    form.addresses.BILLING,
    billingSameAsRegistered,
  )

  const setField =
    (field: 'name' | 'pan_number' | 'phone' | 'email') =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setForm((current) => ({ ...current, [field]: event.target.value }))

  const setOrganisationSelectField = (field: 'currency' | 'entity_type', value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
    if (field === 'currency') {
      setHasCurrencyManualOverride(true)
    }
  }

  const handleCountryChange = (nextCountryCode: string) => {
    setForm((current) => {
      const previousCountry = getCountryOption(current.country_code) ?? DEFAULT_COUNTRY_OPTION
      const nextCountry = getCountryOption(nextCountryCode) ?? DEFAULT_COUNTRY_OPTION
      const shouldAutoUpdateCurrency = !hasCurrencyManualOverride || current.currency === previousCountry.defaultCurrency

      return {
        ...current,
        country_code: nextCountryCode,
        currency: shouldAutoUpdateCurrency ? nextCountry.defaultCurrency : current.currency,
        addresses: {
          REGISTERED: syncAddressCountry(current.addresses.REGISTERED, previousCountry.code, nextCountry.code),
          BILLING: syncAddressCountry(current.addresses.BILLING, previousCountry.code, nextCountry.code),
        },
      }
    })
    if (!hasCurrencyManualOverride || form.currency === selectedCountry.defaultCurrency) {
      setHasCurrencyManualOverride(false)
    }
  }

  const setAddressField =
    (addressType: 'REGISTERED' | 'BILLING', field: AddressFieldKey) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((current) => ({
        ...current,
        addresses: {
          ...current.addresses,
          [addressType]: {
            ...current.addresses[addressType],
            [field]: event.target.value,
          },
        },
      }))

  const setAddressCountry = (addressType: 'REGISTERED' | 'BILLING', countryCode: string) => {
    setForm((current) => ({
      ...current,
      addresses: {
        ...current.addresses,
        [addressType]: {
          ...current.addresses[addressType],
          country_code: countryCode,
          country: getAddressCountryName(countryCode),
          state: '',
          state_code: '',
          pincode: '',
          gstin: current.addresses[addressType].gstin ?? '',
        },
      },
    }))
  }

  const setAddressState = (addressType: 'REGISTERED' | 'BILLING', stateCode: string) => {
    const countryCode = form.addresses[addressType].country_code
    setForm((current) => ({
      ...current,
      addresses: {
        ...current.addresses,
        [addressType]: {
          ...current.addresses[addressType],
          state_code: stateCode,
          state: getSubdivisionName(countryCode, stateCode, ''),
        },
      },
    }))
  }

  const addressErrorKey = (addressType: 'REGISTERED' | 'BILLING', field: string) => `${addressType}.${field}`

  const validateForm = () => {
    const nextErrors: Record<string, string> = {}
    const phoneError = validatePhoneForCountry(form.phone, form.country_code)
    if (phoneError) {
      nextErrors.phone = phoneError
    }

    ;(['REGISTERED', 'BILLING'] as const).forEach((addressType) => {
      const address = addressType === 'BILLING' ? effectiveBillingAddress : form.addresses[addressType]
      const countryCode = resolveCountryCode(address.country_code || address.country || form.country_code)
      const stateCode = resolveSubdivisionCode(countryCode, address.state, address.state_code)

      const postalError = validatePostalCodeForCountry(address.pincode, countryCode)
      if (postalError) {
        nextErrors[addressErrorKey(addressType, 'pincode')] = postalError
      }

      const billingTaxError = validateBillingTaxIdentifier({
        addressType,
        countryCode,
        stateCode,
        panNumber: form.pan_number,
        identifier: address.gstin,
      })
      if (billingTaxError) {
        const targetAddressType = billingSameAsRegistered && addressType === 'BILLING' ? 'REGISTERED' : addressType
        nextErrors[addressErrorKey(targetAddressType, 'gstin')] = billingTaxError
      }
    })

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!validateForm()) {
      return
    }
    try {
      const organisation = await mutateAsync({
        name: form.name,
        pan_number: form.pan_number,
        phone: form.phone,
        email: form.email,
        country_code: form.country_code,
        currency: form.currency,
        entity_type: form.entity_type,
        addresses: [form.addresses.REGISTERED, effectiveBillingAddress],
      })
      toast.success('Organisation created.')
      navigate(`/ct/organisations/${organisation.id}`)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to create organisation.'))
    }
  }

  const renderAddressForm = (addressType: 'REGISTERED' | 'BILLING') => {
    const address = form.addresses[addressType]
    const addressCountry = getAddressCountryOption(address.country_code || address.country) ?? DEFAULT_COUNTRY_OPTION
    const addressRule = getAddressCountryRule(addressCountry.code)
    const subdivisions = getSubdivisionOptions(addressCountry.code)
    const gstLabel = getBillingTaxLabel(addressCountry.code)
    const showGstAsRequired =
      (addressType === 'BILLING' && isBillingTaxRequired(addressCountry.code)) ||
      (addressType === 'REGISTERED' && billingSameAsRegistered && isBillingTaxRequired(addressCountry.code))

    return (
      <div className="grid gap-4">
        <div>
          <label className="field-label" htmlFor={`${addressType}-line1`}>
            Address line 1
            <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
          </label>
          <input
            id={`${addressType}-line1`}
            className="field-input"
            required
            value={address.line1}
            onChange={setAddressField(addressType, 'line1')}
          />
        </div>
        <div>
          <label className="field-label" htmlFor={`${addressType}-line2`}>
            Address line 2
          </label>
          <input
            id={`${addressType}-line2`}
            className="field-input"
            value={address.line2 ?? ''}
            onChange={setAddressField(addressType, 'line2')}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor={`${addressType}-country`}>
              Country
              <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
            </label>
            <AppSelect
              id={`${addressType}-country`}
              value={addressCountry.code}
              onValueChange={(value) => setAddressCountry(addressType, value)}
              options={COUNTRY_SELECT_OPTIONS}
              placeholder="Select country"
            />
          </div>
          <div>
            <label className="field-label" htmlFor={`${addressType}-city`}>
              City
              <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
            </label>
            <input
              id={`${addressType}-city`}
              className="field-input"
              required
              value={address.city}
              onChange={setAddressField(addressType, 'city')}
            />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor={`${addressType}-state`}>
              {addressRule.subdivisionLabel}
              <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
            </label>
            {subdivisions.length > 0 ? (
              <AppSelect
                id={`${addressType}-state`}
                value={resolveSubdivisionCode(addressCountry.code, address.state, address.state_code)}
                onValueChange={(value) => setAddressState(addressType, value)}
                options={subdivisions.map((option) => ({
                  value: option.code,
                  label: option.label,
                  hint: option.taxRegionCode ? `Tax region ${option.taxRegionCode}` : undefined,
                }))}
                placeholder={`Select ${addressRule.subdivisionLabel.toLowerCase()}`}
              />
            ) : (
              <input
                id={`${addressType}-state`}
                className="field-input"
                value={address.state}
                onChange={setAddressField(addressType, 'state')}
                required
              />
            )}
          </div>
          <div>
            <label className="field-label" htmlFor={`${addressType}-pincode`}>
              {addressRule.postalLabel}
              {addressRule.postalRequired === false ? null : <span className="ml-1 text-[hsl(var(--destructive))]">*</span>}
            </label>
            <input
              id={`${addressType}-pincode`}
              className="field-input"
              required={addressRule.postalRequired !== false}
              value={address.pincode}
              placeholder={addressRule.postalPlaceholder}
              onChange={setAddressField(addressType, 'pincode')}
            />
            <FieldErrorText message={fieldErrors[addressErrorKey(addressType, 'pincode')]} />
          </div>
        </div>
        <div>
          <label className="field-label" htmlFor={`${addressType}-gstin`}>
            {gstLabel}
            {showGstAsRequired ? <span className="ml-1 text-[hsl(var(--destructive))]">*</span> : null}
          </label>
          <input
            id={`${addressType}-gstin`}
            className="field-input"
            required={showGstAsRequired}
            value={address.gstin ?? ''}
            placeholder={addressRule.taxPlaceholder}
            onChange={setAddressField(addressType, 'gstin')}
          />
          <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
            {billingSameAsRegistered && addressType === 'REGISTERED'
              ? `${gstLabel} will also be saved on the billing address because billing is set to the registered address.`
              : addressRule.taxHelperText || `${gstLabel} is optional unless your billing country requires it.`}
          </p>
          <FieldErrorText message={fieldErrors[addressErrorKey(addressType, 'gstin')]} />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Provisioning"
        title="Create organisation"
        description="Capture the legal profile first. Registered and billing addresses plus PAN are required before activation."
      />

      <SectionCard title="Organisation details" description="This creates the tenant shell and the default office locations derived from Control Tower addresses.">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <label htmlFor="name" className="field-label">
                Organisation name
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <input id="name" required value={form.name} onChange={setField('name')} className="field-input" />
            </div>
            <div>
              <label htmlFor="pan_number" className="field-label">
                PAN number
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <input id="pan_number" required value={form.pan_number} onChange={setField('pan_number')} className="field-input" />
            </div>
            <div>
              <label htmlFor="email" className="field-label">
                Contact email
              </label>
              <input id="email" type="email" value={form.email} onChange={setField('email')} className="field-input" />
            </div>
            <div>
              <label htmlFor="phone" className="field-label">
                Contact phone
              </label>
              <input id="phone" value={form.phone} onChange={setField('phone')} className="field-input" />
              <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">
                Must start with {selectedCountry.dialCode} for {selectedCountry.name}.
              </p>
              <FieldErrorText message={fieldErrors.phone} />
            </div>
            <div>
              <label htmlFor="country_code" className="field-label">
                Country
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <AppSelect
                id="country_code"
                value={form.country_code}
                onValueChange={handleCountryChange}
                options={COUNTRY_SELECT_OPTIONS}
                placeholder="Select country"
              />
            </div>
            <div>
              <label htmlFor="currency" className="field-label">
                Currency
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <AppSelect
                id="currency"
                value={form.currency}
                onValueChange={(value) => setOrganisationSelectField('currency', value)}
                options={CURRENCY_SELECT_OPTIONS}
                placeholder="Select currency"
              />
            </div>
            <div className="lg:col-span-2">
              <label htmlFor="entity_type" className="field-label">
                Organisation entity type
                <span className="ml-1 text-[hsl(var(--destructive))]">*</span>
              </label>
              <AppSelect
                id="entity_type"
                value={form.entity_type}
                onValueChange={(value) => setOrganisationSelectField('entity_type', value)}
                options={ENTITY_TYPE_OPTIONS}
                placeholder="Select entity type"
              />
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard
              title="Registered address"
              description="This is the statutory address kept on record for the organisation."
            >
              {renderAddressForm('REGISTERED')}
            </SectionCard>

            <SectionCard
              title="Billing address"
              description="This address is used for billing and must carry billing tax registration where required."
            >
              <div className="mb-4">
                <AppCheckbox
                  id="billing-same-as-registered"
                  checked={billingSameAsRegistered}
                  onCheckedChange={setBillingSameAsRegistered}
                  label="Same as registered address"
                  description="Save a separate billing address row using the registered address values, including the tax registration."
                />
              </div>

              {billingSameAsRegistered ? (
                <div className="surface-muted rounded-[24px] p-4 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">
                    Billing address will mirror the registered office.
                  </p>
                  <p className="mt-2">
                    {[
                      effectiveBillingAddress.line1,
                      effectiveBillingAddress.line2,
                      effectiveBillingAddress.city,
                      effectiveBillingAddress.state,
                      effectiveBillingAddress.country,
                      effectiveBillingAddress.pincode,
                    ]
                      .filter(Boolean)
                      .join(', ') || `The billing address will default to ${getAddressCountryName(form.country_code)} once you fill the registered address.`}
                  </p>
                  {effectiveBillingAddress.gstin ? (
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">
                      {getBillingTaxLabel(effectiveBillingAddress.country_code)}: {effectiveBillingAddress.gstin}
                    </p>
                  ) : null}
                </div>
              ) : (
                renderAddressForm('BILLING')
              )}
            </SectionCard>
          </div>

          <div className="surface-muted rounded-[26px] p-5 text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            <p className="font-semibold text-[hsl(var(--foreground-strong))]">Provisioning note</p>
            <p className="mt-2">
              Control Tower can add more addresses later. Every Control Tower address automatically creates a linked office
              location so org admins can start assigning employees immediately.
            </p>
          </div>

          {error ? <div className="notice-error">{error}</div> : null}

          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isPending} className="btn-primary">
              {isPending ? 'Creating organisation...' : 'Create organisation'}
            </button>
          </div>
        </form>
      </SectionCard>
    </div>
  )
}
