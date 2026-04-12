import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PerformancePage } from '@/pages/employee/PerformancePage'

const {
  toastSuccess,
  toastError,
  fetchMyGoals,
  fetchMyReviewCycles,
  fetchMyFeedbackSummary,
  fetchMyReviews,
  updateMyGoalProgress,
  saveMySelfAssessment,
  submitMySelfAssessment,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchMyGoals: vi.fn(),
  fetchMyReviewCycles: vi.fn(),
  fetchMyFeedbackSummary: vi.fn(),
  fetchMyReviews: vi.fn(),
  updateMyGoalProgress: vi.fn(),
  saveMySelfAssessment: vi.fn(),
  submitMySelfAssessment: vi.fn(),
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
    fetchMyGoals,
    fetchMyReviewCycles,
    fetchMyFeedbackSummary,
    fetchMyReviews,
    updateMyGoalProgress,
    saveMySelfAssessment,
    submitMySelfAssessment,
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
        <PerformancePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PerformancePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchMyGoals.mockResolvedValue([
      {
        id: 'goal-1',
        cycle: 'cycle-1',
        employee: 'employee-1',
        title: 'Ship performance module',
        description: 'Build the first release.',
        target: '',
        metric: '',
        weight: '1.00',
        status: 'IN_PROGRESS',
        due_date: null,
        progress_percent: 50,
        created_at: '2026-04-03T00:00:00Z',
      },
    ])
    fetchMyReviewCycles.mockResolvedValue([
      {
        id: 'cycle-1',
        name: 'FY 2026 Review',
        review_type: '360',
        status: 'MANAGER_REVIEW',
        start_date: '2026-07-01',
        end_date: '2026-07-31',
        self_assessment_deadline: '2026-07-07',
        peer_review_deadline: '2026-07-14',
        manager_review_deadline: '2026-07-21',
        calibration_deadline: '2026-07-28',
        feedback_summary_visible: true,
        self_assessment: {
          id: 'review-1',
          cycle: 'cycle-1',
          cycle_name: 'FY 2026 Review',
          cycle_status: 'MANAGER_REVIEW',
          employee: 'employee-1',
          reviewer: 'employee-1',
          relationship: 'SELF',
          ratings: { overall: 4 },
          comments: 'Delivered the milestone.',
          status: 'IN_PROGRESS',
          submitted_at: null,
        },
      },
    ])
    fetchMyFeedbackSummary.mockResolvedValue({
      response_count: 1,
      dimensions: {
        ownership: { avg: 4.5, count: 1 },
      },
      comments: ['Strong cross-team partner.'],
    })
    fetchMyReviews.mockResolvedValue([
      {
        id: 'review-2',
        cycle: 'cycle-1',
        cycle_name: 'FY 2026 Review',
        cycle_status: 'COMPLETED',
        employee: 'employee-1',
        reviewer: 'manager-1',
        relationship: 'MANAGER',
        ratings: { overall: 4 },
        comments: 'Consistent delivery.',
        status: 'SUBMITTED',
        submitted_at: '2026-07-25T00:00:00Z',
      },
    ])
    updateMyGoalProgress.mockResolvedValue({})
    saveMySelfAssessment.mockResolvedValue({})
    submitMySelfAssessment.mockResolvedValue({})
  })

  it('updates goal progress and saves then submits a self-assessment', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Ship performance module')
    const progressInput = screen.getByLabelText('Progress for Ship performance module')
    await user.clear(progressInput)
    await user.type(progressInput, '75')
    await user.click(screen.getByRole('button', { name: 'Save progress' }))

    await waitFor(() => {
      expect(updateMyGoalProgress).toHaveBeenCalledWith('goal-1', 75)
    })

    const commentsInput = screen.getByPlaceholderText('Write your self-assessment comments')
    await user.clear(commentsInput)
    await user.type(commentsInput, 'Completed the planned milestone.')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))

    await waitFor(() => {
      expect(saveMySelfAssessment).toHaveBeenCalledWith('cycle-1', {
        ratings: { overall: 4 },
        comments: 'Completed the planned milestone.',
      })
    })

    await user.click(screen.getByRole('button', { name: 'Submit self-assessment' }))

    await waitFor(() => {
      expect(submitMySelfAssessment).toHaveBeenCalledWith('cycle-1', {
        ratings: { overall: 4 },
        comments: 'Completed the planned milestone.',
      })
    })

    expect(await screen.findByText('Strong cross-team partner.')).toBeInTheDocument()
    expect(await screen.findByText('Consistent delivery.')).toBeInTheDocument()
  })
})
