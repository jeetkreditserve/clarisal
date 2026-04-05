import { useState } from 'react'
import { Pencil, Trash2, Plus, X, Eye } from 'lucide-react'
import { toast } from 'sonner'

import { AppDialog } from '@/components/ui/AppDialog'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useCtPayrollTaxSlabSets,
  useCreateCtPayrollTaxSlabSet,
  useUpdateCtPayrollTaxSlabSet,
  useDeleteCtPayrollTaxSlabSet,
  useCtPayrollStatutoryMasters,
} from '@/hooks/useCtOrganisations'
import { getErrorMessage } from '@/lib/errors'
import type { CtPayrollStatutoryMaster, PayrollTaxSlabSet, TaxCategory } from '@/types/hr'

// ─── Types ────────────────────────────────────────────────────────────────────

type SlabRow = { min_income: string; max_income: string; rate_percent: string }

type MasterFormState = {
  fiscal_year: string
  is_old_regime: boolean
  tax_category: TaxCategory
  slabs: SlabRow[]
}

type EditingState =
  | { mode: 'none' }
  | { mode: 'create'; prefill?: Partial<MasterFormState> }
  | { mode: 'edit'; slabSet: PayrollTaxSlabSet }

type ModalView =
  | { kind: 'tax'; set: PayrollTaxSlabSet }
  | { kind: 'pt'; rule: CtPayrollStatutoryMaster }
  | { kind: 'lwf'; rule: CtPayrollStatutoryMaster }

// ─── Constants ────────────────────────────────────────────────────────────────

const TAX_CATEGORIES: { value: TaxCategory; label: string; hint: string }[] = [
  { value: 'INDIVIDUAL', label: 'Individual', hint: 'Age < 60' },
  { value: 'SENIOR_CITIZEN', label: 'Senior Citizen', hint: 'Age 60–79' },
  { value: 'SUPER_SENIOR_CITIZEN', label: 'Super Senior Citizen', hint: 'Age ≥ 80' },
]

const CATEGORY_LABELS: Record<TaxCategory, string> = {
  INDIVIDUAL: 'Individual',
  SENIOR_CITIZEN: 'Senior Citizen',
  SUPER_SENIOR_CITIZEN: 'Super Senior Citizen',
}

const CATEGORY_HINTS: Record<TaxCategory, string> = {
  INDIVIDUAL: 'age < 60',
  SENIOR_CITIZEN: 'age 60–79',
  SUPER_SENIOR_CITIZEN: 'age ≥ 80',
}

const EMPTY_SLAB: SlabRow = { min_income: '', max_income: '', rate_percent: '' }

const DEFAULT_SLABS: SlabRow[] = [
  { min_income: '0', max_income: '', rate_percent: '' },
]

