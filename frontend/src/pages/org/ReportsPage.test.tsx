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
  useAuth,
} = vi.hoisted(() => ({
  toastLoading: vi.fn(() => 'toast-id'),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  usePayrollSummary: vi.fn(),
  downloadOrgReport: vi.fn(),
  useAuth: vi.fn(),
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

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => useAuth(),
}))

vi.mock('@/components/ui/AppDatePicker', () => ({
  AppDatePicker: ({ id, value = '', onValueChange, placeholder = 'Select date' }: { id?: string; value?: string; onValueChange: (value: string) => void; placeholder?: string }) => (
    <input
      id={id}
      data-testid="app-date-picker"
      aria-label={placeholder}
      value={value}
      onChange={(event) => onValueChange(event.target.value)}
    />
  ),
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
    useAuth.mockReturnValue({
      user: {
        effective_permissions: ['org.reports.read', 'org.reports.builder.manage', 'org.reports.export'],
      },
    })
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

  it('uses shared date pickers for attrition filters', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await user.selectOptions(screen.getByLabelText('Report type'), 'attrition')

    expect(screen.getAllByTestId('app-date-picker')).toHaveLength(2)
  })

  it('shows saved-template and builder actions only when the user can access them', () => {
    const { rerender } = render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /saved templates/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create report/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download report/i })).toBeInTheDocument()

    useAuth.mockReturnValue({
      user: {
        effective_permissions: ['org.reports.read'],
      },
    })

    rerender(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /saved templates/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^create report$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /download report/i })).not.toBeInTheDocument()
  })
})
