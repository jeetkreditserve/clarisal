import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OrgDashboardPage } from '@/pages/org/DashboardPage'

const useOrgDashboard = vi.fn()
const useApprovalInbox = vi.fn()
const useOrgLeaveRequests = vi.fn()
const useOrgOnDutyRequests = vi.fn()

vi.mock('@/hooks/useOrgAdmin', () => ({
  useOrgDashboard: () => useOrgDashboard(),
  useApprovalInbox: () => useApprovalInbox(),
  useOrgLeaveRequests: () => useOrgLeaveRequests(),
  useOrgOnDutyRequests: () => useOrgOnDutyRequests(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <OrgDashboardPage />
    </MemoryRouter>,
  )
}

describe('OrgDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders setup guidance, metrics, and recent activity when data is available', () => {
    useOrgDashboard.mockReturnValue({
      isLoading: false,
      data: {
        onboarding_stage: 'ADMIN_ACTIVATED',
        total_employees: 12,
        active_employees: 8,
        invited_employees: 2,
        pending_employees: 1,
        licence_used: 11,
        licence_total: 20,
        pending_approvals: 3,
        documents_awaiting_review: 2,
        by_department: [{ department_name: 'People Operations', count: 4 }],
        by_location: [{ location_name: 'Registered Office', count: 6 }],
        recent_joins: [
          {
            id: 'employee-1',
            user__first_name: 'Priya',
            user__last_name: 'Sharma',
            employee_code: 'EMP002',
            designation: 'HR Operations Manager',
            date_of_joining: '2026-04-01',
          },
        ],
      },
    })
    useApprovalInbox.mockReturnValue({
      data: [{ id: 'approval-1', subject_label: 'Leave request', requester_name: 'Rohan Mehta', stage_name: 'Manager review' }],
    })
    useOrgLeaveRequests.mockReturnValue({
      data: [{ id: 'leave-1', employee_name: 'Priya Sharma', leave_type_name: 'Casual Leave', start_date: '2026-04-03' }],
    })
    useOrgOnDutyRequests.mockReturnValue({
      data: [{ id: 'od-1', employee_name: 'Ananya Iyer', policy_name: 'Field Visit', start_date: '2026-04-05' }],
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'People operations dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Recommended next steps')).toBeInTheDocument()
    expect(screen.getByText('Total employees')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Leave request')).toBeInTheDocument()
    expect(screen.getByText('People Operations')).toBeInTheDocument()
    expect(screen.getByText('Registered Office')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Priya Sharma' })).toHaveAttribute('href', '/org/employees/employee-1')
  })

  it('renders empty states when lists are empty and setup is complete', () => {
    useOrgDashboard.mockReturnValue({
      isLoading: false,
      data: {
        onboarding_stage: 'EMPLOYEES_INVITED',
        total_employees: 0,
        active_employees: 0,
        invited_employees: 0,
        pending_employees: 0,
        licence_used: 0,
        licence_total: 10,
        pending_approvals: 0,
        documents_awaiting_review: 0,
        by_department: [],
        by_location: [],
        recent_joins: [],
      },
    })
    useApprovalInbox.mockReturnValue({ data: [] })
    useOrgLeaveRequests.mockReturnValue({ data: [] })
    useOrgOnDutyRequests.mockReturnValue({ data: [] })

    renderPage()

    expect(screen.queryByText('Recommended next steps')).not.toBeInTheDocument()
    expect(screen.getByText('No approvals waiting')).toBeInTheDocument()
    expect(screen.getByText('No department distribution yet')).toBeInTheDocument()
    expect(screen.getByText('No location distribution yet')).toBeInTheDocument()
    expect(screen.getByText('No leave activity yet')).toBeInTheDocument()
    expect(screen.getByText('No on-duty activity yet')).toBeInTheDocument()
    expect(screen.getByText('No recent joins recorded yet')).toBeInTheDocument()
  })
})
