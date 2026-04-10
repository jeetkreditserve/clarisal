import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PayrollMastersPage } from '@/pages/ct/PayrollMastersPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

const useCtPayrollTaxSlabSets = vi.fn()
const useCreateCtPayrollTaxSlabSet = vi.fn()
const useUpdateCtPayrollTaxSlabSet = vi.fn()
const useDeleteCtPayrollTaxSlabSet = vi.fn()
const useCtPayrollStatutoryMasters = vi.fn()

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCtPayrollTaxSlabSets: (...args: unknown[]) => useCtPayrollTaxSlabSets(...args),
  useCreateCtPayrollTaxSlabSet: () => useCreateCtPayrollTaxSlabSet(),
  useUpdateCtPayrollTaxSlabSet: () => useUpdateCtPayrollTaxSlabSet(),
  useDeleteCtPayrollTaxSlabSet: () => useDeleteCtPayrollTaxSlabSet(),
  useCtPayrollStatutoryMasters: (...args: unknown[]) => useCtPayrollStatutoryMasters(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <PayrollMastersPage />
    </MemoryRouter>,
  )
}

const FY_NEW_INDIVIDUAL = {
  id: 'slab-set-new',
  name: 'India 2026-2027 New Regime (Individual)',
  fiscal_year: '2026-2027',
  is_old_regime: false,
  tax_category: 'INDIVIDUAL',
  slabs: [
    { id: 's1', min_income: '0', max_income: '400000', rate_percent: '0' },
    { id: 's2', min_income: '400001', max_income: '800000', rate_percent: '5' },
    { id: 's3', min_income: '800001', max_income: null, rate_percent: '10' },
  ],
}

const FY_OLD_INDIVIDUAL = {
  id: 'slab-set-old',
  name: 'India 2026-2027 Old Regime (Individual)',
  fiscal_year: '2026-2027',
  is_old_regime: true,
  tax_category: 'INDIVIDUAL',
  slabs: [
    { id: 's4', min_income: '0', max_income: '250000', rate_percent: '0' },
    { id: 's5', min_income: '250001', max_income: null, rate_percent: '20' },
  ],
}

describe('PayrollMastersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useCtPayrollTaxSlabSets.mockReturnValue({ data: [], isLoading: false })
    useCtPayrollStatutoryMasters.mockReturnValue({ data: undefined, isLoading: false })
    useCreateCtPayrollTaxSlabSet.mockReturnValue({ isPending: false, mutate: vi.fn() })
    useUpdateCtPayrollTaxSlabSet.mockReturnValue({ isPending: false, mutate: vi.fn() })
    useDeleteCtPayrollTaxSlabSet.mockReturnValue({ isPending: false, mutate: vi.fn() })
  })

  it('renders the page header and empty state when no masters exist', () => {
    renderPage()
    expect(screen.getByText('Payroll masters')).toBeInTheDocument()
    expect(screen.getByText(/No income tax masters yet/)).toBeInTheDocument()
  })

  it('renders slab sets grouped by fiscal year and regime', () => {
    useCtPayrollTaxSlabSets.mockReturnValue({
      data: [FY_NEW_INDIVIDUAL, FY_OLD_INDIVIDUAL],
      isLoading: false,
    })
    renderPage()

    expect(screen.getByText('FY 2026-2027')).toBeInTheDocument()
    expect(screen.getByText('New Regime')).toBeInTheDocument()
    expect(screen.getByText('Old Regime')).toBeInTheDocument()
    expect(screen.getByText('3 slabs')).toBeInTheDocument()
    expect(screen.getByText('2 slabs')).toBeInTheDocument()
  })

  it('opens the creation form when New master is clicked', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /New master/i }))

    expect(screen.getByText('New income tax master')).toBeInTheDocument()
    expect(screen.getByText('Format: YYYY-YYYY')).toBeInTheDocument()
  })

  it('pre-fills the fiscal year and category when clicking an empty master slot', async () => {
    const user = userEvent.setup()
    useCtPayrollTaxSlabSets.mockReturnValue({
      data: [FY_NEW_INDIVIDUAL],
      isLoading: false,
    })
    renderPage()

    await user.click(screen.getAllByRole('button', { name: /Add master/i })[0])

    expect(screen.getByText('New income tax master')).toBeInTheDocument()
  })

  it('opens the view modal when the eye button is clicked on a slab set', async () => {
    const user = userEvent.setup()
    useCtPayrollTaxSlabSets.mockReturnValue({
      data: [FY_NEW_INDIVIDUAL],
      isLoading: false,
    })
    renderPage()

    await user.click(screen.getAllByRole('button', { name: /View slabs/i })[0])

    expect(screen.getByText(/India 2026-2027 New Regime/)).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('5%')).toBeInTheDocument()
  })

  it('opens the edit form when the pencil button is clicked', async () => {
    const user = userEvent.setup()
    useCtPayrollTaxSlabSets.mockReturnValue({
      data: [FY_NEW_INDIVIDUAL],
      isLoading: false,
    })
    renderPage()

    await user.click(screen.getAllByRole('button', { name: /Edit slabs/i })[0])

    expect(screen.getByText('Edit income tax master')).toBeInTheDocument()
  })

  it('shows delete confirmation before calling the delete API', async () => {
    const user = userEvent.setup()
    useCtPayrollTaxSlabSets.mockReturnValue({
      data: [FY_NEW_INDIVIDUAL],
      isLoading: false,
    })
    renderPage()

    await user.click(screen.getAllByRole('button', { name: /Delete this master/i })[0])

    expect(screen.getByText('Delete?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Yes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /No/i })).toBeInTheDocument()
  })

  it('calls the delete API with the slab set ID when confirmed', async () => {
    const user = userEvent.setup()
    const deleteMutate = vi.fn()
    useCtPayrollTaxSlabSets.mockReturnValue({
      data: [FY_NEW_INDIVIDUAL],
      isLoading: false,
    })
    useDeleteCtPayrollTaxSlabSet.mockReturnValue({ isPending: false, mutate: deleteMutate })
    renderPage()

    await user.click(screen.getAllByRole('button', { name: /Delete this master/i })[0])
    await user.click(screen.getByRole('button', { name: /Yes/i }))

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalled()
      const [id] = deleteMutate.mock.calls[0]
      expect(id).toBe('slab-set-new')
    })
  })

  it('renders professional tax and LWF statutory sections', () => {
    const mockData = {
      professional_tax_rules: [
        {
          id: 'pt-mh',
          state_name: 'Maharashtra',
          state_code: 'MH',
          is_active: true,
          deduction_frequency: 'Monthly',
          effective_from: '2026-04-01',
          slabs: [
            { gender: 'MALE', min_income: '0', max_income: '7000', deduction_amount: '0', applicable_months: null },
            { gender: 'MALE', min_income: '7001', max_income: '10000', deduction_amount: '175', applicable_months: null },
          ],
        },
      ],
      labour_welfare_fund_rules: [
        {
          id: 'lwf-mh',
          state_name: 'Maharashtra',
          state_code: 'MH',
          is_active: true,
          deduction_frequency: 'Monthly',
          effective_from: '2026-04-01',
          contributions: [
            { min_wage: '0', max_wage: '25000', employee_amount: '24', employer_amount: '24', applicable_months: null },
          ],
        },
      ],
    }
    useCtPayrollStatutoryMasters.mockReturnValue({ data: mockData, isLoading: false })
    renderPage()

    expect(screen.getByText('Professional Tax rules')).toBeInTheDocument()
    expect(screen.getByText('Labour Welfare Fund rules')).toBeInTheDocument()
  })
})
