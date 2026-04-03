import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApprovalWorkflowsPage } from '@/pages/org/ApprovalWorkflowsPage'

const useApprovalWorkflows = vi.fn()
const useApprovalInbox = vi.fn()
const useApproveApprovalAction = vi.fn()
const useRejectApprovalAction = vi.fn()
const useCtOrgConfiguration = vi.fn()

vi.mock('@/hooks/useOrgAdmin', () => ({
  useApprovalWorkflows: () => useApprovalWorkflows(),
  useApprovalInbox: () => useApprovalInbox(),
  useApproveApprovalAction: () => useApproveApprovalAction(),
  useRejectApprovalAction: () => useRejectApprovalAction(),
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
          subject_label: 'Leave request',
          requester_name: 'Rohan Mehta',
          stage_name: 'Manager review',
          status: 'PENDING',
        },
      ],
    })
    useApproveApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useRejectApprovalAction.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
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
  })

  it('uses the CT configuration route and hides the inbox tab in CT mode', () => {
    renderOrgPage('/ct/organisations/org-1/approval-workflows')

    expect(screen.getByRole('button', { name: 'Back to organisation' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Inbox' })).not.toBeInTheDocument()
    expect(screen.getByText('CT Workflow')).toBeInTheDocument()
  })
})
