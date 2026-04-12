import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CreditCard, Download, ReceiptText, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  createBillingPaymentOrder,
  fetchBillingInvoiceDownloadUrl,
  fetchBillingPaymentStatus,
  fetchOrgBillingSummary,
} from '@/lib/api/billing'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, startCase } from '@/lib/format'
import type { PaymentOrderResponse, PaymentStatus } from '@/types/billing'

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void }
  }
}

function formatMoney(value: string | number | null | undefined, currency = 'INR') {
  const numeric = typeof value === 'string' ? Number(value) : Number(value ?? 0)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(numeric) ? numeric : 0)
}

function paymentTone(status?: PaymentStatus | string | null): 'neutral' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'SUCCESS' || status === 'PAID') return 'success'
  if (status === 'FAILED') return 'danger'
  if (status === 'REFUNDED') return 'warning'
  if (status === 'PENDING') return 'info'
  return 'neutral'
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function loadRazorpayCheckout() {
  if (window.Razorpay) return true
  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-razorpay-checkout]')
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error('Unable to load Razorpay checkout.')), { once: true })
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.dataset.razorpayCheckout = 'true'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Unable to load Razorpay checkout.'))
    document.body.appendChild(script)
  })
  return Boolean(window.Razorpay)
}

export function BillingPage() {
  const queryClient = useQueryClient()
  const billingQuery = useQuery({ queryKey: ['org', 'billing'], queryFn: fetchOrgBillingSummary })
  const paymentOrderMutation = useMutation({ mutationFn: createBillingPaymentOrder })
  const invoiceDownloadMutation = useMutation({ mutationFn: fetchBillingInvoiceDownloadUrl })

  const billing = billingQuery.data
  const currency = billing?.organisation.currency ?? 'INR'
  const draftBatch = billing?.licence_batches.find((batch) => batch.payment_status === 'DRAFT') ?? null
  const latestInvoice = billing?.invoices[0] ?? null

  const pollPayment = async (paymentOrder: PaymentOrderResponse) => {
    for (let attempt = 0; attempt < 12; attempt += 1) {
      await sleep(2500)
      const payment = await fetchBillingPaymentStatus(paymentOrder.id)
      if (payment.status === 'SUCCESS') {
        await queryClient.invalidateQueries({ queryKey: ['org', 'billing'] })
        toast.success('Payment confirmed.')
        return
      }
      if (payment.status === 'FAILED') {
        await queryClient.invalidateQueries({ queryKey: ['org', 'billing'] })
        toast.error('Payment failed.')
        return
      }
    }
    await queryClient.invalidateQueries({ queryKey: ['org', 'billing'] })
  }

  const handlePayNow = async () => {
    if (!draftBatch) {
      toast.error('No draft licence batch is ready for payment.')
      return
    }
    try {
      const paymentOrder = await paymentOrderMutation.mutateAsync({ licence_batch_id: draftBatch.id })
      if (paymentOrder.gateway === 'RAZORPAY') {
        const loaded = await loadRazorpayCheckout()
        if (loaded && window.Razorpay) {
          const checkout = new window.Razorpay({
            ...paymentOrder.gateway_options,
            name: billing?.organisation.name ?? 'Clarisal',
            description: `${draftBatch.quantity} seats`,
            handler: () => void pollPayment(paymentOrder),
          })
          checkout.open()
          return
        }
      }
      toast.success('Payment order created.')
      void pollPayment(paymentOrder)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the payment order.'))
    }
  }

  const handleDownloadInvoice = async (invoiceId: string) => {
    try {
      const response = await invoiceDownloadMutation.mutateAsync(invoiceId)
      window.open(response.download_url, '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to open the invoice PDF.'))
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Billing"
        title="Billing & Subscription"
        description="Keep licence batches, online payment confirmation, and invoice downloads in one place."
        actions={
          <button type="button" className="btn-secondary" onClick={() => void billingQuery.refetch()}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        {!billing ? (
          Array.from({ length: 3 }).map((_, index) => <SkeletonMetricCard key={index} />)
        ) : (
          <>
            <MetricCard title="Billing status" value={startCase(billing.organisation.billing_status)} hint={`Gateway: ${startCase(billing.organisation.gateway)}`} icon={CreditCard} tone="primary" />
            <MetricCard title="Draft amount" value={formatMoney(draftBatch?.total_amount, currency)} hint={draftBatch ? `${draftBatch.quantity} seats awaiting payment` : 'No draft payment due'} icon={ReceiptText} tone="warning" />
            <MetricCard title="Latest invoice" value={latestInvoice?.invoice_number ?? 'None'} hint={latestInvoice ? formatDate(latestInvoice.issue_date) : 'Issued invoices appear here'} icon={ReceiptText} tone="success" />
          </>
        )}
      </div>

      <SectionCard
        title="Current Subscription"
        description="Draft batches can be paid online. Paid batches continue to drive active licence capacity."
        action={
          <button
            type="button"
            className="btn-primary"
            onClick={() => void handlePayNow()}
            disabled={!draftBatch || paymentOrderMutation.isPending}
          >
            <CreditCard className="h-4 w-4" />
            {paymentOrderMutation.isPending ? 'Creating order...' : 'Pay Now'}
          </button>
        }
      >
        {!billing ? (
          <SkeletonTable rows={3} />
        ) : billing.licence_batches.length === 0 ? (
          <EmptyState title="No licence batches" description="Licence batches created by Control Tower will appear here." icon={CreditCard} />
        ) : (
          <div className="table-shell">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Seats</th>
                  <th className="pb-3 pr-4 font-semibold">Period</th>
                  <th className="pb-3 pr-4 font-semibold">Amount</th>
                  <th className="pb-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="table-body divide-y divide-[hsl(var(--border)_/_0.84)]">
                {billing.licence_batches.map((batch) => (
                  <tr key={batch.id} className="table-row">
                    <td className="py-4 pr-4 font-semibold text-[hsl(var(--foreground-strong))]">{batch.quantity}</td>
                    <td className="table-secondary py-4 pr-4">{formatDate(batch.start_date)} to {formatDate(batch.end_date)}</td>
                    <td className="table-secondary py-4 pr-4">{formatMoney(batch.total_amount, currency)}</td>
                    <td className="py-4">
                      <StatusBadge tone={paymentTone(batch.payment_status)}>{startCase(batch.payment_status)}</StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Payment Activity" description="Recent online payment orders and gateway confirmations.">
        {!billing ? (
          <SkeletonTable rows={3} />
        ) : billing.payments.length === 0 ? (
          <EmptyState title="No online payments yet" description="Payment orders will appear here after Pay Now is used." icon={CreditCard} />
        ) : (
          <div className="grid gap-3">
            {billing.payments.map((payment) => (
              <div key={payment.id} className="flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-[hsl(var(--border)_/_0.84)] p-4">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{formatMoney(payment.amount, payment.currency)}</p>
                  <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{payment.gateway} order {payment.gateway_order_id}</p>
                </div>
                <StatusBadge tone={paymentTone(payment.status)}>{startCase(payment.status)}</StatusBadge>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Invoices" description="Issued invoice PDFs are generated after successful gateway confirmation.">
        {!billing ? (
          <SkeletonTable rows={3} />
        ) : billing.invoices.length === 0 ? (
          <EmptyState title="No invoices issued" description="Invoices are generated automatically after successful payments." icon={ReceiptText} />
        ) : (
          <div className="table-shell">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Invoice</th>
                  <th className="pb-3 pr-4 font-semibold">Issue date</th>
                  <th className="pb-3 pr-4 font-semibold">Total</th>
                  <th className="pb-3 font-semibold">PDF</th>
                </tr>
              </thead>
              <tbody className="table-body divide-y divide-[hsl(var(--border)_/_0.84)]">
                {billing.invoices.map((invoice) => (
                  <tr key={invoice.id} className="table-row">
                    <td className="py-4 pr-4 font-semibold text-[hsl(var(--foreground-strong))]">{invoice.invoice_number}</td>
                    <td className="table-secondary py-4 pr-4">{formatDate(invoice.issue_date)}</td>
                    <td className="table-secondary py-4 pr-4">{formatMoney(invoice.total_amount, currency)}</td>
                    <td className="py-4">
                      <button type="button" className="btn-secondary" onClick={() => void handleDownloadInvoice(invoice.id)}>
                        <Download className="h-4 w-4" />
                        PDF
                      </button>
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
