import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AssetsInventoryPage } from '@/pages/org/AssetsInventoryPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useAssetCategories = vi.fn()
const useAssetItems = vi.fn()
const useAssetMaintenance = vi.fn()
const useCreateAssetCategory = vi.fn()
const useCreateAssetItem = vi.fn()
const useCreateAssetMaintenance = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useAssetCategories: () => useAssetCategories(),
  useAssetItems: (...args: unknown[]) => useAssetItems(...args),
  useAssetMaintenance: () => useAssetMaintenance(),
  useCreateAssetCategory: () => useCreateAssetCategory(),
  useCreateAssetItem: () => useCreateAssetItem(),
  useCreateAssetMaintenance: () => useCreateAssetMaintenance(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <AssetsInventoryPage />
    </MemoryRouter>,
  )
}

describe('AssetsInventoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAssetCategories.mockReturnValue({
      data: [{ id: 'category-1', name: 'Laptops', description: 'Portable computers', is_active: true, created_at: '2026-04-10T00:00:00Z' }],
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
          lifecycle_status: 'ASSIGNED',
          notes: '',
          metadata: {},
          current_assignee: {
            id: 'employee-1',
            name: 'Rohan Mehta',
            employee_code: 'EMP300',
          },
          created_at: '2026-04-10T00:00:00Z',
        },
      ],
      isLoading: false,
    })
    useAssetMaintenance.mockReturnValue({
      data: [],
      isLoading: false,
    })
    useCreateAssetCategory.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({}) })
    useCreateAssetItem.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({}) })
    useCreateAssetMaintenance.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue({}) })
  })

  it('renders inventory sections with asset state and assignee context', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Asset inventory' })).toBeInTheDocument()
    expect(screen.getByText('MacBook Pro')).toBeInTheDocument()
    expect(screen.getByText('Rohan Mehta')).toBeInTheDocument()
    expect(screen.getByText('Category: Laptops')).toBeInTheDocument()
  })

  it('creates a new asset from the inventory form', async () => {
    const user = userEvent.setup()
    const createAsset = vi.fn().mockResolvedValue({})
    useCreateAssetItem.mockReturnValue({ isPending: false, mutateAsync: createAsset })

    renderPage()

    await user.type(screen.getByLabelText('Asset name'), 'ThinkPad X1')
    await user.type(screen.getByLabelText('Asset tag'), 'LAP-301')
    await user.type(screen.getByLabelText('Serial number'), 'SN-301')
    await user.click(screen.getByRole('button', { name: 'Add asset' }))

    await waitFor(() => {
      expect(createAsset).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'ThinkPad X1',
          asset_tag: 'LAP-301',
          serial_number: 'SN-301',
        }),
      )
    })
    expect(toastSuccess).toHaveBeenCalledWith('Asset added to inventory.')
  })
})
