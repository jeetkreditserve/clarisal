import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TaxDeclarationsPage } from '@/pages/employee/TaxDeclarationsPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useCreateMyInvestmentDeclaration = vi.fn()
const useDeleteMyInvestmentDeclaration = vi.fn()
const useDownloadMyForm12BB = vi.fn()
const useMyInvestmentDeclarations = vi.fn()
const useUploadMyDocument = vi.fn()
const useUpdateMyInvestmentDeclaration = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useCreateMyInvestmentDeclaration: () => useCreateMyInvestmentDeclaration(),
  useDeleteMyInvestmentDeclaration: () => useDeleteMyInvestmentDeclaration(),
  useDownloadMyForm12BB: () => useDownloadMyForm12BB(),
  useMyInvestmentDeclarations: () => useMyInvestmentDeclarations(),
  useUploadMyDocument: () => useUploadMyDocument(),
  useUpdateMyInvestmentDeclaration: () => useUpdateMyInvestmentDeclaration(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <TaxDeclarationsPage />
    </MemoryRouter>,
  )
}

describe('TaxDeclarationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useCreateMyInvestmentDeclaration.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useDeleteMyInvestmentDeclaration.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useDownloadMyForm12BB.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(new Blob(['pdf'])) })
    useUploadMyDocument.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useUpdateMyInvestmentDeclaration.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
  })

  it('renders declarations for the selected fiscal year', () => {
    useMyInvestmentDeclarations.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'decl-1',
          employee_id: 'emp-1',
          employee_name: 'Aarav Shah',
          fiscal_year: '2026-2027',
          section: '80C',
          description: 'PPF',
          declared_amount: '150000.00',
          proof_file_key: '',
          proof_document_id: null,
          proof_document_file_name: null,
          proof_document_url: null,
          is_verified: true,
          verified_by_id: 'admin-1',
          verified_by_name: 'Payroll Admin',
          section_limit: '150000.00',
          created_at: '2026-04-01T00:00:00Z',
          modified_at: '2026-04-02T00:00:00Z',
        },
      ],
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Tax declarations' })).toBeInTheDocument()
    expect(screen.getByText('PPF')).toBeInTheDocument()
    expect(screen.getByText('Reviewed by Payroll Admin')).toBeInTheDocument()
    expect(screen.getByText('Verified')).toBeInTheDocument()
    expect(screen.getByText('Proof document')).toBeInTheDocument()
    expect(screen.queryByLabelText('Proof file key')).not.toBeInTheDocument()
  })

  it('creates a new declaration', async () => {
    const user = userEvent.setup()
    const createDeclaration = vi.fn().mockResolvedValue(undefined)

    useCreateMyInvestmentDeclaration.mockReturnValue({ isPending: false, mutateAsync: createDeclaration })
    useMyInvestmentDeclarations.mockReturnValue({ isLoading: false, data: [] })

    renderPage()

    await user.type(screen.getByLabelText('Description'), 'Mediclaim premium')
    await user.type(screen.getByLabelText('Declared amount'), '25000.00')
    await user.click(screen.getByRole('button', { name: 'Save declaration' }))

    await waitFor(() => {
      expect(createDeclaration).toHaveBeenCalledWith({
        fiscal_year: expect.stringContaining('-'),
        section: '80C',
        description: 'Mediclaim premium',
        declared_amount: '25000.00',
        proof_document_id: null,
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Tax declaration saved.')
  })
})
