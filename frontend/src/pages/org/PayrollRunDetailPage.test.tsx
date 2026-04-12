import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PayrollRunDetailPage } from '@/pages/org/PayrollRunDetailPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useDownloadPayslipPdf = vi.fn()
const useDownloadPayrollRunPayslipsZip = vi.fn()
const useFinalizePayrollRun = vi.fn()
const useNotifyPayrollRunPayslips = vi.fn()
const usePayrollRunDetail = vi.fn()
const usePayrollRunItems = vi.fn()
const useRerunPayrollRun = vi.fn()
const useSubmitPayrollRun = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useDownloadPayslipPdf: () => useDownloadPayslipPdf(),
  useDownloadPayrollRunPayslipsZip: () => useDownloadPayrollRunPayslipsZip(),
  useFinalizePayrollRun: () => useFinalizePayrollRun(),
  useNotifyPayrollRunPayslips: () => useNotifyPayrollRunPayslips(),
  usePayrollRunDetail: (...args: unknown[]) => usePayrollRunDetail(...args),
  usePayrollRunItems: (...args: unknown[]) => usePayrollRunItems(...args),
  useRerunPayrollRun: () => useRerunPayrollRun(),
  useSubmitPayrollRun: () => useSubmitPayrollRun(),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/org/payroll/runs/run-1']}>
      <Routes>
        <Route path="/org/payroll/runs/:id" element={<PayrollRunDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PayrollRunDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePayrollRunDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'run-1',
        name: 'April 2026 Payroll',
        status: 'FINALIZED',
        period_year: 2026,
        period_month: 4,
        total_gross: '32000.00',
        total_net: '30000.00',
        total_deductions: '2000.00',
        employee_count: 1,
        use_attendance_inputs: false,
      },
    })
    usePayrollRunItems.mockReturnValue({
      isLoading: false,
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'item-1',
            employee_id: 'employee-1',
            employee_name: 'Priya Sharma',
            employee_code: 'EMP001',
            department: 'People Ops',
            status: 'READY',
            gross_pay: '32000.00',
            epf_employee: '1800.00',
            esi_employee: '0.00',
            pt_monthly: '200.00',
            income_tax: '1800.00',
            lop_days: '0',
            net_pay: '30000.00',
            snapshot: { lines: [] },
          },
        ],
      },
    })
    useSubmitPayrollRun.mockReturnValue({ mutateAsync: vi.fn() })
    useFinalizePayrollRun.mockReturnValue({ mutateAsync: vi.fn() })
    useRerunPayrollRun.mockReturnValue({ mutateAsync: vi.fn() })
    useDownloadPayslipPdf.mockReturnValue({ isPending: false, mutateAsync: vi.fn() })
    useDownloadPayrollRunPayslipsZip.mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockResolvedValue({
        blob: new Blob(['zip']),
        filename: 'payslips-2026-04.zip',
      }),
    })
    useNotifyPayrollRunPayslips.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:test'),
      revokeObjectURL: vi.fn(),
    })
  })

  it('downloads and resends selected finalized payslips', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('checkbox', { name: 'Select Priya Sharma' }))
    await user.click(screen.getByRole('button', { name: 'Download selected payslips' }))

    await waitFor(() => {
      expect(useDownloadPayrollRunPayslipsZip().mutateAsync).toHaveBeenCalledWith({
        runId: 'run-1',
        item_ids: ['item-1'],
      })
    })

    await user.click(screen.getByRole('button', { name: 'Send selected payslip notices' }))
    await user.click(screen.getByRole('button', { name: 'Send selected' }))

    await waitFor(() => {
      expect(useNotifyPayrollRunPayslips().mutateAsync).toHaveBeenCalledWith({
        runId: 'run-1',
        item_ids: ['item-1'],
      })
    })
    expect(toastSuccess).toHaveBeenCalledWith('Selected payslip notices sent.')
  })

  it('requests the next run-item page from the API', async () => {
    const user = userEvent.setup()
    usePayrollRunItems.mockImplementation((_runId: string, params?: { page?: number }) => ({
      isLoading: false,
      data: {
        count: 75,
        next: params?.page === 2 ? null : 'next-page',
        previous: params?.page === 2 ? 'previous-page' : null,
        results: [
          {
            id: `item-${params?.page ?? 1}`,
            employee_id: `employee-${params?.page ?? 1}`,
            employee_name: `Employee Page ${params?.page ?? 1}`,
            employee_code: `EMP00${params?.page ?? 1}`,
            department: 'People Ops',
            status: 'READY',
            gross_pay: '32000.00',
            epf_employee: '1800.00',
            esi_employee: '0.00',
            pt_monthly: '200.00',
            income_tax: '1800.00',
            lop_days: '0',
            net_pay: '30000.00',
            snapshot: { lines: [] },
          },
        ],
      },
    }))

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Next page' }))

    await waitFor(() => {
      expect(usePayrollRunItems).toHaveBeenLastCalledWith('run-1', expect.objectContaining({ page: 2 }))
    })
    expect(screen.getByText('Employee Page 2')).toBeInTheDocument()
    expect(screen.getByText('Showing 21-21 of 75 items')).toBeInTheDocument()
  })

  it('uses the run exception count and requests exception rows from the API', async () => {
    const user = userEvent.setup()
    usePayrollRunDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'run-1',
        name: 'April 2026 Payroll',
        status: 'FINALIZED',
        period_year: 2026,
        period_month: 4,
        total_gross: '32000.00',
        total_net: '30000.00',
        total_deductions: '2000.00',
        employee_count: 75,
        exception_count: 3,
        use_attendance_inputs: false,
      },
    })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Show exceptions only' }))

    await waitFor(() => {
      expect(usePayrollRunItems).toHaveBeenLastCalledWith('run-1', expect.objectContaining({ has_exception: true, page: 1 }))
    })
  })

  it('only exposes row payslip PDF actions after finalization', () => {
    usePayrollRunDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'run-1',
        name: 'April 2026 Payroll',
        status: 'APPROVED',
        period_year: 2026,
        period_month: 4,
        total_gross: '32000.00',
        total_net: '30000.00',
        total_deductions: '2000.00',
        employee_count: 1,
        use_attendance_inputs: false,
      },
    })

    renderPage()

    expect(screen.queryByRole('button', { name: /Preview/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'PDF' })).not.toBeInTheDocument()
  })

  it('shows the employee EPF deduction column in the payroll table', () => {
    renderPage()

    expect(screen.getByText('EPF (Emp)')).toBeInTheDocument()
    const employeeRow = screen.getByText('Priya Sharma').closest('tr')
    expect(employeeRow).not.toBeNull()
    const cells = within(employeeRow as HTMLTableRowElement).getAllByRole('cell')
    expect(cells[4]).toHaveTextContent('₹1,800.00')
  })

  it('shows separate EPF and EPS employer contribution lines in the expanded row', async () => {
    const user = userEvent.setup()
    usePayrollRunItems.mockReturnValue({
      isLoading: false,
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'item-1',
            employee_id: 'employee-1',
            employee_name: 'Priya Sharma',
            employee_code: 'EMP001',
            department: 'People Ops',
            status: 'READY',
            gross_pay: '32000.00',
            esi_employee: '0.00',
            pt_monthly: '200.00',
            income_tax: '1800.00',
            lop_days: '0',
            net_pay: '30000.00',
            pf_employer: '1800.00',
            epf_employer: '550.50',
            eps_employer: '1249.50',
            snapshot: {
              lines: [
                {
                  component_type: 'EMPLOYER_CONTRIBUTION',
                  component_name: 'Employer PF (12.00% of PF Wages)',
                  monthly_amount: '1800.00',
                },
              ],
            },
          },
        ],
      },
    })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Expand payroll details for Priya Sharma' }))

    expect(screen.getByText('EPF (Employer)')).toBeInTheDocument()
    expect(screen.getByText('EPS')).toBeInTheDocument()
    expect(screen.queryByText('Employer PF (12.00% of PF Wages)')).not.toBeInTheDocument()
  })
})
