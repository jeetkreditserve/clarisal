import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MyTeamPage } from '@/pages/employee/MyTeamPage'

const useMyApprovalInbox = vi.fn()
const useMyTeam = vi.fn()
const useMyTeamAttendance = vi.fn()
const useMyTeamLeave = vi.fn()

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useMyApprovalInbox: (scope?: string) => useMyApprovalInbox(scope),
  useMyTeam: () => useMyTeam(),
  useMyTeamAttendance: (targetDate?: string) => useMyTeamAttendance(targetDate),
  useMyTeamLeave: (filters?: unknown) => useMyTeamLeave(filters),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <MyTeamPage />
    </MemoryRouter>,
  )
}

describe('MyTeamPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMyTeam.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'emp-1',
          name: 'Rohan Mehta',
          employee_code: 'EMP-101',
          designation: 'Senior Engineer',
          department: 'Engineering',
          status: 'ACTIVE',
          pending_leave_requests: 1,
          attendance_deviations_this_month: 2,
          leave_balance_summary: [
            {
              leave_type_id: 'leave-1',
              leave_type_name: 'Annual Leave',
              available: '7.00',
              credited: '8.00',
              used: '1.00',
              pending: '0.00',
              color: '#2563eb',
            },
          ],
        },
      ],
    })
    useMyTeamAttendance.mockReturnValue({
      data: [
        {
          id: 'day-1',
          employee_id: 'emp-1',
          employee_name: 'Rohan Mehta',
          employee_code: 'EMP-101',
          attendance_date: '2026-04-11',
          status: 'PRESENT',
          check_in_at: '2026-04-11T09:02:00Z',
          check_out_at: '2026-04-11T18:10:00Z',
          worked_minutes: 488,
          overtime_minutes: 8,
          late_minutes: 2,
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
          source: 'WEB',
          created_at: '2026-04-11T09:02:00Z',
          modified_at: '2026-04-11T18:10:00Z',
        },
      ],
    })
    useMyTeamLeave.mockReturnValue({
      data: [
        {
          id: 'leave-req-1',
          employee: 'emp-1',
          employee_name: 'Rohan Mehta',
          leave_type: 'leave-1',
          leave_type_name: 'Annual Leave',
          start_date: '2026-04-11',
          end_date: '2026-04-11',
          start_session: 'FULL_DAY',
          end_session: 'FULL_DAY',
          total_units: '1.00',
          reason: 'Medical appointment',
          status: 'PENDING',
          rejection_reason: '',
          created_at: '2026-04-10T10:00:00Z',
          modified_at: '2026-04-10T10:00:00Z',
        },
      ],
    })
    useMyApprovalInbox.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'action-1',
          status: 'PENDING',
          comment: '',
          acted_at: null,
          approval_run_id: 'run-1',
          request_kind: 'LEAVE',
          subject_label: 'Rohan leave request',
          requester_name: 'Rohan Mehta',
          requester_employee_id: 'emp-1',
          stage_name: 'Manager review',
          organisation_id: 'org-1',
          owner_name: 'Maya Patel',
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
  })

  it('renders team metrics, team cards, and team-scoped approvals', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'My team' })).toBeInTheDocument()
    expect(screen.getAllByText('Rohan Mehta').length).toBeGreaterThan(0)
    expect(screen.getByText(/Senior Engineer/)).toBeInTheDocument()
    expect(screen.getAllByText('Pending approvals').length).toBeGreaterThan(0)
    expect(screen.getByText('Rohan leave request')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review team attendance' })).toHaveAttribute('href', '/me/my-team/attendance')
  })

  it('renders an empty state when the manager has no direct reports', () => {
    useMyTeam.mockReturnValue({ isLoading: false, data: [] })
    useMyTeamAttendance.mockReturnValue({ data: [] })
    useMyTeamLeave.mockReturnValue({ data: [] })
    useMyApprovalInbox.mockReturnValue({ isLoading: false, data: [] })

    renderPage()

    expect(screen.getByText('You have no direct reports')).toBeInTheDocument()
  })
})
