import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CandidateDetailPage } from '@/pages/org/CandidateDetailPage'

const {
  toastSuccess,
  toastError,
  fetchEmployees,
  fetchRecruitmentCandidate,
  scheduleRecruitmentInterview,
  createRecruitmentOffer,
  acceptRecruitmentOffer,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchEmployees: vi.fn(),
  fetchRecruitmentCandidate: vi.fn(),
  scheduleRecruitmentInterview: vi.fn(),
  createRecruitmentOffer: vi.fn(),
  acceptRecruitmentOffer: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/lib/api/org-admin', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/org-admin')>('@/lib/api/org-admin')
  return {
    ...actual,
    fetchEmployees,
  }
})

vi.mock('@/lib/api/recruitment', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/recruitment')>('@/lib/api/recruitment')
  return {
    ...actual,
    fetchRecruitmentCandidate,
    scheduleRecruitmentInterview,
    createRecruitmentOffer,
    acceptRecruitmentOffer,
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
      <MemoryRouter initialEntries={['/org/recruitment/candidates/candidate-1']}>
        <Routes>
          <Route path="/org/recruitment/candidates/:id" element={<CandidateDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CandidateDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchEmployees.mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 'employee-1',
          employee_code: 'EMP001',
          full_name: 'Asha Rao',
          email: 'asha@example.com',
          designation: 'Engineering Manager',
          employment_type: 'FULL_TIME',
          date_of_joining: '2025-01-01',
          status: 'ACTIVE',
          department_name: null,
          office_location_name: null,
        },
      ],
    })
    fetchRecruitmentCandidate.mockResolvedValue({
      id: 'candidate-1',
      first_name: 'Priya',
      last_name: 'Nair',
      full_name: 'Priya Nair',
      email: 'priya@example.com',
      phone: '',
      source: 'Referral',
      created_at: '2026-04-03T12:00:00Z',
      applications: [
        {
          id: 'app-1',
          candidate: 'candidate-1',
          candidate_name: 'Priya Nair',
          candidate_email: 'priya@example.com',
          job_posting_id: 'job-1',
          job_posting_title: 'Backend Engineer',
          stage: 'INTERVIEW',
          applied_at: '2026-04-03T12:00:00Z',
          notes: '',
          rejection_reason: '',
          interviews: [],
          offer_letter: null,
        },
      ],
    })
    scheduleRecruitmentInterview.mockResolvedValue({
      id: 'interview-1',
      application: 'app-1',
      interviewer_id: 'employee-1',
      interviewer_name: 'Asha Rao',
      scheduled_at: '2026-04-15T10:30:00Z',
      format: 'VIDEO',
      feedback: '',
      outcome: 'PENDING',
      meet_link: 'https://meet.example.com/round-1',
      created_at: '2026-04-03T13:00:00Z',
    })
    createRecruitmentOffer.mockResolvedValue({
      id: 'offer-1',
      application_id: 'app-1',
      ctc_annual: '1450000.00',
      joining_date: '2026-05-15',
      status: 'DRAFT',
      template_text: 'Offer summary',
      sent_at: null,
      accepted_at: null,
      expires_at: null,
      onboarded_employee_id: null,
    })
    acceptRecruitmentOffer.mockResolvedValue({
      employee_id: 'employee-99',
      status: 'INVITED',
    })
  })

  it('schedules an interview for the selected application', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Priya Nair')
    await user.selectOptions(screen.getByLabelText('Interviewer'), 'employee-1')
    await user.type(screen.getByLabelText('Scheduled at'), '2026-04-15T10:30')
    await user.type(screen.getByLabelText('Meet link'), 'https://meet.example.com/round-1')
    await user.click(screen.getByRole('button', { name: 'Schedule interview' }))

    await waitFor(() => {
      expect(scheduleRecruitmentInterview).toHaveBeenCalledWith('app-1', {
        interviewer_id: 'employee-1',
        scheduled_at: '2026-04-15T10:30',
        format: 'VIDEO',
        meet_link: 'https://meet.example.com/round-1',
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Interview scheduled.')
  })
})
