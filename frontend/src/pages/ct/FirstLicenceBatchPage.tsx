import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CreditCard } from 'lucide-react'
import { toast } from 'sonner'

import { AppDatePicker } from '@/components/ui/AppDatePicker'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonFormBlock, SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useCreateLicenceBatch, useOrganisation, useUpdateLicenceBatch } from '@/hooks/useCtOrganisations'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, startCase } from '@/lib/format'
import type { LicenceBatch } from '@/types/organisation'

type BatchFormState = {
  quantity: string
  price_per_licence_per_month: string
  start_date: string
  end_date: string
  note: string
}

function calculateBillingMonths(startDate: string, endDate: string) {
  if (!startDate || !endDate) return 0
  const start = new Date(`${startDate}T00:00:00Z`)
  const end = new Date(`${endDate}T00:00:00Z`)
  const diffMs = end.getTime() - start.getTime()
  if (Number.isNaN(diffMs) || diffMs < 0) return 0
  const totalDays = Math.floor(diffMs / (24 * 60 * 60 * 1000)) + 1
  return Math.max(1, Math.ceil(totalDays / 30))
}

function formatMoney(value: string | number, currency = 'INR') {
  const numeric = typeof value === 'number' ? value : Number(value)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(numeric) ? numeric : 0)
}

function emptyBatchForm(): BatchFormState {
  return {
    quantity: '1',
    price_per_licence_per_month: '0.00',
    start_date: '',
    end_date: '',
    note: '',
  }
}

