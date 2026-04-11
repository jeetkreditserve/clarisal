import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ExpensePoliciesPage } from '@/pages/org/ExpensePoliciesPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

const useCreateOrgExpensePolicy = vi.fn()
const useOrgExpensePolicies = vi.fn()
const useUpdateOrgExpensePolicy = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useCreateOrgExpensePolicy: () => useCreateOrgExpensePolicy(),
  useOrgExpensePolicies: () => useOrgExpensePolicies(),
  useUpdateOrgExpensePolicy: () => useUpdateOrgExpensePolicy(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <ExpensePoliciesPage />
    </MemoryRouter>,
  )
}

describe('ExpensePoliciesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useOrgExpensePolicies.mockReturnValue({ data: [], isLoading: false })
    useCreateOrgExpensePolicy.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({ id: 'policy-1' }) })
    useUpdateOrgExpensePolicy.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
  })

  it('creates an expense policy with one category', async () => {
    const user = userEvent.setup()
    const createPolicy = vi.fn().mockResolvedValue({ id: 'policy-1' })
    useCreateOrgExpensePolicy.mockReturnValue({ isPending: false, mutateAsync: createPolicy })

    renderPage()

    await user.type(screen.getByLabelText('Policy name'), 'Travel and meals')
    await user.type(screen.getByLabelText('Description'), 'Standard expense coverage')
    fireEvent.change(screen.getByLabelText('Currency'), { target: { value: 'INR' } })
    fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'TRAVEL' } })
    await user.type(screen.getByLabelText('Name'), 'Travel')
    fireEvent.change(screen.getByLabelText('Per-claim limit'), { target: { value: '5000.00' } })
    await user.click(screen.getByRole('button', { name: 'Create policy' }))

    await waitFor(() => {
      expect(createPolicy).toHaveBeenCalledWith({
        name: 'Travel and meals',
        description: 'Standard expense coverage',
        currency: 'INR',
        categories: [
          {
            code: 'TRAVEL',
            name: 'Travel',
            per_claim_limit: '5000.00',
            requires_receipt: false,
          },
        ],
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Expense policy created.')
  })
})
