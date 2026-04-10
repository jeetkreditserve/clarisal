import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CtOrgPayrollPage } from '@/pages/ct/CtOrgPayrollPage'

const useCtOrgPayrollSummary = vi.fn()

vi.mock('@/hooks/useCtOrganisations', () => ({
  useCtOrgPayrollSummary: (...args: unknown[]) => useCtOrgPayrollSummary(...args),
}))

function renderPage(orgId = 'org-123') {
  return render(
    <MemoryRouter initialEntries={[`/ct/organisations/${orgId}/payroll`]}>
      <Routes>
        <Route path="/ct/organisations/:organisationId/payroll" element={<CtOrgPayrollPage />} />
        <Route path="/ct/organisations/:organisationId" element={<div>Organisation detail</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CtOrgPayrollPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows empty state when payroll data is unavailable', () => {
    useCtOrgPayrollSummary.mockReturnValue({ data: undefined, isLoading: false })
    renderPage()
    expect(screen.getByText('Payroll support data unavailable')).toBeInTheDocument()
  })

  it('renders payroll metrics and run history when data is available', () => {
    useCtOrgPayrollSummary.mockReturnValue({
      data: {
        tax_slab_set_count: 3,
        compensation_template_count: 5,
        approved_assignment_count: 10,
        pending_assignment_count: 4,
        payslip_count: 25,
        diagnostics: [],
        payroll_runs: [
          {
            id: 'run-1',
            name: 'April 2026 Run',
            period_year: 2026,
            period_month: 4,
            run_type: 'REGULAR',
            status: 'FINALIZED',
            created_at: '2026-04-05T10:00:00Z',
            calculated_at: '2026-04-05T10:30:00Z',
            submitted_at: '2026-04-05T11:00:00Z',
            finalized_at: '2026-04-05T11:30:00Z',
            ready_count: 12,
            exception_count: 0,
            exception_messages: [],
            attendance_snapshot_summary: {
              attendance_source: 'eSSL',
              period_start: '2026-04-01',
              period_end: '2026-04-30',
              use_attendance_inputs: true,
              employee_count: 12,
              ready_item_count: 12,
              exception_item_count: 0,
              total_attendance_paid_days: '26.00',
              total_lop_days: '2.00',
              total_overtime_minutes: 0,
            },
          },
        ],
      },
      isLoading: false,
    })
    renderPage()

    expect(screen.getByText('April 2026 Run')).toBeInTheDocument()
    expect(screen.getByText(/Tax slab sets/)).toBeInTheDocument()
    expect(screen.getByText(/Templates/)).toBeInTheDocument()
    expect(screen.getByText(/Approved assignments/)).toBeInTheDocument()
    expect(screen.getByText(/Pending assignments/)).toBeInTheDocument()
    expect(screen.getByText(/Payslips/)).toBeInTheDocument()
    expect(screen.getByText(/Attendance inputs: 26.00 paid days/)).toBeInTheDocument()
    expect(screen.getByText(/2\.00 LOP days/)).toBeInTheDocument()
    expect(screen.getByText(/Attendance-linked payable days: enabled/)).toBeInTheDocument()
  })

  it('shows exception diagnostics when present', () => {
    useCtOrgPayrollSummary.mockReturnValue({
      data: {
        tax_slab_set_count: 1,
        compensation_template_count: 2,
        approved_assignment_count: 5,
        pending_assignment_count: 1,
        payslip_count: 0,
        diagnostics: [
          {
            code: 'MISSING_COMPENSATION_ASSIGNMENT',
            title: 'Employees without compensation assignment',
            detail: '3 employees have no active salary structure.',
            action: 'Assign compensation templates to these employees.',
            severity: 'critical',
          },
        ],
        payroll_runs: [],
      },
      isLoading: false,
    })
    renderPage()

    expect(screen.getByText('Needs CT attention')).toBeInTheDocument()
    expect(screen.getByText('Employees without compensation assignment')).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
  })

  it('shows blocked run exception messages', () => {
    useCtOrgPayrollSummary.mockReturnValue({
      data: {
        tax_slab_set_count: 1,
        compensation_template_count: 1,
        approved_assignment_count: 0,
        pending_assignment_count: 5,
        payslip_count: 0,
        diagnostics: [],
        payroll_runs: [
          {
            id: 'run-blocked',
            name: 'March 2026 Run',
            period_year: 2026,
            period_month: 3,
            run_type: 'REGULAR',
            status: 'CALCULATED',
            created_at: '2026-03-05T10:00:00Z',
            calculated_at: '2026-03-05T10:30:00Z',
            submitted_at: null,
            finalized_at: null,
            ready_count: 8,
            exception_count: 2,
            exception_messages: [
              'Employee Alice has no PF account configured.',
              'Employee Bob salary template is missing.',
            ],
            attendance_snapshot_summary: {
              attendance_source: '',
              period_start: null,
              period_end: null,
              use_attendance_inputs: false,
              employee_count: 10,
              ready_item_count: 8,
              exception_item_count: 2,
              total_attendance_paid_days: '30.00',
              total_lop_days: '0.00',
              total_overtime_minutes: 0,
            },
          },
        ],
      },
      isLoading: false,
    })
    renderPage()

    expect(screen.getByText('March 2026 Run')).toBeInTheDocument()
    expect(screen.getByText('Why this run is blocked')).toBeInTheDocument()
    expect(screen.getByText('Employee Alice has no PF account configured.')).toBeInTheDocument()
    expect(screen.getByText('Employee Bob salary template is missing.')).toBeInTheDocument()
  })

  it('shows empty state for no payroll runs', () => {
    useCtOrgPayrollSummary.mockReturnValue({
      data: {
        tax_slab_set_count: 0,
        compensation_template_count: 0,
        approved_assignment_count: 0,
        pending_assignment_count: 0,
        payslip_count: 0,
        diagnostics: [],
        payroll_runs: [],
      },
      isLoading: false,
    })
    renderPage()

    expect(screen.getByText('No payroll runs yet')).toBeInTheDocument()
    expect(screen.getByText(/Once this organisation starts payroll preview/)).toBeInTheDocument()
  })
})
