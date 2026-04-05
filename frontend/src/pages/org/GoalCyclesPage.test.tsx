import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { GoalCyclesPage } from '@/pages/org/GoalCyclesPage'

const {
  toastSuccess,
  toastError,
  fetchOrgGoalCycles,
  createOrgGoalCycle,
} = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  fetchOrgGoalCycles: vi.fn(),
  createOrgGoalCycle: vi.fn(),
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
    createOrgGoalCycle,
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
        <GoalCyclesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('GoalCyclesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchOrgGoalCycles.mockResolvedValue([])
    createOrgGoalCycle.mockResolvedValue({
      id: 'cycle-1',
      name: 'Q2 2026',
      start_date: '2026-04-01',
      end_date: '2026-06-30',
      status: 'DRAFT',
      created_at: '2026-04-03T00:00:00Z',
    })
  })

  it('creates a goal cycle', async () => {
    const user = userEvent.setup()

    renderPage()

    await screen.findByText('No goal cycles yet')
    await user.type(screen.getByLabelText('Cycle name'), 'Q2 2026')
    await user.type(screen.getByLabelText('Start date'), '2026-04-01')
    await user.type(screen.getByLabelText('End date'), '2026-06-30')
    await user.click(screen.getByRole('button', { name: 'Create goal cycle' }))

    await waitFor(() => {
      expect(createOrgGoalCycle.mock.calls[0]?.[0]).toEqual({
        name: 'Q2 2026',
        start_date: '2026-04-01',
        end_date: '2026-06-30',
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Goal cycle created.')
  })
})
