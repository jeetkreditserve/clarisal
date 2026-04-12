import { render, screen, waitFor, within } from '@testing-library/react'
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
  convertRecruitmentCandidate,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchEmployees: vi.fn(),
  fetchRecruitmentCandidate: vi.fn(),
  scheduleRecruitmentInterview: vi.fn(),
  createRecruitmentOffer: vi.fn(),
  acceptRecruitmentOffer: vi.fn(),
  convertRecruitmentCandidate: vi.fn(),
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
    convertRecruitmentCandidate,
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
      converted_to_employee_id: null,
      converted_to_employee_name: null,
      converted_at: null,
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
    convertRecruitmentCandidate.mockResolvedValue({
      employee: {
        id: 'employee-99',
        employee_code: 'EMP099',
        full_name: 'Priya Nair',
        email: 'priya@example.com',
        designation: 'Backend Engineer',
        employment_type: 'FULL_TIME',
        date_of_joining: '2026-05-15',
        probation_end_date: null,
        status: 'INVITED',
        department_name: null,
        office_location_name: null,
      },
      message: 'Candidate converted to employee invite for priya@example.com',
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

  it('shows a convert action when the offer is accepted but the employee invite is not created yet', async () => {
    fetchRecruitmentCandidate.mockResolvedValue({
      id: 'candidate-1',
      first_name: 'Priya',
      last_name: 'Nair',
      full_name: 'Priya Nair',
      email: 'priya@example.com',
      phone: '',
      source: 'Referral',
      converted_to_employee_id: null,
      converted_to_employee_name: null,
      converted_at: null,
      created_at: '2026-04-03T12:00:00Z',
      applications: [
        {
          id: 'app-1',
          candidate: 'candidate-1',
          candidate_name: 'Priya Nair',
          candidate_email: 'priya@example.com',
          job_posting_id: 'job-1',
          job_posting_title: 'Backend Engineer',
          stage: 'OFFER',
          applied_at: '2026-04-03T12:00:00Z',
          notes: '',
          rejection_reason: '',
          interviews: [],
          offer_letter: {
            id: 'offer-1',
            application_id: 'app-1',
            ctc_annual: '1450000.00',
            joining_date: '2026-05-15',
            status: 'ACCEPTED',
            template_text: 'Offer summary',
            sent_at: null,
            accepted_at: '2026-04-10T12:00:00Z',
            expires_at: null,
            onboarded_employee_id: null,
          },
        },
      ],
    })

    renderPage()

    expect(await screen.findByRole('button', { name: 'Convert to employee' })).toBeInTheDocument()
  })

  it('hides the convert action while the offer is not accepted', async () => {
    fetchRecruitmentCandidate.mockResolvedValue({
      id: 'candidate-1',
      first_name: 'Priya',
      last_name: 'Nair',
      full_name: 'Priya Nair',
      email: 'priya@example.com',
      phone: '',
      source: 'Referral',
      converted_to_employee_id: null,
      converted_to_employee_name: null,
      converted_at: null,
      created_at: '2026-04-03T12:00:00Z',
      applications: [
        {
          id: 'app-1',
          candidate: 'candidate-1',
          candidate_name: 'Priya Nair',
          candidate_email: 'priya@example.com',
          job_posting_id: 'job-1',
          job_posting_title: 'Backend Engineer',
          stage: 'OFFER',
          applied_at: '2026-04-03T12:00:00Z',
          notes: '',
          rejection_reason: '',
          interviews: [],
          offer_letter: {
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
          },
        },
      ],
    })

    renderPage()

    await screen.findByText('Priya Nair')
    expect(screen.queryByRole('button', { name: 'Convert to employee' })).not.toBeInTheDocument()
  })

  it('confirms offer details before converting the candidate', async () => {
    const user = userEvent.setup()
    fetchRecruitmentCandidate.mockResolvedValue({
      id: 'candidate-1',
      first_name: 'Priya',
      last_name: 'Nair',
      full_name: 'Priya Nair',
      email: 'priya@example.com',
      phone: '',
      source: 'Referral',
      converted_to_employee_id: null,
      converted_to_employee_name: null,
      converted_at: null,
      created_at: '2026-04-03T12:00:00Z',
      applications: [
        {
          id: 'app-1',
          candidate: 'candidate-1',
          candidate_name: 'Priya Nair',
          candidate_email: 'priya@example.com',
          job_posting_id: 'job-1',
          job_posting_title: 'Backend Engineer',
          stage: 'OFFER',
          applied_at: '2026-04-03T12:00:00Z',
          notes: '',
          rejection_reason: '',
          interviews: [],
          offer_letter: {
            id: 'offer-1',
            application_id: 'app-1',
            ctc_annual: '1450000.00',
            joining_date: '2026-05-15',
            status: 'ACCEPTED',
            template_text: 'Offer summary',
            sent_at: null,
            accepted_at: '2026-04-10T12:00:00Z',
            expires_at: null,
            onboarded_employee_id: null,
          },
        },
      ],
    })

    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Convert to employee' }))

    const dialog = screen.getByRole('dialog', { name: 'Convert Candidate to Employee' })
    expect(within(dialog).getByText(/Priya Nair/)).toBeInTheDocument()
    expect(within(dialog).getByText(/priya@example.com/)).toBeInTheDocument()
    expect(within(dialog).getByText(/Backend Engineer/)).toBeInTheDocument()
    expect(within(dialog).getByText(/1450000.00/)).toBeInTheDocument()
    expect(within(dialog).getByText(/2026-05-15/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Convert & Send Invite' }))

    await waitFor(() => {
      expect(convertRecruitmentCandidate).toHaveBeenCalled()
    })
    expect(convertRecruitmentCandidate.mock.calls[0][0]).toBe('candidate-1')
    expect(toastSuccess).toHaveBeenCalledWith('Candidate converted to employee invite for priya@example.com')
  })

  it('shows the converted employee link when the handoff is complete', async () => {
    fetchRecruitmentCandidate.mockResolvedValue({
      id: 'candidate-1',
      first_name: 'Priya',
      last_name: 'Nair',
      full_name: 'Priya Nair',
      email: 'priya@example.com',
      phone: '',
      source: 'Referral',
      converted_to_employee_id: 'employee-99',
      converted_to_employee_name: 'Priya Nair',
      converted_at: '2026-04-10T12:00:00Z',
      created_at: '2026-04-03T12:00:00Z',
      applications: [
        {
          id: 'app-1',
          candidate: 'candidate-1',
          candidate_name: 'Priya Nair',
          candidate_email: 'priya@example.com',
          job_posting_id: 'job-1',
          job_posting_title: 'Backend Engineer',
          stage: 'HIRED',
          applied_at: '2026-04-03T12:00:00Z',
          notes: '',
          rejection_reason: '',
          interviews: [],
          offer_letter: {
            id: 'offer-1',
            application_id: 'app-1',
            ctc_annual: '1450000.00',
            joining_date: '2026-05-15',
            status: 'ACCEPTED',
            template_text: 'Offer summary',
            sent_at: null,
            accepted_at: '2026-04-10T12:00:00Z',
            expires_at: null,
            onboarded_employee_id: 'employee-99',
          },
        },
      ],
    })

    renderPage()

    const link = await screen.findByRole('link', { name: 'Converted: Priya Nair' })
    expect(link).toHaveAttribute('href', '/org/employees/employee-99')
  })
})
