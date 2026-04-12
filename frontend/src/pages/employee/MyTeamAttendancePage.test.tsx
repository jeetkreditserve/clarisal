import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MyTeamAttendancePage } from '@/pages/employee/MyTeamAttendancePage'

const useMyTeamAttendance = vi.fn()

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useMyTeamAttendance: (targetDate?: string) => useMyTeamAttendance(targetDate),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <MyTeamAttendancePage />
    </MemoryRouter>,
  )
}

describe('MyTeamAttendancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMyTeamAttendance.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'day-1',
          employee_id: 'emp-1',
          employee_name: 'Rohan Mehta',
          employee_code: 'EMP-101',
          attendance_date: '2026-04-11',
          status: 'PRESENT',
          source: 'WEB',
          check_in_at: '2026-04-11T09:00:00Z',
          check_out_at: '2026-04-11T18:00:00Z',
          worked_minutes: 540,
          overtime_minutes: 60,
          late_minutes: 0,
          paid_fraction: '1.00',
          leave_fraction: '0.00',
          on_duty_fraction: '0.00',
          is_holiday: false,
          is_week_off: false,
          is_late: false,
          needs_regularization: false,
          raw_punch_count: 2,
          note: '',
          metadata: {},
          shift_name: 'General',
          policy_name: 'Default Attendance Policy',
          created_at: '2026-04-11T09:00:00Z',
          modified_at: '2026-04-11T18:00:00Z',
        },
        {
          id: 'day-2',
          employee_id: 'emp-2',
          employee_name: 'Ananya Gupta',
          employee_code: 'EMP-102',
          attendance_date: '2026-04-11',
          status: 'INCOMPLETE',
          source: 'WEB',
          check_in_at: '2026-04-11T09:15:00Z',
          check_out_at: null,
          worked_minutes: 0,
          overtime_minutes: 0,
          late_minutes: 15,
          paid_fraction: '0.00',
          leave_fraction: '0.00',
          on_duty_fraction: '0.00',
          is_holiday: false,
          is_week_off: false,
          is_late: true,
          needs_regularization: true,
          raw_punch_count: 1,
          note: 'Only one punch',
          metadata: {},
          shift_name: 'General',
          policy_name: 'Default Attendance Policy',
          created_at: '2026-04-11T09:15:00Z',
          modified_at: '2026-04-11T09:15:00Z',
        },
      ],
    })
  })

  it('renders attendance rows and the CSV export action', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Team attendance' })).toBeInTheDocument()
    expect(screen.getByText('Rohan Mehta')).toBeInTheDocument()
    expect(screen.getByText('Ananya Gupta')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeInTheDocument()
  })

  it('filters the table to rows that need attention', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Needs attention' }))

    expect(screen.queryByText('Rohan Mehta')).not.toBeInTheDocument()
    expect(screen.getByText('Ananya Gupta')).toBeInTheDocument()
  })
})
