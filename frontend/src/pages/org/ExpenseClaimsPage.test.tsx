import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ExpenseClaimsPage } from '@/pages/org/ExpenseClaimsPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

const useApprovalInbox = vi.fn()
const useApproveApprovalAction = vi.fn()
const useEmployees = vi.fn()
const useOrgExpenseClaimSummary = vi.fn()
const useOrgExpenseClaims = vi.fn()
const useRejectApprovalAction = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useApprovalInbox: () => useApprovalInbox(),
  useApproveApprovalAction: () => useApproveApprovalAction(),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useOrgExpenseClaimSummary: () => useOrgExpenseClaimSummary(),
  useOrgExpenseClaims: (...args: unknown[]) => useOrgExpenseClaims(...args),
  useRejectApprovalAction: () => useRejectApprovalAction(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <ExpenseClaimsPage />
    </MemoryRouter>,
  )
}

describe('ExpenseClaimsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useOrgExpenseClaimSummary.mockReturnValue({
      data: {
        total_claims: 1,
        total_amount: '1250.00',
        by_status: {},
        by_reimbursement_status: {
          PENDING_PAYROLL: { count: 1, amount: '1250.00' },
        },
      },
      isLoading: false,
    })
    useOrgExpenseClaims.mockReturnValue({
      data: [
        {
          id: 'claim-1',
          employee: 'emp-1',
          employee_name: 'Priya Sharma',
          employee_code: 'EMP001',
          policy_id: 'policy-1',
          policy_name: 'Travel',
          title: 'Client visit',
          claim_date: '2026-04-10',
          currency: 'INR',
          status: 'SUBMITTED',
          reimbursement_status: 'NOT_READY',
          approval_run_id: 'run-1',
          reimbursement_pay_run_id: null,
          submitted_at: '2026-04-10T10:00:00Z',
          approved_at: null,
          rejected_at: null,
          reimbursed_at: null,
          rejection_reason: '',
          total_amount: '1250.00',
          created_at: '2026-04-10T09:00:00Z',
          lines: [
            {
              id: 'line-1',
              category: null,
              category_name: 'Travel',
              expense_date: '2026-04-09',
              merchant: 'Indian Railways',
              description: 'Train fare',
              amount: '1250.00',
              currency: 'INR',
              receipts: [],
            },
          ],
        },
      ],
      isLoading: false,
    })
    useApprovalInbox.mockReturnValue({
      data: [
        {
          id: 'action-1',
          status: 'PENDING',
          comment: '',
          acted_at: null,
          approval_run_id: 'run-1',
          request_kind: 'EXPENSE_CLAIM',
          subject_label: 'Client visit',
          requester_name: 'Priya Sharma',
          requester_employee_id: 'emp-1',
          stage_name: 'Manager review',
          organisation_id: 'org-1',
          owner_name: 'Aditi Rao',
          assignment_source: 'DIRECT',
          original_approver_name: null,
          due_at: null,
          is_overdue: false,
          escalated_from_action_id: null,
          created_at: '2026-04-10T10:00:00Z',
          modified_at: '2026-04-10T10:00:00Z',
        },
      ],
    })
    useEmployees.mockReturnValue({ data: { results: [] } })
    useApproveApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useRejectApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
  })

  it('bulk-approves selected expense claims from the review queue', async () => {
    const user = userEvent.setup()
    const approveAction = vi.fn().mockResolvedValue(undefined)
    useApproveApprovalAction.mockReturnValue({ isPending: false, mutateAsync: approveAction })

    renderPage()

    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Approve selected' }))

    await waitFor(() => {
      expect(approveAction).toHaveBeenCalledWith({ actionId: 'action-1', comment: '' })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Selected expense claims approved.')
  })
})
