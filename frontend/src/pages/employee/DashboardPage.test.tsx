import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EmployeeDashboardPage } from '@/pages/employee/DashboardPage'

const useMyDashboard = vi.fn()
const useMyProfile = vi.fn()

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useMyDashboard: () => useMyDashboard(),
  useMyProfile: () => useMyProfile(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <EmployeeDashboardPage />
    </MemoryRouter>,
  )
}

describe('EmployeeDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMyProfile.mockReturnValue({
      data: {
        employee: {
          full_name: 'Rohan Mehta',
          email: 'rohan.mehta@acmeworkforce.com',
        },
      },
    })
  })

  it('renders quick actions, onboarding state, and calendar when dashboard data is loaded', () => {
    useMyDashboard.mockReturnValue({
      isLoading: false,
      data: {
        profile_completion: { percent: 78, completed_sections: ['basic_details'], missing_sections: ['bank_details'] },
        employee_code: 'EMP-001',
        pending_documents: 1,
        verified_documents: 3,
        rejected_documents: 0,
        offboarding: null,
        onboarding_status: 'PENDING',
        approvals: { items: [] },
        notices: [{ id: 'notice-1', title: 'Office reopening', body: 'Please report by 9 AM.' }],
        calendar: {
          month: '2026-04',
          days: [
            {
              date: '2026-04-01',
              entries: [{ date: '2026-04-01', kind: 'HOLIDAY', label: 'Founders Day', status: 'PUBLISHED', color: '#16a34a' }],
            },
          ],
        },
        events: [{ kind: 'BIRTHDAY', date: '2026-04-01', label: 'Aditi Rao' }],
        leave_balances: [{ leave_type_id: 'leave-1', leave_type_name: 'Casual Leave', available: '8', credited: '12', pending: '1' }],
      },
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'My dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Quick actions')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Continue onboarding' })).toHaveAttribute('href', '/me/onboarding')
    expect(screen.getByText('No approvals are waiting on you right now.')).toBeInTheDocument()
    expect(screen.getByText('Month calendar')).toBeInTheDocument()
    expect(screen.getByText('Founders Day')).toBeInTheDocument()
  })

  it('renders offboarding metrics when an exit workflow is active', () => {
    useMyDashboard.mockReturnValue({
      isLoading: false,
      data: {
        profile_completion: { percent: 100, completed_sections: ['basic_details'], missing_sections: [] },
        employee_code: 'EMP-001',
        pending_documents: 0,
        verified_documents: 4,
        rejected_documents: 0,
        offboarding: {
          status: 'IN_PROGRESS',
          exit_status: 'Pending clearance',
          date_of_exit: '2026-04-30',
          completed_required_task_count: 1,
          required_task_count: 2,
          pending_required_task_count: 1,
          pending_document_requests: 1,
          has_primary_bank_account: false,
          tasks: [{ id: 'task-1', title: 'Return laptop', description: 'Submit device to IT.', status: 'PENDING' }],
        },
        onboarding_status: 'COMPLETE',
        approvals: { items: [] },
        notices: [],
        calendar: { month: '2026-04', days: [] },
        events: [],
        leave_balances: [],
      },
    })

    renderPage()

    expect(screen.getByText('Exit workflow')).toBeInTheDocument()
    expect(screen.getByText('Return laptop')).toBeInTheDocument()
    expect(screen.getByText('Pending clearance')).toBeInTheDocument()
  })
})
