import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApprovalWorkflowsPage } from '@/pages/org/ApprovalWorkflowsPage'

const toastSuccess = vi.fn()
const useApprovalWorkflows = vi.fn()
const useApprovalInbox = vi.fn()
const useApprovalDelegations = vi.fn()
const useApproveApprovalAction = vi.fn()
const useCreateApprovalDelegation = vi.fn()
const useEmployees = vi.fn()
const useRejectApprovalAction = vi.fn()
const useUpdateApprovalDelegation = vi.fn()
const useCtOrgConfiguration = vi.fn()
const approveMutation = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useApprovalWorkflows: () => useApprovalWorkflows(),
  useApprovalInbox: () => useApprovalInbox(),
  useApprovalDelegations: () => useApprovalDelegations(),
  useApproveApprovalAction: () => useApproveApprovalAction(),
  useCreateApprovalDelegation: () => useCreateApprovalDelegation(),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useRejectApprovalAction: () => useRejectApprovalAction(),
  useUpdateApprovalDelegation: () => useUpdateApprovalDelegation(),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCtOrgConfiguration: (...args: unknown[]) => useCtOrgConfiguration(...args),
}))

function renderOrgPage(initialEntry = '/org/approval-workflows') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/org/approval-workflows" element={<ApprovalWorkflowsPage />} />
        <Route path="/org/approval-workflows/new" element={<div>Workflow builder route</div>} />
        <Route path="/ct/organisations/:organisationId/approval-workflows" element={<ApprovalWorkflowsPage />} />
        <Route path="/ct/organisations/:organisationId/approval-workflows/new" element={<div>CT workflow builder route</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ApprovalWorkflowsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useApprovalWorkflows.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'workflow-1',
          name: 'Default Leave Workflow',
          description: '',
          is_default: true,
          default_request_kind: 'LEAVE',
          is_active: true,
          rules: [{ request_kind: 'LEAVE' }],
          stages: [{ id: 'stage-1' }],
          modified_at: '2026-04-01T00:00:00Z',
        },
      ],
    })
    useApprovalInbox.mockReturnValue({
      data: [
        {
          id: 'action-1',
          request_kind: 'LEAVE',
          subject_label: 'Leave request',
          requester_name: 'Rohan Mehta',
          stage_name: 'Manager review',
          status: 'PENDING',
          owner_name: 'Ava Patel',
          assignment_source: 'DELEGATED',
          original_approver_name: 'Nikhil Rao',
          is_overdue: true,
          due_at: '2026-04-02T00:00:00Z',
          escalated_from_action_id: null,
        },
        {
          id: 'action-2',
          request_kind: 'EXPENSE_CLAIM',
          subject_label: 'Expense claim',
          requester_name: 'Ari Sharma',
          stage_name: 'Finance review',
          status: 'PENDING',
          owner_name: 'Ava Patel',
          assignment_source: 'PRIMARY',
          original_approver_name: null,
          is_overdue: false,
          due_at: '2026-04-03T00:00:00Z',
          escalated_from_action_id: null,
        },
      ],
    })
    useApprovalDelegations.mockReturnValue({
      data: [
        {
          id: 'delegation-1',
          delegator_employee: 'employee-1',
          delegator_employee_name: 'Ava Patel',
          delegate_employee: 'employee-2',
          delegate_employee_name: 'Nikhil Rao',
          request_kinds: ['LEAVE'],
          start_date: '2026-04-01',
          end_date: '2026-04-30',
          is_active: true,
        },
      ],
    })
    approveMutation.mockReset()
    useApproveApprovalAction.mockReturnValue({ isPending: false, mutateAsync: approveMutation })
    useCreateApprovalDelegation.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useEmployees.mockReturnValue({
      data: { results: [{ id: 'employee-1', full_name: 'Ava Patel', designation: 'Manager' }, { id: 'employee-2', full_name: 'Nikhil Rao', designation: 'Lead' }] },
    })
    useRejectApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useUpdateApprovalDelegation.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useCtOrgConfiguration.mockReturnValue({
      data: {
        approval_workflows: [
          {
            id: 'ct-workflow-1',
            name: 'CT Workflow',
            description: '',
            is_default: false,
            default_request_kind: null,
            is_active: true,
            rules: [],
            stages: [],
            modified_at: '2026-04-01T00:00:00Z',
          },
        ],
      },
      isLoading: false,
    })
  })

  it('renders org-admin workflow catalogue and switches to the inbox tab', async () => {
    const user = userEvent.setup()
    renderOrgPage()

    expect(screen.getByRole('heading', { name: 'Approvals' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Build workflow' })).toBeInTheDocument()
    expect(screen.getByText('Workflow catalogue')).toBeInTheDocument()
    expect(screen.getByText('Default LEAVE')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Inbox' }))

    expect(screen.getByText('Approval inbox')).toBeInTheDocument()
    expect(screen.getByText('Leave request')).toBeInTheDocument()
    expect(screen.getByText('Delegated')).toBeInTheDocument()
    expect(screen.getByText('Overdue')).toBeInTheDocument()
    expect(screen.getByText(/Routed via delegated from Nikhil Rao/i)).toBeInTheDocument()
  })

  it('uses the CT configuration route and hides the inbox tab in CT mode', () => {
    renderOrgPage('/ct/organisations/org-1/approval-workflows')

    expect(screen.getByRole('button', { name: 'Back to organisation' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Inbox' })).not.toBeInTheDocument()
    expect(screen.getByText('CT Workflow')).toBeInTheDocument()
  })

  it('shows delegation management in org settings', async () => {
    const user = userEvent.setup()
    renderOrgPage('/org/approval-workflows?tab=settings')

    expect(screen.getByText('Approval delegation')).toBeInTheDocument()
    expect(screen.getByText('Current delegations')).toBeInTheDocument()
    expect(screen.getByText('Ava Patel → Nikhil Rao')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Deactivate' }))

    expect(useUpdateApprovalDelegation().mutateAsync).toHaveBeenCalled()
  })

  it('bulk-approves selected leave requests from the inbox', async () => {
    const user = userEvent.setup()
    approveMutation.mockResolvedValue(undefined)

    renderOrgPage('/org/approval-workflows?tab=inbox')

    await user.click(screen.getByRole('checkbox', { name: 'Select leave request' }))
    await user.click(screen.getByRole('button', { name: 'Approve selected leave requests' }))
    await user.click(screen.getByRole('button', { name: 'Approve selected' }))

    expect(approveMutation).toHaveBeenCalledWith({
      actionId: 'action-1',
      comment: 'Bulk approved from the approval inbox.',
    })
    expect(approveMutation).toHaveBeenCalledTimes(1)
    expect(toastSuccess).toHaveBeenCalledWith('Selected leave requests approved.')
  })
})
