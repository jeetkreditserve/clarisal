import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NoticesPage } from '@/pages/org/NoticesPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

const useNotices = vi.fn()
const usePublishNotice = vi.fn()
const useCtOrgConfiguration = vi.fn()
const usePublishCtNotice = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useNotices: (...args: unknown[]) => useNotices(...args),
  usePublishNotice: () => usePublishNotice(),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCtOrgConfiguration: (...args: unknown[]) => useCtOrgConfiguration(...args),
  usePublishCtNotice: (...args: unknown[]) => usePublishCtNotice(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/org/notices']}>
      <Routes>
        <Route path="/org/notices" element={<NoticesPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('NoticesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useNotices.mockReturnValue({
      data: [
        {
          id: 'notice-1',
          title: 'Payroll run tonight',
          body: 'Review the final lock checklist.',
          category: 'OPERATIONS',
          audience_type: 'ALL_EMPLOYEES',
          status: 'SCHEDULED',
          is_sticky: true,
          automation_state: 'WAITING_TO_PUBLISH',
          is_automation_blocked: true,
          scheduled_for: '2026-04-10T09:00:00Z',
          expires_at: '2026-04-09T09:00:00Z',
          modified_at: '2026-04-01T10:00:00Z',
        },
      ],
      isLoading: false,
    })
    usePublishNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCtOrgConfiguration.mockReturnValue({ data: undefined, isLoading: false })
    usePublishCtNotice.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('shows automation state and blocked lifecycle warnings', async () => {
    const user = userEvent.setup()
    const publishNotice = vi.fn().mockResolvedValue(undefined)
    usePublishNotice.mockReturnValue({ isPending: false, mutateAsync: publishNotice })

    renderPage()

    expect(screen.getByText('Automation blocked')).toBeInTheDocument()
    expect(screen.getAllByText('1').length).toBeGreaterThan(0)
    expect(screen.getByText('Waiting To Publish')).toBeInTheDocument()
    expect(
      screen.getByText(/Automation is blocked. Review the schedule or expiry window/i),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Publish' }))

    await waitFor(() => {
      expect(publishNotice).toHaveBeenCalledWith('notice-1')
    })
    expect(toastSuccess).toHaveBeenCalledWith('Notice published.')
  })
})
