import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateOrganisation } from '@/hooks/useCtOrganisations'
import { cn } from '@/lib/utils'

export function NewOrganisationPage() {
  const navigate = useNavigate()
  const { mutateAsync, isPending } = useCreateOrganisation()
  const [form, setForm] = useState({ name: '', licence_count: 1, address: '', phone: '', email: '' })
  const [error, setError] = useState<string | null>(null)

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [field]: field === 'licence_count' ? Number(e.target.value) : e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const org = await mutateAsync(form)
      navigate(`/ct/organisations/${org.id}`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { name?: string[] } } }
      setError(e.response?.data?.name?.[0] ?? 'Failed to create organisation.')
    }
  }

  const field = (id: string, label: string, type = 'text', required = false) => (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-foreground mb-1.5">
        {label}{required && <span className="text-destructive ml-1">*</span>}
      </label>
      <input
        id={id} type={type} required={required}
        value={String(form[id as keyof typeof form])}
        onChange={set(id)}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
      />
    </div>
  )

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">New Organisation</h1>
        <p className="mt-1 text-sm text-muted-foreground">Create a new tenant organisation.</p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border bg-card p-6 shadow-sm space-y-4">
        {field('name', 'Organisation name', 'text', true)}
        {field('licence_count', 'Licence count', 'number', true)}
        {field('email', 'Contact email', 'email')}
        {field('phone', 'Phone')}
        {field('address', 'Address')}

        {error && (
          <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isPending}
            className={cn(
              'rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
              'hover:opacity-90 disabled:opacity-60',
            )}
          >
            {isPending ? 'Creating…' : 'Create Organisation'}
          </button>
        </div>
      </form>
    </div>
  )
}
