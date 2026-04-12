import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AppraisalCyclesPage } from '@/pages/org/AppraisalCyclesPage'

const {
  toastSuccess,
  toastError,
  fetchOrgGoalCycles,
  fetchOrgAppraisalCycles,
  createOrgAppraisalCycle,
  activateOrgAppraisalCycle,
  advanceOrgAppraisalCycle,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchOrgGoalCycles: vi.fn(),
  fetchOrgAppraisalCycles: vi.fn(),
  createOrgAppraisalCycle: vi.fn(),
  activateOrgAppraisalCycle: vi.fn(),
  advanceOrgAppraisalCycle: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/lib/api/performance', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/performance')>('@/lib/api/performance')
  return {
    ...actual,
    fetchOrgGoalCycles,
    fetchOrgAppraisalCycles,
    createOrgAppraisalCycle,
    activateOrgAppraisalCycle,
    advanceOrgAppraisalCycle,
  }
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AppraisalCyclesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AppraisalCyclesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchOrgGoalCycles.mockResolvedValue([
      {
        id: 'goal-1',
        name: 'FY 2026 Goals',
        start_date: '2026-04-01',
        end_date: '2026-06-30',
        status: 'ACTIVE',
        auto_create_review_cycle: true,
        created_at: '2026-04-01T00:00:00Z',
      },
    ])
    fetchOrgAppraisalCycles.mockResolvedValue([
      {
        id: 'cycle-1',
        name: 'FY 2026 Review',
        review_type: '360',
        goal_cycle: 'goal-1',
        start_date: '2026-07-01',
        end_date: '2026-07-31',
        status: 'DRAFT',
        is_probation_review: false,
        self_assessment_deadline: '2026-07-07',
        peer_review_deadline: '2026-07-14',
        manager_review_deadline: '2026-07-21',
        calibration_deadline: '2026-07-28',
        activated_at: null,
        completed_at: null,
        completion_stats: {
          self_submitted: 0,
          self_total: 4,
          manager_submitted: 0,
          manager_total: 4,
          feedback_submitted: 0,
          feedback_total: 4,
        },
        created_at: '2026-06-25T00:00:00Z',
      },
    ])
    createOrgAppraisalCycle.mockResolvedValue({})
    activateOrgAppraisalCycle.mockResolvedValue({})
    advanceOrgAppraisalCycle.mockResolvedValue({})
  })

  it('creates an appraisal cycle with deadlines and linked goal cycle', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('FY 2026 Review')
    await user.type(screen.getByLabelText('Cycle name'), 'Mid-Year Review')
    await user.selectOptions(screen.getByLabelText('Linked goal cycle'), 'goal-1')
    await user.type(screen.getByLabelText('Start date'), '2026-07-01')
    await user.type(screen.getByLabelText('End date'), '2026-07-31')
    await user.type(screen.getByLabelText('Self-assessment deadline'), '2026-07-07')
    await user.type(screen.getByLabelText('Peer-review deadline'), '2026-07-14')
    await user.type(screen.getByLabelText('Manager-review deadline'), '2026-07-21')
    await user.type(screen.getByLabelText('Calibration deadline'), '2026-07-28')
    await user.click(screen.getByRole('button', { name: 'Create appraisal cycle' }))

    await waitFor(() => {
      expect(createOrgAppraisalCycle.mock.calls[0]?.[0]).toEqual({
        name: 'Mid-Year Review',
        review_type: '360',
        goal_cycle_id: 'goal-1',
        start_date: '2026-07-01',
        end_date: '2026-07-31',
        self_assessment_deadline: '2026-07-07',
        peer_review_deadline: '2026-07-14',
        manager_review_deadline: '2026-07-21',
        calibration_deadline: '2026-07-28',
      })
    })
  })

  it('activates a draft appraisal cycle', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('FY 2026 Review')
    await user.click(screen.getByRole('button', { name: 'Activate cycle' }))

    await waitFor(() => {
      expect(activateOrgAppraisalCycle.mock.calls[0]?.[0]).toBe('cycle-1')
    })
  })
})
