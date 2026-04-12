import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CtBillingPage } from '@/pages/ct/CtBillingPage'

const { fetchCtBillingOverview } = vi.hoisted(() => ({
  fetchCtBillingOverview: vi.fn(),
}))

vi.mock('@/lib/api/billing', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/billing')>('@/lib/api/billing')
  return {
    ...actual,
    fetchCtBillingOverview,
  }
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <CtBillingPage />
    </QueryClientProvider>,
  )
}

describe('CtBillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchCtBillingOverview.mockResolvedValue({
      results: [
        {
          organisation_id: 'org-1',
          organisation_name: 'Acme Workforce',
          billing_status: 'PENDING_PAYMENT',
          status: 'PENDING',
          currency: 'INR',
          licence_count: 25,
          outstanding_amount: '30000.00',
          last_payment_status: 'PENDING',
          last_payment_at: '2026-04-02T00:00:00Z',
          latest_invoice_number: null,
        },
      ],
    })
  })

  it('renders tenant billing rows and outstanding amount', async () => {
    renderPage()

    expect(await screen.findByText('Acme Workforce')).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getAllByText(/30,000/)[0]).toBeInTheDocument()
    expect(screen.getByText('Last payment Pending on 02 Apr 2026')).toBeInTheDocument()
  })
})
