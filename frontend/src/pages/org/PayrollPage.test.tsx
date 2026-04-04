import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PayrollPage } from '@/pages/org/PayrollPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

const useCancelPayrollFiling = vi.fn()
const useCalculatePayrollRun = vi.fn()
const useCreateCompensationAssignment = vi.fn()
const useCreateCompensationTemplate = vi.fn()
const useCreatePayrollRun = vi.fn()
const useCreatePayrollTaxSlabSet = vi.fn()
const useDownloadPayrollFiling = vi.fn()
const useEmployees = vi.fn()
const useFinalizePayrollRun = vi.fn()
const useGeneratePayrollFiling = vi.fn()
const usePayrollSummary = vi.fn()
const useRegeneratePayrollFiling = vi.fn()
const useRerunPayrollRun = vi.fn()
const useSubmitCompensationAssignment = vi.fn()
const useSubmitCompensationTemplate = vi.fn()
const useSubmitPayrollRun = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useCancelPayrollFiling: () => useCancelPayrollFiling(),
  useCalculatePayrollRun: () => useCalculatePayrollRun(),
  useCreateCompensationAssignment: () => useCreateCompensationAssignment(),
  useCreateCompensationTemplate: () => useCreateCompensationTemplate(),
  useCreatePayrollRun: () => useCreatePayrollRun(),
  useCreatePayrollTaxSlabSet: () => useCreatePayrollTaxSlabSet(),
  useDownloadPayrollFiling: () => useDownloadPayrollFiling(),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useFinalizePayrollRun: () => useFinalizePayrollRun(),
  useGeneratePayrollFiling: () => useGeneratePayrollFiling(),
  usePayrollSummary: () => usePayrollSummary(),
  useRegeneratePayrollFiling: () => useRegeneratePayrollFiling(),
  useRerunPayrollRun: () => useRerunPayrollRun(),
  useSubmitCompensationAssignment: () => useSubmitCompensationAssignment(),
  useSubmitCompensationTemplate: () => useSubmitCompensationTemplate(),
  useSubmitPayrollRun: () => useSubmitPayrollRun(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <PayrollPage />
    </MemoryRouter>,
  )
}

describe('PayrollPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    usePayrollSummary.mockReturnValue({
      isLoading: false,
      data: {
        tax_slab_sets: [
          { id: 'slab-1', name: 'FY 2026-2027', source_set_id: null, fiscal_year: '2026-2027', slabs: [{ id: 'slab-line-1' }] },
        ],
        compensation_templates: [],
        compensation_assignments: [],
        pay_runs: [],
        statutory_filing_batches: [],
        payslip_count: 0,
      },
    })
    useEmployees.mockReturnValue({ data: { results: [] } })

    for (const hook of [
      useCreatePayrollTaxSlabSet,
      useCreateCompensationTemplate,
      useSubmitCompensationTemplate,
      useCreateCompensationAssignment,
      useSubmitCompensationAssignment,
      useCalculatePayrollRun,
      useSubmitPayrollRun,
      useFinalizePayrollRun,
      useRerunPayrollRun,
      useGeneratePayrollFiling,
      useRegeneratePayrollFiling,
      useCancelPayrollFiling,
      useDownloadPayrollFiling,
    ]) {
      hook.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    }
  })

  it('renders payroll summary metrics and setup guidance', () => {
    useCreatePayrollRun.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Payroll control room' })).toBeInTheDocument()
    expect(screen.getByText('Payroll workspace sections')).toBeInTheDocument()
    expect(screen.getByText('Tax slab sets')).toBeInTheDocument()
    expect(screen.getByText('Setup guidance')).toBeInTheDocument()
  })

  it('creates a payroll run from the runs section', async () => {
    const user = userEvent.setup()
    const createRun = vi.fn().mockResolvedValue(undefined)
    useCreatePayrollRun.mockReturnValue({ isPending: false, mutateAsync: createRun })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Runs' }))
    await user.clear(screen.getByPlaceholderText('Year'))
    await user.type(screen.getByPlaceholderText('Year'), '2026')
    await user.clear(screen.getByPlaceholderText('Month'))
    await user.type(screen.getByPlaceholderText('Month'), '4')
    await user.click(screen.getByRole('button', { name: 'Create payroll run' }))

    await waitFor(() => {
      expect(createRun).toHaveBeenCalledWith({
        period_year: 2026,
        period_month: 4,
        use_attendance_inputs: false,
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Payroll run created.')
  })

  it('generates a statutory filing from the filings section', async () => {
    const user = userEvent.setup()
    const generateFiling = vi.fn().mockResolvedValue({ status: 'GENERATED' })
    useCreatePayrollRun.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useGeneratePayrollFiling.mockReturnValue({ isPending: false, mutateAsync: generateFiling })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Filings' }))
    await user.selectOptions(screen.getByDisplayValue('PF ECR'), 'FORM16')
    await user.clear(screen.getByDisplayValue(/\d{4}-\d{4}/))
    await user.type(screen.getByPlaceholderText('2026-2027'), '2026-2027')
    await user.click(screen.getByRole('button', { name: 'Generate filing' }))

    await waitFor(() => {
      expect(generateFiling).toHaveBeenCalledWith({
        filing_type: 'FORM16',
        fiscal_year: '2026-2027',
        artifact_format: 'PDF',
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Statutory filing generated.')
  })
})
