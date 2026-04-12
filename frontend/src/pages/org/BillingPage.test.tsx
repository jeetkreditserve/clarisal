import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BillingPage } from '@/pages/org/BillingPage'
import type { OrgBillingSummary } from '@/types/billing'

const {
  createBillingPaymentOrder,
  fetchBillingInvoiceDownloadUrl,
  fetchBillingPaymentStatus,
  fetchOrgBillingSummary,
  toastError,
  toastSuccess,
} = vi.hoisted(() => ({
  createBillingPaymentOrder: vi.fn(),
  fetchBillingInvoiceDownloadUrl: vi.fn(),
  fetchBillingPaymentStatus: vi.fn(),
  fetchOrgBillingSummary: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    error: toastError,
    success: toastSuccess,
  },
}))

vi.mock('@/lib/api/billing', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/billing')>('@/lib/api/billing')
  return {
    ...actual,
    createBillingPaymentOrder,
    fetchBillingInvoiceDownloadUrl,
    fetchBillingPaymentStatus,
    fetchOrgBillingSummary,
  }
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BillingPage />
    </QueryClientProvider>,
  )
}

function makeBillingSummary(overrides: Partial<OrgBillingSummary> = {}): OrgBillingSummary {
  return {
    organisation: {
      id: 'org-1',
      name: 'Acme Workforce',
      billing_status: 'PENDING_PAYMENT',
      currency: 'INR',
      gateway: 'RAZORPAY',
    },
    licence_batches: [
      {
        id: 'batch-1',
        quantity: 25,
        price_per_licence_per_month: '100.00',
        start_date: '2026-04-01',
        end_date: '2027-03-31',
        billing_months: 12,
        total_amount: '30000.00',
        payment_status: 'DRAFT',
        lifecycle_state: 'DRAFT',
        note: '',
        payment_provider: 'RAZORPAY',
        payment_reference: '',
        invoice_reference: '',
        created_by_email: 'ct@example.com',
        paid_by_email: null,
        paid_at: null,
        created_at: '2026-04-01T00:00:00Z',
        modified_at: '2026-04-01T00:00:00Z',
      },
    ],
    payments: [],
    invoices: [],
    ...overrides,
  }
}

describe('BillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchOrgBillingSummary.mockResolvedValue(makeBillingSummary())
    createBillingPaymentOrder.mockResolvedValue({
      id: 'payment-1',
      gateway: 'RAZORPAY',
      gateway_order_id: 'order_123',
      amount: '30000.00',
      currency: 'INR',
      status: 'PENDING',
      gateway_options: { key: 'rzp_test', order_id: 'order_123' },
    })
    fetchBillingPaymentStatus.mockResolvedValue({
      id: 'payment-1',
      licence_batch_id: 'batch-1',
      amount: '30000.00',
      currency: 'INR',
      gateway: 'RAZORPAY',
      gateway_order_id: 'order_123',
      gateway_payment_id: null,
      status: 'SUCCESS',
      failure_reason: '',
      gateway_options: {},
      completed_at: '2026-04-02T00:00:00Z',
      created_at: '2026-04-01T00:00:00Z',
      modified_at: '2026-04-02T00:00:00Z',
    })
    fetchBillingInvoiceDownloadUrl.mockResolvedValue({ download_url: 'https://example.com/invoice.pdf', invoice_number: 'INV-2026-000001' })
    delete window.Razorpay
  })

  it('creates a gateway order for the draft licence batch', async () => {
    const user = userEvent.setup()
    const open = vi.fn()
    window.Razorpay = class {
      open = open

      constructor(_options: Record<string, unknown>) {}
    }

    renderPage()

    await screen.findByText('25 seats awaiting payment')
    await user.click(screen.getByRole('button', { name: 'Pay Now' }))

    await waitFor(() => {
      expect(createBillingPaymentOrder.mock.calls[0]?.[0]).toEqual({ licence_batch_id: 'batch-1' })
    })
    expect(open).toHaveBeenCalled()
  })

  it('opens issued invoice PDFs from the presigned URL endpoint', async () => {
    const user = userEvent.setup()
    const open = vi.spyOn(window, 'open').mockReturnValue(null)
    fetchOrgBillingSummary.mockResolvedValue(
      makeBillingSummary({
        invoices: [
          {
            id: 'invoice-1',
            payment_id: 'payment-1',
            invoice_number: 'INV-2026-000001',
            issue_date: '2026-04-02',
            due_date: '2026-04-02',
            amount: '30000.00',
            gst_amount: '5400.00',
            total_amount: '35400.00',
            status: 'ISSUED',
            storage_key: 'orgs/org-1/invoices/invoice-1.pdf',
            created_at: '2026-04-02T00:00:00Z',
            modified_at: '2026-04-02T00:00:00Z',
          },
        ],
      }),
    )

    renderPage()

    expect(await screen.findAllByText('INV-2026-000001')).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: 'PDF' }))

    await waitFor(() => {
      expect(fetchBillingInvoiceDownloadUrl.mock.calls[0]?.[0]).toBe('invoice-1')
    })
    expect(open).toHaveBeenCalledWith('https://example.com/invoice.pdf', '_blank', 'noopener,noreferrer')
  })
})
