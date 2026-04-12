import type { LicenceBatch } from '@/types/organisation'

export type PaymentStatus = 'PENDING' | 'SUCCESS' | 'FAILED' | 'REFUNDED'
export type InvoiceStatus = 'DRAFT' | 'ISSUED' | 'PAID' | 'VOID'

export interface BillingPayment {
  id: string
  licence_batch_id: string
  amount: string
  currency: string
  gateway: 'RAZORPAY' | 'STRIPE' | 'MANUAL'
  gateway_order_id: string
  gateway_payment_id: string | null
  status: PaymentStatus
  failure_reason: string
  gateway_options: Record<string, unknown>
  completed_at: string | null
  created_at: string
  modified_at: string
}

export interface BillingInvoice {
  id: string
  payment_id: string
  invoice_number: string
  issue_date: string
  due_date: string
  amount: string
  gst_amount: string
  total_amount: string
  status: InvoiceStatus
  storage_key: string
  created_at: string
  modified_at: string
}

export interface OrgBillingSummary {
  organisation: {
    id: string
    name: string
    billing_status: string
    currency: string
    gateway: 'RAZORPAY' | 'STRIPE'
  }
  licence_batches: LicenceBatch[]
  payments: BillingPayment[]
  invoices: BillingInvoice[]
}

export interface PaymentOrderResponse {
  id: string
  gateway: 'RAZORPAY' | 'STRIPE'
  gateway_order_id: string
  amount: string
  currency: string
  status: PaymentStatus
  gateway_options: Record<string, unknown>
}

export interface CtBillingOverviewRow {
  organisation_id: string
  organisation_name: string
  billing_status: string
  status: string
  currency: string
  licence_count: number
  outstanding_amount: string
  last_payment_status: PaymentStatus | null
  last_payment_at: string | null
  latest_invoice_number: string | null
}
