import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AssetAssignmentsPage } from '@/pages/org/AssetAssignmentsPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useAssetAssignments = vi.fn()
const useAssetItems = vi.fn()
const useCreateAssetAssignment = vi.fn()
const useEmployees = vi.fn()
const useMarkAssetAssignmentLost = vi.fn()
const useReturnAssetAssignment = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useAssetAssignments: (...args: unknown[]) => useAssetAssignments(...args),
  useAssetItems: (...args: unknown[]) => useAssetItems(...args),
  useCreateAssetAssignment: () => useCreateAssetAssignment(),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useMarkAssetAssignmentLost: () => useMarkAssetAssignmentLost(),
  useReturnAssetAssignment: () => useReturnAssetAssignment(),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/org/assets/assignments?employee=employee-1']}>
      <AssetAssignmentsPage />
    </MemoryRouter>,
  )
}

describe('AssetAssignmentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAssetAssignments.mockReturnValue({
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
          acknowledged_at: '2026-04-10T10:00:00Z',
          expected_return_date: '2026-10-10',
          returned_at: null,
          condition_on_issue: 'GOOD',
          condition_on_return: null,
          status: 'ACTIVE',
          notes: 'Return to IT on exit.',
        },
      ],
      isLoading: false,
    })
    useAssetItems.mockReturnValue({
      data: [
        {
          id: 'asset-1',
          name: 'MacBook Pro',
          asset_tag: 'LAP-300',
          serial_number: 'SN-123',
          vendor: 'Apple',
          category: 'category-1',
          category_name: 'Laptops',
          purchase_date: '2026-04-01',
          purchase_cost: '185000.00',
          warranty_expiry: '2029-04-01',
          condition: 'GOOD',
          lifecycle_status: 'AVAILABLE',
          notes: '',
          metadata: {},
          current_assignee: null,
          created_at: '2026-04-10T00:00:00Z',
        },
      ],
      isLoading: false,
    })
    useEmployees.mockReturnValue({
      data: {
        results: [{ id: 'employee-1', full_name: 'Rohan Mehta', designation: 'Engineer', employee_code: 'EMP300' }],
      },
      isLoading: false,
    })
    useCreateAssetAssignment.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({}) })
    useReturnAssetAssignment.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({}) })
    useMarkAssetAssignmentLost.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({}) })
  })

  it('renders active assignment rows and assignee filters', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Asset assignments' })).toBeInTheDocument()
    expect(screen.getAllByText('MacBook Pro').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Rohan Mehta/).length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Employee filter')).toBeInTheDocument()
  })

  it('returns an asset from the confirmation dialog', async () => {
    const user = userEvent.setup()
    const returnAsset = vi.fn().mockResolvedValue({})
    useReturnAssetAssignment.mockReturnValue({ isPending: false, mutateAsync: returnAsset })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Return asset' }))
    await user.click(screen.getByRole('button', { name: 'Confirm return' }))

    await waitFor(() => {
      expect(returnAsset).toHaveBeenCalledWith({
        id: 'assignment-1',
        payload: expect.objectContaining({ condition_on_return: 'GOOD' }),
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Asset return recorded.')
  })
})
