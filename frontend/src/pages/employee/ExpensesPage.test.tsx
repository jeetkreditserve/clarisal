import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ExpensesPage } from '@/pages/employee/ExpensesPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

const useCancelMyExpenseClaim = vi.fn()
const useCreateMyExpenseClaim = vi.fn()
const useMyExpenseClaims = vi.fn()
const useMyExpensePolicies = vi.fn()
const useSubmitMyExpenseClaim = vi.fn()
const useUpdateMyExpenseClaim = vi.fn()
const useUploadMyExpenseReceipt = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useCancelMyExpenseClaim: () => useCancelMyExpenseClaim(),
  useCreateMyExpenseClaim: () => useCreateMyExpenseClaim(),
  useMyExpenseClaims: () => useMyExpenseClaims(),
  useMyExpensePolicies: () => useMyExpensePolicies(),
  useSubmitMyExpenseClaim: () => useSubmitMyExpenseClaim(),
  useUpdateMyExpenseClaim: () => useUpdateMyExpenseClaim(),
  useUploadMyExpenseReceipt: () => useUploadMyExpenseReceipt(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <ExpensesPage />
    </MemoryRouter>,
  )
}

describe('ExpensesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMyExpensePolicies.mockReturnValue({ data: [], isLoading: false })
    useMyExpenseClaims.mockReturnValue({ data: [], isLoading: false })
    useCreateMyExpenseClaim.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({ id: 'claim-1' }) })
    useUpdateMyExpenseClaim.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useUploadMyExpenseReceipt.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useSubmitMyExpenseClaim.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useCancelMyExpenseClaim.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
  })

  it('creates an expense draft with a manual category', async () => {
    const user = userEvent.setup()
    const createClaim = vi.fn().mockResolvedValue({ id: 'claim-1' })
    useCreateMyExpenseClaim.mockReturnValue({ isPending: false, mutateAsync: createClaim })

    renderPage()

    await user.type(screen.getByLabelText('Title'), 'April client visit')
    await user.type(screen.getByLabelText('Manual category'), 'Travel')
    await user.type(screen.getByLabelText('Merchant'), 'Indian Railways')
    await user.type(screen.getByLabelText('Amount'), '1250.00')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))

    await waitFor(() => {
      expect(createClaim).toHaveBeenCalledWith({
        title: 'April client visit',
        claim_date: expect.any(String),
        policy: null,
        currency: 'INR',
        submit: false,
        lines: [
          {
            category_id: undefined,
            category_name: 'Travel',
            expense_date: expect.any(String),
            merchant: 'Indian Railways',
            description: '',
            amount: '1250.00',
            currency: 'INR',
          },
        ],
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Expense claim saved as draft.')
  })
})
