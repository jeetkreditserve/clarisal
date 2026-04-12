import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PayslipsPage } from '@/pages/employee/PayslipsPage'

const toastSuccess = vi.fn()
const toastError = vi.fn()
const useDownloadMyPayslip = vi.fn()
const useDownloadMyPayslipsForFiscalYear = vi.fn()
const useMyPayslips = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/hooks/useEmployeeSelf', () => ({
  useDownloadMyPayslip: () => useDownloadMyPayslip(),
  useDownloadMyPayslipsForFiscalYear: () => useDownloadMyPayslipsForFiscalYear(),
  useMyPayslips: (...args: unknown[]) => useMyPayslips(...args),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <PayslipsPage />
    </MemoryRouter>,
  )
}

describe('PayslipsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDownloadMyPayslip.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(new Blob(['pdf'])) })
    useDownloadMyPayslipsForFiscalYear.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(new Blob(['zip'])) })
  })

  it('renders payslips and filter controls', () => {
    useMyPayslips.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'payslip-1',
          employee_id: 'emp-1',
          pay_run_id: 'run-1',
          slip_number: 'PS/2026/04/001',
          period_year: 2026,
          period_month: 4,
          snapshot: { period_label: 'April 2026', gross_pay: '45000', total_deductions: '4000', net_pay: '41000', lines: [] },
          rendered_text: 'Rendered payslip text',
          created_at: '2026-04-30T00:00:00Z',
        },
      ],
    })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Payslips' })).toBeInTheDocument()
    expect(screen.getByLabelText('Fiscal year')).toBeInTheDocument()
    expect(screen.getByLabelText('Search slip number')).toBeInTheDocument()
    expect(screen.getByText('PS/2026/04/001')).toBeInTheDocument()
    expect(screen.queryByText('Raw generated text')).not.toBeInTheDocument()
  })

  it('downloads a fiscal year zip', async () => {
    const user = userEvent.setup()
    const downloadZip = vi.fn().mockResolvedValue(new Blob(['zip']))

    useDownloadMyPayslipsForFiscalYear.mockReturnValue({ isPending: false, mutateAsync: downloadZip })
    useMyPayslips.mockReturnValue({ isLoading: false, data: [] })

    renderPage()

    await user.click(screen.getByRole('button', { name: 'Download fiscal year ZIP' }))

    await waitFor(() => {
      expect(downloadZip).toHaveBeenCalledWith(expect.stringContaining('-'))
    })
    expect(toastSuccess).toHaveBeenCalledWith('Fiscal-year payslips downloaded.')
  })
})
