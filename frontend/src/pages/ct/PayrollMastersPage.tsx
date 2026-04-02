import { useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateCtPayrollTaxSlabSet, useCtPayrollTaxSlabSets } from '@/hooks/useCtOrganisations'
import { getErrorMessage } from '@/lib/errors'

const currentYear = new Date().getFullYear()

export function PayrollMastersPage() {
  const { data, isLoading } = useCtPayrollTaxSlabSets()
  const createMutation = useCreateCtPayrollTaxSlabSet()
  const [form, setForm] = useState({
    name: 'Default India Master',
    fiscal_year: `${currentYear}-${currentYear + 1}`,
    slab_one_limit: '300000',
    slab_two_limit: '700000',
    slab_two_rate: '10',
    slab_three_rate: '20',
  })

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createMutation.mutateAsync({
        name: form.name,
        country_code: 'IN',
        fiscal_year: form.fiscal_year,
        is_active: true,
        slabs: [
          { min_income: '0', max_income: form.slab_one_limit, rate_percent: '0' },
          { min_income: form.slab_one_limit, max_income: form.slab_two_limit, rate_percent: form.slab_two_rate },
          { min_income: form.slab_two_limit, max_income: null, rate_percent: form.slab_three_rate },
        ],
      })
      toast.success('Payroll master created.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the payroll master.'))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Control Tower • Payroll"
        title="Payroll masters"
        description="Maintain the central India tax slab masters that are copied into each organisation payroll workspace."
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Create master" description="Publish a new fiscal-year slab definition that organisations can copy and customize.">
          <form onSubmit={handleSubmit} className="grid gap-4">
            <input className="field-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Master name" />
            <input className="field-input" value={form.fiscal_year} onChange={(event) => setForm((current) => ({ ...current, fiscal_year: event.target.value }))} placeholder="2026-2027" />
            <input className="field-input" value={form.slab_one_limit} onChange={(event) => setForm((current) => ({ ...current, slab_one_limit: event.target.value }))} placeholder="First slab upper limit" />
            <input className="field-input" value={form.slab_two_limit} onChange={(event) => setForm((current) => ({ ...current, slab_two_limit: event.target.value }))} placeholder="Second slab upper limit" />
            <input className="field-input" value={form.slab_two_rate} onChange={(event) => setForm((current) => ({ ...current, slab_two_rate: event.target.value }))} placeholder="Second slab rate" />
            <input className="field-input" value={form.slab_three_rate} onChange={(event) => setForm((current) => ({ ...current, slab_three_rate: event.target.value }))} placeholder="Top slab rate" />
            <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
              Create payroll master
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Published masters" description="Each master becomes the source set for org-scoped payroll copies.">
          <div className="space-y-3">
            {(data ?? []).map((set) => (
              <div key={set.id} className="surface-shell rounded-[18px] px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{set.name}</p>
                  <StatusBadge tone="success">CT master</StatusBadge>
                </div>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{set.fiscal_year} • {set.slabs.length} slabs</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
