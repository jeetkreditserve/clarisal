import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { JobPostingsPage } from '@/pages/org/JobPostingsPage'

const {
  toastSuccess,
  toastError,
  fetchRecruitmentJobPostings,
  createRecruitmentJobPosting,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchRecruitmentJobPostings: vi.fn(),
  createRecruitmentJobPosting: vi.fn(),
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
    fetchRecruitmentJobPostings,
    createRecruitmentJobPosting,
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
        <JobPostingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('JobPostingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchRecruitmentJobPostings.mockResolvedValue([])
    createRecruitmentJobPosting.mockResolvedValue({
      id: 'job-1',
      title: 'Senior Backend Engineer',
      department_id: null,
      department_name: null,
      location_id: null,
      location_name: null,
      description: 'Build ATS workflows',
      requirements: 'Django',
      status: 'DRAFT',
      posted_at: null,
      closes_at: null,
      application_count: 0,
      created_at: '2026-04-03T12:00:00Z',
    })
  })

  it('creates a new job posting', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('No job postings yet')
    await user.type(screen.getByLabelText('Title'), 'Senior Backend Engineer')
    await user.type(screen.getByLabelText('Description'), 'Build ATS workflows')
    await user.type(screen.getByLabelText('Requirements'), 'Django')
    await user.click(screen.getByRole('button', { name: 'Create posting' }))

    await waitFor(() => {
      expect(createRecruitmentJobPosting.mock.calls[0]?.[0]).toEqual({
        title: 'Senior Backend Engineer',
        description: 'Build ATS workflows',
        requirements: 'Django',
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Job posting created.')
  })
})
