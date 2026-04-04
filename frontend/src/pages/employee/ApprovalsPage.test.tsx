import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApprovalsPage } from '@/pages/employee/ApprovalsPage'

const useApproveMyApprovalAction = vi.fn()
const useMyApprovalInbox = vi.fn()
const useRejectMyApprovalAction = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useApproveMyApprovalAction: () => useApproveMyApprovalAction(),
  useMyApprovalInbox: () => useMyApprovalInbox(),
  useRejectMyApprovalAction: () => useRejectMyApprovalAction(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <ApprovalsPage />
    </MemoryRouter>,
  )
}

describe('ApprovalsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useApproveMyApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useRejectMyApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useMyApprovalInbox.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'action-1',
          subject_label: 'Attendance regularization',
          requester_name: 'Rohan Mehta',
          request_kind: 'ATTENDANCE_REGULARIZATION',
          stage_name: 'Manager review',
          status: 'PENDING',
          owner_name: 'Ava Patel',
          assignment_source: 'ESCALATED',
          original_approver_name: 'Nikhil Rao',
          is_overdue: true,
          due_at: '2026-04-02T00:00:00Z',
          escalated_from_action_id: 'action-0',
        },
      ],
    })
  })

  it('shows the current owner plus overdue and escalated routing state', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Requests needing my action' })).toBeInTheDocument()
    expect(screen.getByText('Attendance regularization')).toBeInTheDocument()
    expect(screen.getByText(/Owner: Ava Patel/)).toBeInTheDocument()
    expect(screen.getByText(/Routed via escalated from Nikhil Rao/i)).toBeInTheDocument()
    expect(screen.getByText('Overdue')).toBeInTheDocument()
    expect(screen.getByText('Escalated')).toBeInTheDocument()
  })
})
