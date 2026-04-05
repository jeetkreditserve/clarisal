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
const useCreateOrgArrear = vi.fn()
const useCreatePayrollRun = vi.fn()
const useCreatePayrollTdsChallan = vi.fn()
const useDownloadPayrollFiling = vi.fn()
const useEmployees = vi.fn()
const useFinalizePayrollRun = vi.fn()
const useGeneratePayrollFiling = vi.fn()
const useOrgArrears = vi.fn()
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
  useCreateOrgArrear: () => useCreateOrgArrear(),
  useCreatePayrollRun: () => useCreatePayrollRun(),
  useCreatePayrollTdsChallan: () => useCreatePayrollTdsChallan(),
  useDownloadPayrollFiling: () => useDownloadPayrollFiling(),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useFinalizePayrollRun: () => useFinalizePayrollRun(),
  useGeneratePayrollFiling: () => useGeneratePayrollFiling(),
  useOrgArrears: (...args: unknown[]) => useOrgArrears(...args),
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
          { id: 'slab-1', name: 'FY 2026-2027 New Regime Individual', fiscal_year: '2026-2027', is_old_regime: false, slabs: [{ id: 'slab-line-1' }] },
        ],
        compensation_templates: [],
        compensation_assignments: [],
        pay_runs: [],
        statutory_filing_batches: [],
        tds_challans: [],
        payslip_count: 0,
      },
    })
    useEmployees.mockReturnValue({ data: { results: [] } })
    useOrgArrears.mockReturnValue({ data: [] })

    for (const hook of [
      useCreateCompensationTemplate,
      useSubmitCompensationTemplate,
      useCreateCompensationAssignment,
      useCreateOrgArrear,
      useCreatePayrollTdsChallan,
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
    const fiscalYearInputs = screen.getAllByPlaceholderText('2026-2027')
    await user.clear(fiscalYearInputs[0])
    await user.type(fiscalYearInputs[0], '2026-2027')
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

  it('records a payroll TDS challan from the filings section', async () => {
    const user = userEvent.setup()
    const createTdsChallan = vi.fn().mockResolvedValue({ id: 'challan-1' })
    useCreatePayrollRun.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCreatePayrollTdsChallan.mockReturnValue({ isPending: false, mutateAsync: createTdsChallan })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Filings' }))
    await user.clear(screen.getByPlaceholderText('2026-2027'))
    await user.type(screen.getByPlaceholderText('2026-2027'), '2026-2027')
    await user.clear(screen.getByPlaceholderText('0510032'))
    await user.type(screen.getByPlaceholderText('0510032'), '0510032')
    await user.clear(screen.getByPlaceholderText('00004'))
    await user.type(screen.getByPlaceholderText('00004'), '00004')
    await user.clear(screen.getByPlaceholderText('3500.00'))
    await user.type(screen.getByPlaceholderText('3500.00'), '3500.00')
    await user.click(screen.getByRole('button', { name: 'Record TDS challan' }))

    await waitFor(() => {
      expect(createTdsChallan).toHaveBeenCalledWith(
        expect.objectContaining({
          fiscal_year: '2026-2027',
          bsr_code: '0510032',
          challan_serial_number: '00004',
          tax_deposited: '3500.00',
        }),
      )
    })
    expect(toastSuccess).toHaveBeenCalledWith('TDS challan recorded.')
  })

  it('records an arrear from the compensation section', async () => {
    const user = userEvent.setup()
    const createArrear = vi.fn().mockResolvedValue({ id: 'arrear-1' })

    useEmployees.mockReturnValue({
      data: {
        results: [{ id: 'employee-1', full_name: 'Ava Patel', designation: 'Engineer', employee_code: 'EMP001' }],
      },
    })
    useCreatePayrollRun.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    useCreateOrgArrear.mockReturnValue({ isPending: false, mutateAsync: createArrear })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Compensation' }))
    const employeeButtons = screen.getAllByRole('button', { name: 'Employee' })
    await user.click(employeeButtons[1])
    await user.click(screen.getByText('Ava Patel'))
    await user.clear(screen.getByLabelText('For period year'))
    await user.type(screen.getByLabelText('For period year'), '2026')
    await user.clear(screen.getByLabelText('For period month'))
    await user.type(screen.getByLabelText('For period month'), '3')
    await user.type(screen.getByLabelText('Reason'), 'Q4 correction')
    await user.type(screen.getByLabelText('Amount'), '4250.00')
    await user.click(screen.getByRole('button', { name: 'Record arrear' }))

    await waitFor(() => {
      expect(createArrear).toHaveBeenCalledWith({
        employee_id: 'employee-1',
        for_period_year: 2026,
        for_period_month: 3,
        reason: 'Q4 correction',
        amount: '4250.00',
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Arrear recorded.')
  })
})
