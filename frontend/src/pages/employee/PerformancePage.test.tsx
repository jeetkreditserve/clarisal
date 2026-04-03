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
  fetchMyReviews,
  updateMyGoalProgress,
  submitMyReview,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchMyGoals: vi.fn(),
  fetchMyReviews: vi.fn(),
  updateMyGoalProgress: vi.fn(),
  submitMyReview: vi.fn(),
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
    fetchMyReviews,
    updateMyGoalProgress,
    submitMyReview,
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
    fetchMyReviews.mockResolvedValue([
      {
        id: 'review-1',
        cycle: 'cycle-1',
        employee: 'employee-1',
        reviewer: 'employee-1',
        relationship: 'SELF',
        ratings: {},
        comments: '',
        status: 'PENDING',
        submitted_at: null,
      },
    ])
    updateMyGoalProgress.mockResolvedValue({})
    submitMyReview.mockResolvedValue({})
  })

  it('updates goal progress and submits a review', async () => {
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

    await user.type(screen.getByPlaceholderText('Write your appraisal comments'), 'Completed the planned milestone.')
    await user.click(screen.getByRole('button', { name: 'Submit review' }))

    await waitFor(() => {
      expect(submitMyReview).toHaveBeenCalledWith('review-1', {
        ratings: {},
        comments: 'Completed the planned milestone.',
      })
    })
  })
})
