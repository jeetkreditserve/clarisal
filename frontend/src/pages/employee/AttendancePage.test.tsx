import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AttendancePage } from '@/pages/employee/AttendancePage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useCreateMyAttendanceRegularization = vi.fn()
const useMyAttendanceCalendar = vi.fn()
const useMyAttendanceHistory = vi.fn()
const useMyAttendanceRegularizations = vi.fn()
const useMyAttendanceSummary = vi.fn()
const usePunchIn = vi.fn()
const usePunchOut = vi.fn()
const useWithdrawMyAttendanceRegularization = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useCreateMyAttendanceRegularization: () => useCreateMyAttendanceRegularization(),
  useMyAttendanceCalendar: (...args: unknown[]) => useMyAttendanceCalendar(...args),
  useMyAttendanceHistory: (...args: unknown[]) => useMyAttendanceHistory(...args),
  useMyAttendanceRegularizations: () => useMyAttendanceRegularizations(),
  useMyAttendanceSummary: () => useMyAttendanceSummary(),
  usePunchIn: () => usePunchIn(),
  usePunchOut: () => usePunchOut(),
  useWithdrawMyAttendanceRegularization: () => useWithdrawMyAttendanceRegularization(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <AttendancePage />
    </MemoryRouter>,
  )
}

describe('AttendancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useMyAttendanceSummary.mockReturnValue({
      isLoading: false,
      data: {
        today: {
          attendance_date: '2026-04-03',
          status: 'PRESENT',
          worked_minutes: 540,
          overtime_minutes: 60,
          metadata: {},
        },
        shift_source: 'POLICY_DEFAULT',
        shift: null,
        policy: {
          default_start_time: '09:00:00',
          default_end_time: '18:00:00',
          week_off_days: [6],
          overtime_approval_required: true,
          overtime_threshold_minutes: 30,
          overtime_multiplier: '1.50',
        },
        pending_regularizations: [],
      },
    })
    useMyAttendanceHistory.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'day-1',
          attendance_date: '2026-04-03',
          check_in_at: '2026-04-03T09:00:00Z',
          check_out_at: '2026-04-03T18:00:00Z',
          worked_minutes: 540,
          status: 'PRESENT',
          needs_regularization: false,
        },
      ],
    })
    useMyAttendanceCalendar.mockReturnValue({
      isLoading: false,
      data: {
        month: '2026-04',
        days: [
          { date: '2026-04-03', status: 'PRESENT', is_late: false, overtime_minutes: 60, wfh_status: '', effective_shift_source: 'POLICY_DEFAULT', overtime_status: '', lwp_units: '0.00' },
          { date: '2026-04-04', status: 'INCOMPLETE', is_late: true, overtime_minutes: 0, wfh_status: '', effective_shift_source: 'POLICY_DEFAULT', overtime_status: '', lwp_units: '0.00' },
        ],
      },
    })
    useMyAttendanceRegularizations.mockReturnValue({
      isLoading: false,
      data: [],
    })
    useCreateMyAttendanceRegularization.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    usePunchOut.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useWithdrawMyAttendanceRegularization.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('renders attendance summary cards and history', () => {
    usePunchIn.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })

    renderPage()

    expect(screen.getByRole('heading', { name: 'My attendance' })).toBeInTheDocument()
    expect(screen.getByText('Worked minutes')).toBeInTheDocument()
    expect(screen.getByText('540')).toBeInTheDocument()
    expect(screen.getByText('Current month attendance history')).toBeInTheDocument()
    expect(screen.getByText('Overtime policy')).toBeInTheDocument()
  })

  it('checks in successfully', async () => {
    const user = userEvent.setup()
    const punchIn = vi.fn().mockResolvedValue(undefined)
    usePunchIn.mockReturnValue({ isPending: false, mutateAsync: punchIn })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Check in' }))

    await waitFor(() => {
      expect(punchIn).toHaveBeenCalledWith({})
    })
    expect(toastSuccess).toHaveBeenCalledWith('Checked in successfully.')
  })
})
