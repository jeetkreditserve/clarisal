import { useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateCtPayrollTaxSlabSet, useCtPayrollTaxSlabSets, useCtPayrollStatutoryMasters } from '@/hooks/useCtOrganisations'
import { getErrorMessage } from '@/lib/errors'

const currentYear = new Date().getFullYear()

export function PayrollMastersPage() {
  const { data, isLoading } = useCtPayrollTaxSlabSets()
  const createMutation = useCreateCtPayrollTaxSlabSet()
  const { data: statutoryMasters } = useCtPayrollStatutoryMasters()
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
        description="Maintain the central India tax slab masters that are copied into each organisation payroll preview workspace."
      />

      <div className="rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
        <p className="font-semibold">Payroll support is still limited-scope.</p>
        <p className="mt-1 text-[hsl(var(--muted-foreground))]">
          These masters support preview payroll configuration only. They do not yet guarantee complete India statutory payroll behavior across every organisation.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionCard title="Create master" description="Publish a new fiscal-year slab definition that organisations can copy and customize for preview payroll setup.">
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

      {statutoryMasters && (
        <div className="space-y-4">
          <SectionCard
            title="Professional Tax rules"
            description="State-wise PT deduction schedules seeded from statutory data. Read-only — update via seed_statutory_masters management command."
          >
            {statutoryMasters.professional_tax_rules.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">No rules seeded. Run seed_statutory_masters.</p>
            ) : (
              <div className="space-y-2">
                {statutoryMasters.professional_tax_rules.map((rule) => (
                  <div key={rule.id} className="surface-shell flex flex-wrap items-center justify-between gap-2 rounded-[18px] px-4 py-3">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">{rule.state_name}</p>
                      <StatusBadge tone="info">{rule.state_code}</StatusBadge>
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {rule.deduction_frequency} • {rule.slabs?.length ?? 0} slabs • from {rule.effective_from}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Labour Welfare Fund rules"
            description="State-wise LWF contribution schedules. Read-only — update via seed_statutory_masters management command."
          >
            {statutoryMasters.labour_welfare_fund_rules.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">No rules seeded. Run seed_statutory_masters.</p>
            ) : (
              <div className="space-y-2">
                {statutoryMasters.labour_welfare_fund_rules.map((rule) => (
                  <div key={rule.id} className="surface-shell flex flex-wrap items-center justify-between gap-2 rounded-[18px] px-4 py-3">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">{rule.state_name}</p>
                      <StatusBadge tone="info">{rule.state_code}</StatusBadge>
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {rule.deduction_frequency} • {rule.contributions?.length ?? 0} contribution tiers • from {rule.effective_from}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}
    </div>
  )
}