function makeMasterName(fiscal_year: string, is_old_regime: boolean, tax_category: TaxCategory) {
  const regime = is_old_regime ? 'Old Regime' : 'New Regime'
  const category = CATEGORY_LABELS[tax_category]
  return `India ${fiscal_year} ${regime} (${category})`
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatInr(value: string | null | undefined) {
  if (!value || value === '') return '—'
  const n = parseFloat(value)
  if (isNaN(n)) return value
  return `₹${n.toLocaleString('en-IN')}`
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SlabsTable({ slabs }: { slabs: PayrollTaxSlabSet['slabs'] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
          <th className="pb-1 pr-4 font-medium">From</th>
          <th className="pb-1 pr-4 font-medium">Up to</th>
          <th className="pb-1 font-medium">Rate</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-[hsl(var(--border)_/_0.5)]">
        {slabs.map((slab) => (
          <tr key={slab.id}>
            <td className="py-1 pr-4 tabular-nums">{formatInr(slab.min_income)}</td>
            <td className="py-1 pr-4 tabular-nums">{slab.max_income ? formatInr(slab.max_income) : 'No limit'}</td>
            <td className="py-1 tabular-nums font-medium">{slab.rate_percent}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function MasterCard({
  slabSet,
  onView,
  onEdit,
  onDelete,
}: {
  slabSet: PayrollTaxSlabSet
  onView: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <div className="surface-shell rounded-[18px] px-4 py-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-sm text-[hsl(var(--foreground-strong))]">
            {CATEGORY_LABELS[slabSet.tax_category]}
            <span className="ml-2 font-normal text-[hsl(var(--muted-foreground))]">
              ({CATEGORY_HINTS[slabSet.tax_category]})
            </span>
          </p>
          <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
            {slabSet.slabs.length} slab{slabSet.slabs.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            className="btn-icon-ghost"
            title="View slabs"
            onClick={onView}
          >
            <Eye className="size-3.5" />
          </button>
          <button
            type="button"
            className="btn-icon-ghost"
            title="Edit slabs"
            onClick={onEdit}
          >
            <Pencil className="size-3.5" />
          </button>
          {confirmDelete ? (
            <div className="flex items-center gap-1 text-xs">
              <span className="text-[hsl(var(--destructive))]">Delete?</span>
              <button type="button" className="btn-danger-xs" onClick={onDelete}>
                Yes
              </button>
              <button type="button" className="btn-ghost-xs" onClick={() => setConfirmDelete(false)}>
                No
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="btn-icon-ghost text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))]"
              title="Delete this master"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 className="size-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyMasterSlot({
  fiscal_year,
  is_old_regime,
  tax_category,
  onCreate,
}: {
  fiscal_year: string
  is_old_regime: boolean
  tax_category: TaxCategory
  onCreate: (prefill: Partial<MasterFormState>) => void
}) {
  return (
    <button
      type="button"
      className="surface-muted rounded-[18px] px-4 py-4 w-full text-left border border-dashed border-[hsl(var(--border))] hover:border-[hsl(var(--ring))] transition-colors group"
      onClick={() => onCreate({ fiscal_year, is_old_regime, tax_category })}
    >
      <p className="text-sm font-semibold text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--foreground-strong))]">
        {CATEGORY_LABELS[tax_category]}
        <span className="ml-1 font-normal text-xs">({CATEGORY_HINTS[tax_category]})</span>
      </p>
      <p className="mt-1 flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--foreground-strong))]">
        <Plus className="size-3" />
        Add master
      </p>
    </button>
  )
}

// ─── Master Form ──────────────────────────────────────────────────────────────

function MasterForm({
  initial,
  onSubmit,
  onCancel,
  isPending,
  isEdit,
}: {
  initial: MasterFormState
  onSubmit: (form: MasterFormState) => void
  onCancel: () => void
  isPending: boolean
  isEdit: boolean
}) {
  const [form, setForm] = useState<MasterFormState>(initial)

  function updateSlab(index: number, field: keyof SlabRow, value: string) {
    setForm((prev) => {
      const slabs = [...prev.slabs]
      slabs[index] = { ...slabs[index], [field]: value }
      return { ...prev, slabs }
    })
  }

  function addSlab() {
    setForm((prev) => {
      const last = prev.slabs[prev.slabs.length - 1]
      return {
        ...prev,
        slabs: [
          ...prev.slabs,
          { min_income: last?.max_income ?? '', max_income: '', rate_percent: '' },
        ],
      }
    })
  }

  function removeSlab(index: number) {
    setForm((prev) => ({
      ...prev,
      slabs: prev.slabs.filter((_, i) => i !== index),
    }))
  }

  return (
    <div className="surface-shell rounded-[22px] p-5 space-y-5">
      <div className="flex items-center justify-between">
        <p className="font-semibold text-[hsl(var(--foreground-strong))]">
          {isEdit ? 'Edit income tax master' : 'New income tax master'}
        </p>
        <button type="button" onClick={onCancel} className="btn-icon-ghost">
          <X className="size-4" />
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <label className="field-label">Financial year</label>
          <input
            className="field-input"
            placeholder="2026-2027"
            value={form.fiscal_year}
            disabled={isEdit}
            onChange={(e) => setForm((prev) => ({ ...prev, fiscal_year: e.target.value }))}
          />
          <p className="text-xs text-[hsl(var(--muted-foreground))]">Format: YYYY-YYYY</p>
        </div>

        <div className="space-y-1">
          <label className="field-label">Tax regime</label>
          <select
            className="field-input"
            value={form.is_old_regime ? 'old' : 'new'}
            disabled={isEdit}
            onChange={(e) => setForm((prev) => ({ ...prev, is_old_regime: e.target.value === 'old' }))}
          >
            <option value="new">New Regime (default)</option>
            <option value="old">Old Regime</option>
          </select>
        </div>

        <div className="space-y-1">
          <label className="field-label">Taxpayer category</label>
          <select
            className="field-input"
            value={form.tax_category}
            disabled={isEdit}
            onChange={(e) => setForm((prev) => ({ ...prev, tax_category: e.target.value as TaxCategory }))}
          >
            {TAX_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label} ({cat.hint})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Slab rows */}
      <div className="space-y-2">
        <div className="grid grid-cols-[1fr_1fr_100px_32px] gap-2 text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide px-1">
          <span>Income from (₹)</span>
          <span>Income up to (₹)</span>
          <span>Rate (%)</span>
          <span />
        </div>

        {form.slabs.map((slab, i) => (
          <div key={i} className="grid grid-cols-[1fr_1fr_100px_32px] gap-2 items-center">
            <input
              className="field-input tabular-nums"
              placeholder="e.g. 0"
              value={slab.min_income}
              onChange={(e) => updateSlab(i, 'min_income', e.target.value)}
            />
            <input
              className="field-input tabular-nums"
              placeholder="Leave blank for no limit"
              value={slab.max_income}
              onChange={(e) => updateSlab(i, 'max_income', e.target.value)}
            />
            <input
              className="field-input tabular-nums"
              placeholder="e.g. 5"
              value={slab.rate_percent}
              onChange={(e) => updateSlab(i, 'rate_percent', e.target.value)}
            />
            <button
              type="button"
              className="btn-icon-ghost text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))]"
              onClick={() => removeSlab(i)}
              disabled={form.slabs.length <= 1}
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}

        <button type="button" className="btn-ghost text-sm flex items-center gap-1.5" onClick={addSlab}>
          <Plus className="size-3.5" />
          Add slab row
        </button>
      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          type="button"
          className="btn-primary"
          disabled={isPending}
          onClick={() => onSubmit(form)}
        >
          {isEdit ? 'Update master' : 'Publish master'}
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}

// ─── Fiscal Year Block ────────────────────────────────────────────────────────

function FiscalYearBlock({
  fiscal_year,
  sets,
  onView,
  onEdit,
  onDelete,
  onCreatePrefill,
}: {
  fiscal_year: string
  sets: PayrollTaxSlabSet[]
  onView: (set: PayrollTaxSlabSet) => void
  onEdit: (set: PayrollTaxSlabSet) => void
  onDelete: (set: PayrollTaxSlabSet) => void
  onCreatePrefill: (prefill: Partial<MasterFormState>) => void
}) {
  const regimes: { label: string; is_old_regime: boolean }[] = [
    { label: 'New Regime', is_old_regime: false },
    { label: 'Old Regime', is_old_regime: true },
  ]

  return (
    <div className="space-y-4">
      <p className="font-semibold text-[hsl(var(--foreground-strong))]">FY {fiscal_year}</p>
      {regimes.map(({ label, is_old_regime }) => (
        <div key={String(is_old_regime)} className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            {label}
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {TAX_CATEGORIES.map(({ value: cat }) => {
              const match = sets.find(
                (s) => s.is_old_regime === is_old_regime && s.tax_category === cat
              )
              return match ? (
                <MasterCard
                  key={cat}
                  slabSet={match}
                  onView={() => onView(match)}
                  onEdit={() => onEdit(match)}
                  onDelete={() => onDelete(match)}
                />
              ) : (
                <EmptyMasterSlot
                  key={cat}
                  fiscal_year={fiscal_year}
                  is_old_regime={is_old_regime}
                  tax_category={cat}
                  onCreate={onCreatePrefill}
                />
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function PayrollMastersPage() {
  const { data, isLoading } = useCtPayrollTaxSlabSets()
  const { data: statutoryMasters } = useCtPayrollStatutoryMasters()
  const createMutation = useCreateCtPayrollTaxSlabSet()
  const updateMutation = useUpdateCtPayrollTaxSlabSet()
  const deleteMutation = useDeleteCtPayrollTaxSlabSet()

  const [editing, setEditing] = useState<EditingState>({ mode: 'none' })
  const [modalView, setModalView] = useState<ModalView | null>(null)

  const allSets = data ?? []

  // Group by fiscal year, sorted newest first
  const byFiscalYear = allSets.reduce<Record<string, PayrollTaxSlabSet[]>>((acc, set) => {
    ;(acc[set.fiscal_year] ??= []).push(set)
    return acc
  }, {})
  const sortedYears = Object.keys(byFiscalYear).sort().reverse()

  // Always default to currentYear-nextYear.
  // Jan–Mar: this resolves to the upcoming FY (budget season, pre-configure before April).
  // Apr–Dec: this resolves to the active FY.
  const currentYear = new Date().getFullYear()
  const defaultFiscalYear = `${currentYear}-${currentYear + 1}`

  function handleCreate(form: MasterFormState) {
    const payload = {
      name: makeMasterName(form.fiscal_year, form.is_old_regime, form.tax_category),
      fiscal_year: form.fiscal_year,
      country_code: 'IN',
      is_old_regime: form.is_old_regime,
      tax_category: form.tax_category,
      is_active: true,
      slabs: form.slabs.map((s) => ({
        min_income: s.min_income,
        max_income: s.max_income || null,
        rate_percent: s.rate_percent,
      })),
    }
    createMutation.mutate(payload, {
      onSuccess: () => {
        toast.success('Income tax master published.')
        setEditing({ mode: 'none' })
      },
      onError: (err) => toast.error(getErrorMessage(err, 'Unable to publish master.')),
    })
  }

  function handleUpdate(id: string, form: MasterFormState) {
    const payload = {
      slabs: form.slabs.map((s) => ({
        min_income: s.min_income,
        max_income: s.max_income || null,
        rate_percent: s.rate_percent,
      })),
    }
    updateMutation.mutate(
      { id, payload },
      {
        onSuccess: () => {
          toast.success('Master updated.')
          setEditing({ mode: 'none' })
        },
        onError: (err) => toast.error(getErrorMessage(err, 'Unable to update master.')),
      }
    )
  }

  function handleDelete(set: PayrollTaxSlabSet) {
    deleteMutation.mutate(set.id, {
      onSuccess: () => toast.success(`${set.name} deleted.`),
      onError: (err) => toast.error(getErrorMessage(err, 'Unable to delete master.')),
    })
  }

  function openCreate(prefill?: Partial<MasterFormState>) {
    setEditing({ mode: 'create', prefill })
  }

  function getInitialForm(prefill?: Partial<MasterFormState>): MasterFormState {
    return {
      fiscal_year: prefill?.fiscal_year ?? defaultFiscalYear,
      is_old_regime: prefill?.is_old_regime ?? false,
      tax_category: prefill?.tax_category ?? 'INDIVIDUAL',
      slabs: prefill?.slabs ?? DEFAULT_SLABS,
    }
  }

  function getEditInitialForm(set: PayrollTaxSlabSet): MasterFormState {
    return {
      fiscal_year: set.fiscal_year,
      is_old_regime: set.is_old_regime,
      tax_category: set.tax_category,
      slabs: set.slabs.map((s) => ({
        min_income: s.min_income,
        max_income: s.max_income ?? '',
        rate_percent: s.rate_percent,
      })),
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
        description="Statutory income tax slab definitions used across all organisations. One master per financial year, regime, and taxpayer category. PT and LWF schedules are seeded via the seed_statutory_masters management command."
      />

      {/* ── Income tax masters ─────────────────────────────────────────── */}
      <SectionCard
        title="Income tax masters"
        description="India income tax slabs by financial year, regime, and taxpayer age category. The payroll engine automatically selects the correct master for each employee based on their date of birth."
        actions={
          editing.mode === 'none' ? (
            <button type="button" className="btn-secondary text-sm" onClick={() => openCreate()}>
              <Plus className="size-3.5 mr-1" />
              New master
            </button>
          ) : null
        }
      >
        <div className="space-y-6">
          {/* Create / edit form */}
          {editing.mode === 'create' && (
            <MasterForm
              initial={getInitialForm(editing.prefill)}
              onSubmit={handleCreate}
              onCancel={() => setEditing({ mode: 'none' })}
              isPending={createMutation.isPending}
              isEdit={false}
            />
          )}
          {editing.mode === 'edit' && (
            <MasterForm
              initial={getEditInitialForm(editing.slabSet)}
              onSubmit={(form) => handleUpdate(editing.slabSet.id, form)}
              onCancel={() => setEditing({ mode: 'none' })}
              isPending={updateMutation.isPending}
              isEdit={true}
            />
          )}

          {/* Grouped by fiscal year */}
          {sortedYears.length === 0 && editing.mode === 'none' ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              No income tax masters yet. Run{' '}
              <code className="font-mono text-xs">python manage.py seed_statutory_masters</code>{' '}
              to seed 2024-25 and 2025-26, or create a master above.
            </p>
          ) : (
            sortedYears.map((fy) => (
              <FiscalYearBlock
                key={fy}
                fiscal_year={fy}
                sets={byFiscalYear[fy]}
                onView={(set) => setModalView({ kind: 'tax', set })}
                onEdit={(set) => setEditing({ mode: 'edit', slabSet: set })}
                onDelete={handleDelete}
                onCreatePrefill={(prefill) => setEditing({ mode: 'create', prefill })}
              />
            ))
          )}
        </div>
      </SectionCard>

      {/* ── Professional Tax ────────────────────────────────────────────── */}
      {statutoryMasters && (
        <>
          <SectionCard
            title="Professional Tax rules"
            description="State-wise PT deduction schedules. Read-only — update by editing statutory_seed.py and running seed_statutory_masters."
          >
            {statutoryMasters.professional_tax_rules.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No rules seeded. Run{' '}
                <code className="font-mono text-xs">python manage.py seed_statutory_masters</code>.
              </p>
            ) : (
              <div className="space-y-2">
                {statutoryMasters.professional_tax_rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="surface-shell flex flex-wrap items-center justify-between gap-2 rounded-[18px] px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">
                        {rule.state_name}
                      </p>
                      <StatusBadge tone="info">{rule.state_code}</StatusBadge>
                      {rule.is_active ? (
                        <StatusBadge tone="success">Active</StatusBadge>
                      ) : (
                        <StatusBadge tone="neutral">Inactive</StatusBadge>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        {rule.deduction_frequency} deduction · {rule.slabs?.length ?? 0} slab
                        {(rule.slabs?.length ?? 0) !== 1 ? 's' : ''} · effective{' '}
                        {rule.effective_from}
                        {rule.source_label ? ` · ${rule.source_label}` : ''}
                      </p>
                      <button
                        type="button"
                        className="btn-icon-ghost shrink-0"
                        title="View slabs"
                        onClick={() => setModalView({ kind: 'pt', rule })}
                      >
                        <Eye className="size-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Labour Welfare Fund rules"
            description="State-wise LWF contribution schedules. Read-only — update by editing statutory_seed.py and running seed_statutory_masters."
          >
            {statutoryMasters.labour_welfare_fund_rules.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No rules seeded. Run{' '}
                <code className="font-mono text-xs">python manage.py seed_statutory_masters</code>.
              </p>
            ) : (
              <div className="space-y-2">
                {statutoryMasters.labour_welfare_fund_rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="surface-shell flex flex-wrap items-center justify-between gap-2 rounded-[18px] px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-[hsl(var(--foreground-strong))]">
                        {rule.state_name}
                      </p>
                      <StatusBadge tone="info">{rule.state_code}</StatusBadge>
                      {rule.is_active ? (
                        <StatusBadge tone="success">Active</StatusBadge>
                      ) : (
                        <StatusBadge tone="neutral">Inactive</StatusBadge>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        {rule.deduction_frequency} deduction · {rule.contributions?.length ?? 0}{' '}
                        contribution tier
                        {(rule.contributions?.length ?? 0) !== 1 ? 's' : ''} · effective{' '}
                        {rule.effective_from}
                        {rule.source_label ? ` · ${rule.source_label}` : ''}
                      </p>
                      <button
                        type="button"
                        className="btn-icon-ghost shrink-0"
                        title="View contributions"
                        onClick={() => setModalView({ kind: 'lwf', rule })}
                      >
                        <Eye className="size-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </>
      )}

      {/* ── Detail modal ─────────────────────────────────────────────────── */}
      <AppDialog
        open={modalView !== null}
        onOpenChange={(open) => { if (!open) setModalView(null) }}
        title={
          modalView?.kind === 'tax'
            ? `${modalView.set.name}`
            : modalView?.kind === 'pt'
            ? `PT — ${modalView.rule.state_name} (${modalView.rule.state_code})`
            : modalView?.kind === 'lwf'
            ? `LWF — ${modalView.rule.state_name} (${modalView.rule.state_code})`
            : ''
        }
        description={
          modalView?.kind === 'tax'
            ? `${modalView.set.fiscal_year} · ${modalView.set.is_old_regime ? 'Old Regime' : 'New Regime'} · ${CATEGORY_LABELS[modalView.set.tax_category]} (${CATEGORY_HINTS[modalView.set.tax_category]})`
            : modalView?.kind === 'pt'
            ? `${modalView.rule.deduction_frequency} deduction · effective ${modalView.rule.effective_from}${modalView.rule.source_label ? ` · ${modalView.rule.source_label}` : ''}`
            : modalView?.kind === 'lwf'
            ? `${modalView.rule.deduction_frequency} deduction · effective ${modalView.rule.effective_from}${modalView.rule.source_label ? ` · ${modalView.rule.source_label}` : ''}`
            : undefined
        }
      >
        {modalView?.kind === 'tax' && (
          <SlabsTable slabs={modalView.set.slabs} />
        )}

        {modalView?.kind === 'pt' && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                <th className="pb-1 pr-4 font-medium">Gender</th>
                <th className="pb-1 pr-4 font-medium">Income from</th>
                <th className="pb-1 pr-4 font-medium">Income up to</th>
                <th className="pb-1 pr-4 font-medium">Deduction</th>
                <th className="pb-1 font-medium">Months</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border)_/_0.5)]">
              {(modalView.rule.slabs ?? []).map((slab, i) => (
                <tr key={i}>
                  <td className="py-1.5 pr-4 capitalize">{slab.gender.toLowerCase()}</td>
                  <td className="py-1.5 pr-4 tabular-nums">{formatInr(slab.min_income)}</td>
                  <td className="py-1.5 pr-4 tabular-nums">{slab.max_income ? formatInr(slab.max_income) : 'No limit'}</td>
                  <td className="py-1.5 pr-4 tabular-nums font-medium">₹{slab.deduction_amount}</td>
                  <td className="py-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                    {slab.applicable_months ? slab.applicable_months.join(', ') : 'All months'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {modalView?.kind === 'lwf' && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
                <th className="pb-1 pr-4 font-medium">Wage from</th>
                <th className="pb-1 pr-4 font-medium">Wage up to</th>
                <th className="pb-1 pr-4 font-medium">Employee</th>
                <th className="pb-1 pr-4 font-medium">Employer</th>
                <th className="pb-1 font-medium">Months</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border)_/_0.5)]">
              {(modalView.rule.contributions ?? []).map((tier, i) => (
                <tr key={i}>
                  <td className="py-1.5 pr-4 tabular-nums">{formatInr(tier.min_wage)}</td>
                  <td className="py-1.5 pr-4 tabular-nums">{tier.max_wage ? formatInr(tier.max_wage) : 'No limit'}</td>
                  <td className="py-1.5 pr-4 tabular-nums font-medium">₹{tier.employee_amount}</td>
                  <td className="py-1.5 pr-4 tabular-nums font-medium">₹{tier.employer_amount}</td>
                  <td className="py-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                    {tier.applicable_months ? tier.applicable_months.join(', ') : 'All months'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </AppDialog>
    </div>
  )
}
