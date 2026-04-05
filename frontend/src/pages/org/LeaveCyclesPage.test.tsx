import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LeaveCyclesPage } from '@/pages/org/LeaveCyclesPage'

const toastSuccess = vi.fn()
const useCreateLeaveCycle = vi.fn()
const useLeaveCycles = vi.fn()
const useUpdateLeaveCycle = vi.fn()
const useCreateCtLeaveCycle = vi.fn()
const useCtOrgConfiguration = vi.fn()
const useUpdateCtLeaveCycle = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: vi.fn(),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useCreateLeaveCycle: () => useCreateLeaveCycle(),
  useLeaveCycles: () => useLeaveCycles(),
  useUpdateLeaveCycle: (...args: unknown[]) => useUpdateLeaveCycle(...args),
}))

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCreateCtLeaveCycle: (...args: unknown[]) => useCreateCtLeaveCycle(...args),
  useCtOrgConfiguration: (...args: unknown[]) => useCtOrgConfiguration(...args),
  useUpdateCtLeaveCycle: (...args: unknown[]) => useUpdateCtLeaveCycle(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/org/leave-cycles']}>
      <Routes>
        <Route path="/org/leave-cycles" element={<LeaveCyclesPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LeaveCyclesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useLeaveCycles.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'cycle-1',
          name: 'FY Leave Cycle',
          cycle_type: 'FINANCIAL_YEAR',
          start_month: 4,
          start_day: 1,
          is_default: true,
          is_active: true,
          leave_plan_count: 2,
          active_leave_plan_count: 2,
          modified_at: '2026-04-01T00:00:00Z',
        },
      ],
    })
    useCreateLeaveCycle.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useUpdateLeaveCycle.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCreateCtLeaveCycle.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useCtOrgConfiguration.mockReturnValue({ isLoading: false, data: undefined })
    useUpdateCtLeaveCycle.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
  })

  it('creates a new leave cycle from the modal', async () => {
    const user = userEvent.setup()
    const createMutation = vi.fn().mockResolvedValue(undefined)
    useCreateLeaveCycle.mockReturnValue({ isPending: false, mutateAsync: createMutation })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Add leave cycle' }))
    await user.clear(screen.getByLabelText('Cycle name'))
    await user.type(screen.getByLabelText('Cycle name'), 'Custom Leave Year')
    await user.click(screen.getByRole('button', { name: 'Save cycle' }))

    await waitFor(() => {
      expect(createMutation).toHaveBeenCalledWith({
        name: 'Custom Leave Year',
        cycle_type: 'CALENDAR_YEAR',
        start_month: 1,
        start_day: 1,
        is_default: true,
        is_active: true,
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Leave cycle created.')
  })

  it('edits an existing cycle and reveals custom fixed-start inputs', async () => {
    const user = userEvent.setup()

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Edit' }))
    await user.click(screen.getByRole('button', { name: 'Financial Year' }))
    await user.click(screen.getByRole('button', { name: 'Custom Fixed Start' }))

    expect(screen.getByLabelText('Start month')).toBeVisible()
    expect(screen.getByLabelText('Start day')).toBeVisible()
  })
})
