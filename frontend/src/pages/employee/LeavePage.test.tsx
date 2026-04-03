import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeavePage } from '@/pages/employee/LeavePage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useCreateMyLeaveRequest = vi.fn()
const useMyCalendar = vi.fn()
const useMyLeaveOverview = vi.fn()
const useWithdrawMyLeaveRequest = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useCreateMyLeaveRequest: () => useCreateMyLeaveRequest(),
  useMyCalendar: () => useMyCalendar(),
  useMyLeaveOverview: () => useMyLeaveOverview(),
  useWithdrawMyLeaveRequest: () => useWithdrawMyLeaveRequest(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <LeavePage />
    </MemoryRouter>,
  )
}

describe('LeavePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useMyCalendar.mockReturnValue({
      data: {
        month: '2026-04',
        days: [],
      },
    })
    useMyLeaveOverview.mockReturnValue({
      isLoading: false,
      data: {
        balances: [
          {
            leave_type_id: 'leave-1',
            leave_type_name: 'Casual Leave',
            color: '#22c55e',
            available: '5.00',
            credited: '12.00',
            used: '2.00',
            pending: '1.00',
          },
        ],
        leave_plan: {
          leave_types: [{ id: 'leave-1', name: 'Casual Leave', is_active: true }],
        },
        requests: [
          {
            id: 'request-1',
            leave_type_name: 'Casual Leave',
            start_date: '2026-04-10',
            end_date: '2026-04-11',
            total_units: '2.00',
            status: 'PENDING',
          },
        ],
      },
    })
  })

  it('renders leave balances and requests', () => {
    useCreateMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useWithdrawMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Leave management' })).toBeInTheDocument()
    expect(screen.getAllByText('Casual Leave')).toHaveLength(2)
    expect(screen.getByText('5.00')).toBeInTheDocument()
    expect(screen.getByText('My leave requests')).toBeInTheDocument()
  })

  it('withdraws a pending leave request', async () => {
    const user = userEvent.setup()
    const withdrawRequest = vi.fn().mockResolvedValue(undefined)

    useCreateMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useWithdrawMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: withdrawRequest })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Withdraw' }))

    await waitFor(() => {
      expect(withdrawRequest).toHaveBeenCalledWith('request-1')
    })
    expect(toastSuccess).toHaveBeenCalledWith('Leave request withdrawn.')
  })
})