export function FirstLicenceBatchPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const organisationId = id ?? ''
  const { data: organisation, isLoading } = useOrganisation(organisationId)
  const createBatchMutation = useCreateLicenceBatch(organisationId)
  const updateBatchMutation = useUpdateLicenceBatch(organisationId)
  const [batchForm, setBatchForm] = useState<BatchFormState>(emptyBatchForm)
  const [editingBatchId, setEditingBatchId] = useState<string | null>(null)

  const effectiveBatchForm = useMemo<BatchFormState>(() => {
    if (!organisation || editingBatchId) {
      return batchForm
    }
    return {
      quantity: batchForm.quantity || '1',
      price_per_licence_per_month:
        batchForm.price_per_licence_per_month || organisation.batch_defaults.price_per_licence_per_month,
      start_date: batchForm.start_date || organisation.batch_defaults.start_date,
      end_date: batchForm.end_date || organisation.batch_defaults.end_date,
      note: batchForm.note,
    }
  }, [batchForm, editingBatchId, organisation])

  const pricingPreview = useMemo(() => {
    const months = calculateBillingMonths(effectiveBatchForm.start_date, effectiveBatchForm.end_date)
    const quantity = Number(effectiveBatchForm.quantity || 0)
    const price = Number(effectiveBatchForm.price_per_licence_per_month || 0)
    return {
      billingMonths: months,
      totalAmount: quantity * price * months,
    }
  }, [effectiveBatchForm])

  if (isLoading || !organisation) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonFormBlock rows={8} />
        <SkeletonTable rows={4} />
      </div>
    )
  }

  const resetBatchForm = () => {
    setEditingBatchId(null)
    setBatchForm(emptyBatchForm())
  }

  const handleEditBatch = (batch: LicenceBatch) => {
    setEditingBatchId(batch.id)
    setBatchForm({
      quantity: String(batch.quantity),
      price_per_licence_per_month: batch.price_per_licence_per_month,
      start_date: batch.start_date,
      end_date: batch.end_date,
      note: batch.note,
    })
  }

  const handleSaveBatch = async (event: React.FormEvent) => {
    event.preventDefault()
    const payload = {
      quantity: Number(effectiveBatchForm.quantity),
      price_per_licence_per_month: effectiveBatchForm.price_per_licence_per_month,
      start_date: effectiveBatchForm.start_date,
      end_date: effectiveBatchForm.end_date,
      note: effectiveBatchForm.note,
    }

    try {
      if (editingBatchId) {
        await updateBatchMutation.mutateAsync({ batchId: editingBatchId, payload })
        toast.success('Draft licence batch updated.')
      } else {
        await createBatchMutation.mutateAsync(payload)
        toast.success('Draft licence batch created.')
      }
      resetBatchForm()
      navigate(`/ct/organisations/${organisation.id}`)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save licence batch.'))
    }
  }

  return (
    <div className="space-y-6">
      <Link
        to={`/ct/organisations/${organisation.id}`}
        className="inline-flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground-strong))]"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to organisation detail
      </Link>

      <PageHeader
        eyebrow="Provisioning"
        title="Create the first licence batch"
        description={`Organisation ${organisation.name} has been created. The next step is to define the first commercial licence batch, or skip and do it later from the organisation detail page.`}
        actions={
          <button
            type="button"
            onClick={() => navigate(`/ct/organisations/${organisation.id}`)}
            className="btn-secondary"
          >
            Skip for now
          </button>
        }
      />

      <SectionCard
        title="First commercial batch"
        description="Draft batches stay editable until payment is marked. The first paid batch will automatically send the bootstrap admin onboarding email."
      >
        <form onSubmit={handleSaveBatch} className="grid gap-4 lg:grid-cols-2">
          <div>
            <label htmlFor="batch-quantity" className="field-label">
              Quantity
            </label>
            <input
              id="batch-quantity"
              type="number"
              min={1}
              value={effectiveBatchForm.quantity}
              onChange={(event) => setBatchForm((current) => ({ ...current, quantity: event.target.value }))}
              className="field-input"
            />
          </div>
          <div>
            <label htmlFor="batch-price" className="field-label">
              Price per licence per month
            </label>
            <input
              id="batch-price"
              type="number"
              min={0}
              step="0.01"
              value={effectiveBatchForm.price_per_licence_per_month}
              onChange={(event) =>
                setBatchForm((current) => ({ ...current, price_per_licence_per_month: event.target.value }))
              }
              className="field-input"
            />
          </div>
          <div>
            <label htmlFor="batch-start-date" className="field-label">
              Start date
            </label>
            <AppDatePicker
              id="batch-start-date"
              value={effectiveBatchForm.start_date}
              onValueChange={(value) => setBatchForm((current) => ({ ...current, start_date: value }))}
              placeholder="Select start date"
            />
          </div>
          <div>
            <label htmlFor="batch-end-date" className="field-label">
              End date
            </label>
            <AppDatePicker
              id="batch-end-date"
              value={effectiveBatchForm.end_date}
              onValueChange={(value) => setBatchForm((current) => ({ ...current, end_date: value }))}
              placeholder="Select end date"
            />
          </div>
          <div className="lg:col-span-2">
            <label htmlFor="batch-note" className="field-label">
              Note
            </label>
            <input
              id="batch-note"
              value={effectiveBatchForm.note}
              onChange={(event) => setBatchForm((current) => ({ ...current, note: event.target.value }))}
              className="field-input"
              placeholder="Optional context for this batch"
            />
          </div>
          <div className="surface-muted rounded-[24px] p-5">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">Billing months</p>
            <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
              {pricingPreview.billingMonths}
            </p>
          </div>
          <div className="surface-muted rounded-[24px] p-5">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">Upfront total</p>
            <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground-strong))]">
              {formatMoney(pricingPreview.totalAmount, organisation.currency)}
            </p>
          </div>
          <div className="flex flex-wrap gap-3 lg:col-span-2">
            <button
              type="submit"
              className="btn-primary"
              disabled={createBatchMutation.isPending || updateBatchMutation.isPending}
            >
              <CreditCard className="h-4 w-4" />
              {editingBatchId ? 'Update draft batch' : 'Save draft batch'}
            </button>
            {editingBatchId ? (
              <button type="button" onClick={resetBatchForm} className="btn-secondary">
                Cancel editing
              </button>
            ) : null}
          </div>
        </form>
      </SectionCard>

      <SectionCard
        title="Existing licence batches"
        description="Draft batches remain editable until paid. Paid batches become read-only and contribute to seat capacity once active."
      >
        {organisation.licence_batches.length === 0 ? (
          <EmptyState
            title="No licence batches yet"
            description="Save the first commercial batch above, or skip and return later from organisation detail."
            icon={CreditCard}
          />
        ) : (
          <div className="table-shell">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Qty</th>
                  <th className="pb-3 pr-4 font-semibold">Price</th>
                  <th className="pb-3 pr-4 font-semibold">Term</th>
                  <th className="pb-3 pr-4 font-semibold">State</th>
                  <th className="pb-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {organisation.licence_batches.map((batch) => (
                  <tr key={batch.id} className="table-row border-b border-[hsla(var(--border),0.76)] last:border-b-0">
                    <td className="table-primary py-4 pr-4 font-semibold">{batch.quantity}</td>
                    <td className="table-secondary py-4 pr-4">
                      {formatMoney(batch.price_per_licence_per_month, organisation.currency)}
                    </td>
                    <td className="table-secondary py-4 pr-4">
                      {formatDate(batch.start_date)} to {formatDate(batch.end_date)}
                    </td>
                    <td className="py-4 pr-4">
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge tone={batch.payment_status === 'PAID' ? 'success' : 'warning'}>
                          {startCase(batch.payment_status)}
                        </StatusBadge>
                        <StatusBadge
                          tone={
                            batch.lifecycle_state === 'ACTIVE'
                              ? 'success'
                              : batch.lifecycle_state === 'EXPIRED'
                                ? 'danger'
                                : 'info'
                          }
                        >
                          {startCase(batch.lifecycle_state)}
                        </StatusBadge>
                      </div>
                    </td>
                    <td className="py-4 text-right">
                      {batch.payment_status === 'DRAFT' ? (
                        <button onClick={() => handleEditBatch(batch)} className="btn-ghost" type="button">
                          Edit
                        </button>
                      ) : (
                        <span className="text-xs font-medium uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">
                          Locked
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  )
}
