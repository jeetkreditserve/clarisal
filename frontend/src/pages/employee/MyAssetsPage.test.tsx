import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MyAssetsPage } from '@/pages/employee/MyAssetsPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useAcknowledgeMyAssetAssignment = vi.fn()
const useMyAssetAssignments = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useAcknowledgeMyAssetAssignment: () => useAcknowledgeMyAssetAssignment(),
  useMyAssetAssignments: () => useMyAssetAssignments(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <MyAssetsPage />
    </MemoryRouter>,
  )
}

describe('MyAssetsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAcknowledgeMyAssetAssignment.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockResolvedValue({}),
    })
  })

  it('renders assigned assets with acknowledgement actions', () => {
    useMyAssetAssignments.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'assignment-1',
          asset: 'asset-1',
          asset_name: 'MacBook Pro',
          asset_tag: 'LAP-300',
          employee: 'employee-1',
          employee_name: 'Rohan Mehta',
          employee_code: 'EMP300',
          assigned_at: '2026-04-10T09:00:00Z',
          acknowledged_at: null,
          expected_return_date: '2026-10-10',
          returned_at: null,
          condition_on_issue: 'GOOD',
          condition_on_return: null,
          status: 'ACTIVE',
          notes: 'Return to IT on exit.',
        },
      ],
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'My assets' })).toBeInTheDocument()
    expect(screen.getByText('MacBook Pro')).toBeInTheDocument()
    expect(screen.getByText(/LAP-300/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Acknowledge receipt' })).toBeInTheDocument()
  })

  it('acknowledges an assigned asset from the confirmation dialog', async () => {
    const user = userEvent.setup()
    const acknowledge = vi.fn().mockResolvedValue({})

    useAcknowledgeMyAssetAssignment.mockReturnValue({
      isPending: false,
      mutateAsync: acknowledge,
    })
    useMyAssetAssignments.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'assignment-1',
          asset: 'asset-1',
          asset_name: 'MacBook Pro',
          asset_tag: 'LAP-300',
          employee: 'employee-1',
          employee_name: 'Rohan Mehta',
          employee_code: 'EMP300',
          assigned_at: '2026-04-10T09:00:00Z',
          acknowledged_at: null,
          expected_return_date: '2026-10-10',
          returned_at: null,
          condition_on_issue: 'GOOD',
          condition_on_return: null,
          status: 'ACTIVE',
          notes: 'Return to IT on exit.',
        },
      ],
    })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Acknowledge receipt' }))
    await user.click(screen.getByRole('button', { name: 'Confirm acknowledgement' }))

    await waitFor(() => {
      expect(acknowledge).toHaveBeenCalledWith('assignment-1')
    })
    expect(toastSuccess).toHaveBeenCalledWith('Asset acknowledgement recorded.')
  })
})
