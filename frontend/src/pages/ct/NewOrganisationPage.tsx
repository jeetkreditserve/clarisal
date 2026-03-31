import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { useCreateOrganisation } from '@/hooks/useCtOrganisations'
import { getErrorMessage } from '@/lib/errors'
import type { OrganisationAddressInput } from '@/lib/api/organisations'

const emptyAddress = (address_type: 'REGISTERED' | 'BILLING'): OrganisationAddressInput => ({
  address_type,
  line1: '',
  line2: '',
  city: '',
  state: '',
  country: 'India',
  pincode: '',
  gstin: '',
})

export function NewOrganisationPage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending } = useCreateOrganisation()
  const [form, setForm] = useState({
    name: '',
    pan_number: '',
    phone: '',
    email: '',
    country_code: 'IN',
    currency: 'INR',
    addresses: {
      REGISTERED: emptyAddress('REGISTERED'),
      BILLING: emptyAddress('BILLING'),
    },
  })
  const [error, setError] = useState<string | null>(null)

  const setField = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [field]: event.target.value }))

  const setAddressField =
    (addressType: 'REGISTERED' | 'BILLING', field: keyof OrganisationAddressInput) =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    try {
      const organisation = await mutateAsync({
        name: form.name,
        pan_number: form.pan_number,
        phone: form.phone,
        email: form.email,
        country_code: form.country_code,
        currency: form.currency,
        addresses: [form.addresses.REGISTERED, form.addresses.BILLING],
      })
      toast.success('Organisation created.')
      navigate(`/ct/organisations/${organisation.id}`)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to create organisation.'))
    }
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
            {[
              ['name', 'Organisation name', true],
              ['pan_number', 'PAN number', true],
              ['email', 'Contact email', false],
              ['phone', 'Contact phone', false],
              ['country_code', 'Country code', true],
              ['currency', 'Currency', true],
            ].map(([field, label, required]) => (
              <div key={field}>
                <label htmlFor={field} className="field-label">
                  {label}
                  {required ? <span className="ml-1 text-[hsl(var(--destructive))]">*</span> : null}
                </label>
                <input
                  id={field}
                  type={field === 'email' ? 'email' : 'text'}
                  required={Boolean(required)}
                  value={String(form[field as keyof typeof form])}
                  onChange={setField(field as keyof typeof form)}
                  className="field-input"
                />
              </div>
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            {(['REGISTERED', 'BILLING'] as const).map((addressType) => (
              <SectionCard
                key={addressType}
                title={`${addressType === 'REGISTERED' ? 'Registered' : 'Billing'} address`}
                description="Every new organisation must have this address on day one."
              >
                <div className="grid gap-4">
                  {[
                    ['line1', 'Address line 1', true],
                    ['line2', 'Address line 2', false],
                    ['city', 'City', true],
                    ['state', 'State', true],
                    ['country', 'Country', false],
                    ['pincode', 'Pincode', true],
                    ['gstin', 'GSTIN', false],
                  ].map(([field, label, required]) => (
                    <div key={field}>
                      <label className="field-label" htmlFor={`${addressType}-${field}`}>
                        {label}
                      </label>
                      <input
                        id={`${addressType}-${field}`}
                        className="field-input"
                        required={Boolean(required)}
                        value={String(form.addresses[addressType][field as keyof OrganisationAddressInput] ?? '')}
                        onChange={setAddressField(addressType, field as keyof OrganisationAddressInput)}
                      />
                    </div>
                  ))}
                </div>
              </SectionCard>
            ))}
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
