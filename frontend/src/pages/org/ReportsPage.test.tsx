import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ReportsPage } from '@/pages/org/ReportsPage'

const {
  toastLoading,
  toastSuccess,
  toastError,
  usePayrollSummary,
  downloadOrgReport,
} = vi.hoisted(() => ({
  toastLoading: vi.fn(() => 'toast-id'),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  usePayrollSummary: vi.fn(),
  downloadOrgReport: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    loading: toastLoading,
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  usePayrollSummary: () => usePayrollSummary(),
}))

vi.mock('@/lib/api/org-admin', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/org-admin')>('@/lib/api/org-admin')
  return {
    ...actual,
    downloadOrgReport,
  }
})

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePayrollSummary.mockReturnValue({
      data: {
        pay_runs: [
          { id: 'run-1', name: 'April 2026 Payroll', period_month: 4, period_year: 2026, status: 'FINALIZED' },
        ],
      },
    })
    downloadOrgReport.mockResolvedValue({
      blob: new Blob(['report']),
      filename: 'payroll-register.xlsx',
    })
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:report'),
      revokeObjectURL: vi.fn(),
    })
    HTMLAnchorElement.prototype.click = vi.fn()
  })

  it('downloads the payroll register with the selected pay run', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await user.selectOptions(screen.getByLabelText('Report type'), 'payroll-register')
    await user.selectOptions(screen.getByLabelText('Payroll run'), 'run-1')
    await user.click(screen.getByRole('button', { name: 'Download report' }))

    await waitFor(() => {
      expect(downloadOrgReport).toHaveBeenCalledWith('payroll-register', { pay_run_id: 'run-1' }, 'xlsx')
    })
    expect(toastSuccess).toHaveBeenCalled()
  })
})
