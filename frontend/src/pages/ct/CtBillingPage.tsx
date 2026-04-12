import { useQuery } from '@tanstack/react-query'
import { CreditCard, ReceiptText, RefreshCw } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { MetricCard } from '@/components/ui/MetricCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonMetricCard, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { fetchCtBillingOverview } from '@/lib/api/billing'
import { formatDate, startCase } from '@/lib/format'
import type { PaymentStatus } from '@/types/billing'

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
  if (status === 'PENDING' || status === 'PENDING_PAYMENT') return 'info'
  return 'neutral'
}

export function CtBillingPage() {
  const billingQuery = useQuery({ queryKey: ['ct', 'billing'], queryFn: fetchCtBillingOverview })
  const rows = billingQuery.data?.results ?? []
  const outstandingTotal = rows.reduce((sum, row) => sum + Number(row.outstanding_amount || 0), 0)
  const pendingCount = rows.filter((row) => row.billing_status === 'PENDING_PAYMENT').length
  const paidCount = rows.filter((row) => row.billing_status === 'PAID').length

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Billing"
        title="Payment Gateway Overview"
        description="Track tenant payment state, outstanding online orders, and the latest issued invoices."
        actions={
          <button type="button" className="btn-secondary" onClick={() => void billingQuery.refetch()}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        {billingQuery.isLoading ? (
          Array.from({ length: 3 }).map((_, index) => <SkeletonMetricCard key={index} />)
        ) : (
          <>
            <MetricCard title="Pending tenants" value={pendingCount} hint="Awaiting payment confirmation" icon={CreditCard} tone="warning" />
            <MetricCard title="Paid tenants" value={paidCount} hint="Billing marked paid" icon={ReceiptText} tone="success" />
            <MetricCard title="Outstanding" value={formatMoney(outstandingTotal)} hint="Pending online payment orders" icon={CreditCard} tone="info" />
          </>
        )}
      </div>

      <SectionCard title="Tenant Billing" description="Operational view of licence billing and gateway status across organisations.">
        {billingQuery.isLoading ? (
          <SkeletonTable rows={5} />
        ) : rows.length === 0 ? (
          <EmptyState title="No billing records" description="Organisations with licence batches will appear here." icon={ReceiptText} />
        ) : (
          <div className="table-shell">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="table-head-row">
                  <th className="pb-3 pr-4 font-semibold">Organisation</th>
                  <th className="pb-3 pr-4 font-semibold">Licences</th>
                  <th className="pb-3 pr-4 font-semibold">Outstanding</th>
                  <th className="pb-3 pr-4 font-semibold">Payment</th>
                  <th className="pb-3 font-semibold">Invoice</th>
                </tr>
              </thead>
              <tbody className="table-body divide-y divide-[hsl(var(--border)_/_0.84)]">
                {rows.map((row) => (
                  <tr key={row.organisation_id} className="table-row">
                    <td className="py-4 pr-4">
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{row.organisation_name}</p>
                      <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">{startCase(row.status)}</p>
                    </td>
                    <td className="table-secondary py-4 pr-4">{row.licence_count}</td>
                    <td className="table-secondary py-4 pr-4">{formatMoney(row.outstanding_amount, row.currency)}</td>
                    <td className="py-4 pr-4">
                      <div className="flex flex-col items-start gap-2">
                        <StatusBadge tone={paymentTone(row.billing_status)}>{startCase(row.billing_status)}</StatusBadge>
                        {row.last_payment_status ? (
                          <span className="text-xs text-[hsl(var(--muted-foreground))]">
                            Last payment {startCase(row.last_payment_status)}
                            {row.last_payment_at ? ` on ${formatDate(row.last_payment_at)}` : ''}
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="table-secondary py-4">{row.latest_invoice_number ?? 'Not issued'}</td>
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
