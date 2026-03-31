import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateOrganisation } from '@/hooks/useCtOrganisations'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { getErrorMessage } from '@/lib/errors'
import { toast } from 'sonner'

export function NewOrganisationPage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending } = useCreateOrganisation()
  const [form, setForm] = useState({
    name: '',
    licence_count: 5,
    address: '',
    phone: '',
    email: '',
    country_code: 'IN',
    currency: 'INR',
  })
  const [error, setError] = useState<string | null>(null)

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [field]: field === 'licence_count' ? Number(e.target.value) : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const org = await mutateAsync(form)
      toast.success('Organisation created.')
      navigate(`/ct/organisations/${org.id}`)
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to create organisation.'))
    }
  }

  const field = (id: string, label: string, type = 'text', required = false) => (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
        {required ? <span className="ml-1 text-rose-600">*</span> : null}
      </label>
      <input
        id={id}
        type={type}
        required={required}
        value={String(form[id as keyof typeof form])}
        onChange={set(id)}
        className="field-input"
      />
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Provisioning"
        title="Create organisation"
        description="Set the commercial and operational baseline before payment confirmation and admin invitation."
      />

      <SectionCard title="Organisation details" description="This creates the tenant shell and opening licence balance.">
        <form onSubmit={handleSubmit} className="grid gap-5 lg:grid-cols-2">
          <div className="lg:col-span-2">{field('name', 'Organisation name', 'text', true)}</div>
          {field('licence_count', 'Opening licence count', 'number', true)}
          {field('email', 'Contact email', 'email')}
          {field('phone', 'Contact phone')}
          {field('country_code', 'Country code', 'text', true)}
          {field('currency', 'Currency', 'text', true)}
          <div className="lg:col-span-2">{field('address', 'Address')}</div>

          {error ? (
            <div className="rounded-[20px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 lg:col-span-2">
              {error}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3 lg:col-span-2">
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
