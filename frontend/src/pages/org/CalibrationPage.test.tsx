import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CalibrationPage } from '@/pages/org/CalibrationPage'

const {
  toastSuccess,
  toastError,
  createOrgCalibrationSession,
  adjustOrgCalibrationRating,
  lockOrgCalibrationSession,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  createOrgCalibrationSession: vi.fn(),
  adjustOrgCalibrationRating: vi.fn(),
  lockOrgCalibrationSession: vi.fn(),
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
    createOrgCalibrationSession,
    adjustOrgCalibrationRating,
    lockOrgCalibrationSession,
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
      <MemoryRouter initialEntries={['/org/performance/appraisals/cycle-1/calibration']}>
        <Routes>
          <Route path="/org/performance/appraisals/:id/calibration" element={<CalibrationPage />} />
          <Route path="/org/performance/appraisals" element={<div>Appraisal cycles page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CalibrationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    createOrgCalibrationSession.mockResolvedValue({
      id: 'session-1',
      cycle: 'cycle-1',
      locked_at: null,
      entries: [
        {
          id: 'entry-1',
          employee: 'employee-1',
          employee_name: 'Ava Patel',
          original_rating: 3.5,
          current_rating: 3.5,
          reason: '',
        },
      ],
    })
    adjustOrgCalibrationRating.mockResolvedValue({})
    lockOrgCalibrationSession.mockResolvedValue({
      id: 'session-1',
      cycle: 'cycle-1',
      locked_at: '2026-07-28T00:00:00Z',
      entries: [],
    })
  })

  it('updates a calibration rating and locks the session', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('Ava Patel')
    const ratingInput = screen.getByLabelText('Calibration rating for Ava Patel')
    await user.clear(ratingInput)
    await user.type(ratingInput, '4.5')
    await user.type(screen.getByPlaceholderText('Why is this rating changing?'), 'Raised after moderation')
    await user.click(screen.getByRole('button', { name: 'Save rating' }))

    await waitFor(() => {
      expect(adjustOrgCalibrationRating).toHaveBeenCalledWith('session-1', 'employee-1', {
        rating: 4.5,
        reason: 'Raised after moderation',
      })
    })

    await user.click(screen.getByRole('button', { name: 'Lock session' }))

    await waitFor(() => {
      expect(lockOrgCalibrationSession.mock.calls[0]?.[0]).toBe('session-1')
    })
  })
})
