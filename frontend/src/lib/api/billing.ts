import api from '@/lib/api'
import type { BillingInvoice, BillingPayment, CtBillingOverviewRow, OrgBillingSummary, PaymentOrderResponse } from '@/types/billing'

export async function fetchOrgBillingSummary(): Promise<OrgBillingSummary> {
  const { data } = await api.get('/org/billing/')
  return data
}

export async function createBillingPaymentOrder(payload: {
  licence_batch_id?: string
  amount?: string
}): Promise<PaymentOrderResponse> {
  const { data } = await api.post('/org/billing/payment-orders/', payload)
  return data
}

export async function fetchBillingPaymentStatus(paymentId: string): Promise<BillingPayment> {
  const { data } = await api.get(`/org/billing/payment-orders/${paymentId}/status/`)
  return data
}

export async function fetchBillingInvoices(): Promise<BillingInvoice[]> {
  const { data } = await api.get('/org/billing/invoices/')
  return data
}

export async function fetchBillingInvoiceDownloadUrl(invoiceId: string): Promise<{
  download_url: string
  invoice_number: string
}> {
  const { data } = await api.get(`/org/billing/invoices/${invoiceId}/download/`)
  return data
}

export async function fetchCtBillingOverview(): Promise<{ results: CtBillingOverviewRow[] }> {
  const { data } = await api.get('/ct/billing/')
  return data
}
