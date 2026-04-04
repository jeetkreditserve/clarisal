import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeavePage } from '@/pages/employee/LeavePage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useCreateMyLeaveEncashment = vi.fn()
const useCreateMyLeaveRequest = vi.fn()
const useMyCalendar = vi.fn()
const useMyLeaveEncashments = vi.fn()
const useMyLeaveOverview = vi.fn()
const useWithdrawMyLeaveRequest = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useCreateMyLeaveEncashment: () => useCreateMyLeaveEncashment(),
  useCreateMyLeaveRequest: () => useCreateMyLeaveRequest(),
  useMyCalendar: () => useMyCalendar(),
  useMyLeaveEncashments: () => useMyLeaveEncashments(),
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
    useMyLeaveEncashments.mockReturnValue({ data: [] })
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
          leave_types: [{ id: 'leave-1', name: 'Casual Leave', is_active: true, allows_encashment: true }],
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
    useCreateMyLeaveEncashment.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
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

    useCreateMyLeaveEncashment.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCreateMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useWithdrawMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: withdrawRequest })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Withdraw' }))

    await waitFor(() => {
      expect(withdrawRequest).toHaveBeenCalledWith('request-1')
    })
    expect(toastSuccess).toHaveBeenCalledWith('Leave request withdrawn.')
  })

  it('submits a leave encashment request', async () => {
    const user = userEvent.setup()
    const createEncashment = vi.fn().mockResolvedValue(undefined)

    useCreateMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCreateMyLeaveEncashment.mockReturnValue({ isPending: false, mutateAsync: createEncashment })
    useWithdrawMyLeaveRequest.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })

    renderPage()

    const leaveTypeButtons = screen.getAllByRole('button', { name: 'Select leave type' })
    await user.click(leaveTypeButtons[1])
    const encashmentOptions = screen.getAllByRole('button', { name: 'Casual Leave' })
    await user.click(encashmentOptions[encashmentOptions.length - 1])
    await user.type(screen.getByPlaceholderText('Cycle start'), '2026-01-01')
    await user.type(screen.getByPlaceholderText('Cycle end'), '2026-12-31')
    await user.type(screen.getByPlaceholderText('Days to encash'), '2.50')
    await user.click(screen.getByRole('button', { name: 'Submit encashment request' }))

    await waitFor(() => {
      expect(createEncashment).toHaveBeenCalledWith({
        leave_type_id: 'leave-1',
        cycle_start: '2026-01-01',
        cycle_end: '2026-12-31',
        days_to_encash: '2.50',
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Leave encashment request submitted.')
  })
})
