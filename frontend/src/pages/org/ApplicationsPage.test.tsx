import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApplicationsPage } from '@/pages/org/ApplicationsPage'

const {
  toastSuccess,
  toastError,
  fetchRecruitmentApplications,
  advanceRecruitmentApplicationStage,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchRecruitmentApplications: vi.fn(),
  advanceRecruitmentApplicationStage: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/lib/api/recruitment', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/recruitment')>('@/lib/api/recruitment')
  return {
    ...actual,
    fetchRecruitmentApplications,
    advanceRecruitmentApplicationStage,
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
        <ApplicationsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ApplicationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRecruitmentApplications.mockResolvedValue([
      {
        id: 'app-1',
        candidate: 'candidate-1',
        candidate_name: 'Priya Nair',
        candidate_email: 'priya@example.com',
        job_posting_id: 'job-1',
        job_posting_title: 'Backend Engineer',
        stage: 'APPLIED',
        applied_at: '2026-04-03T12:00:00Z',
        notes: '',
        rejection_reason: '',
        interviews: [],
        offer_letter: null,
      },
    ])
    advanceRecruitmentApplicationStage.mockResolvedValue({
      id: 'app-1',
      stage: 'SCREENING',
    })
  })

  it('updates an application stage', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Priya Nair')
    await user.selectOptions(screen.getByLabelText('Move Priya Nair to stage'), 'SCREENING')
    await user.click(screen.getByRole('button', { name: 'Update stage' }))

    await waitFor(() => {
      expect(advanceRecruitmentApplicationStage).toHaveBeenCalledWith('app-1', 'SCREENING')
    })
    expect(toastSuccess).toHaveBeenCalledWith('Application stage updated.')
  })
})
