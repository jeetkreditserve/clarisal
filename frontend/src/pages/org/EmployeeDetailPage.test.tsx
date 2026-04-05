import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EmployeeDetailPage } from '@/pages/org/EmployeeDetailPage'

const useApprovalWorkflows = vi.fn()
const useCompleteEmployeeOffboarding = vi.fn()
const useDeleteEmployee = vi.fn()
const useDepartments = vi.fn()
const useEmployeeDetail = vi.fn()
const useEmployeeDocumentDownload = vi.fn()
const useEmployeeDocumentRequests = vi.fn()
const useEmployeeDocuments = vi.fn()
const useEmployees = vi.fn()
const useEndEmployeeEmployment = vi.fn()
const useLocations = vi.fn()
const useMarkEmployeeJoined = vi.fn()
const useMarkEmployeeProbationComplete = vi.fn()
const useOrgFullAndFinalSettlements = vi.fn()
const useUpdateEmployee = vi.fn()
const useUpdateEmployeeOffboarding = vi.fn()
const useUpdateEmployeeOffboardingTask = vi.fn()

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/hooks/useOrgAdmin', () => ({
  useApprovalWorkflows: () => useApprovalWorkflows(),
  useCompleteEmployeeOffboarding: () => useCompleteEmployeeOffboarding(),
  useDeleteEmployee: () => useDeleteEmployee(),
  useDepartments: () => useDepartments(),
  useEmployeeDetail: (id: string) => useEmployeeDetail(id),
  useEmployeeDocumentDownload: () => useEmployeeDocumentDownload(),
  useEmployeeDocumentRequests: (id: string) => useEmployeeDocumentRequests(id),
  useEmployeeDocuments: (id: string) => useEmployeeDocuments(id),
  useEmployees: (...args: unknown[]) => useEmployees(...args),
  useEndEmployeeEmployment: (id: string) => useEndEmployeeEmployment(id),
  useLocations: () => useLocations(),
  useMarkEmployeeJoined: (id: string) => useMarkEmployeeJoined(id),
  useMarkEmployeeProbationComplete: (id: string) => useMarkEmployeeProbationComplete(id),
  useOrgFullAndFinalSettlements: () => useOrgFullAndFinalSettlements(),
  useUpdateEmployee: (id: string) => useUpdateEmployee(id),
  useUpdateEmployeeOffboarding: (id: string) => useUpdateEmployeeOffboarding(id),
  useUpdateEmployeeOffboardingTask: (id: string) => useUpdateEmployeeOffboardingTask(id),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/org/employees/emp-1']}>
      <Routes>
        <Route path="/org/employees/:id" element={<EmployeeDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('EmployeeDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useApprovalWorkflows.mockReturnValue({ data: [] })
    useDepartments.mockReturnValue({ data: [] })
    useEmployeeDocumentDownload.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({ url: 'https://example.com' }) })
    useEmployeeDocumentRequests.mockReturnValue({ data: [] })
    useEmployeeDocuments.mockReturnValue({ data: [] })
    useEmployees.mockReturnValue({ data: { results: [] } })
    useLocations.mockReturnValue({ data: [] })
    useOrgFullAndFinalSettlements.mockReturnValue({
      data: [
        {
          id: 'fnf-1',
          employee_id: 'emp-1',
          employee_name: 'Employee One',
          offboarding_process_id: 'off-1',
          last_working_day: '2026-05-31',
          status: 'APPROVED',
          prorated_salary: '25000.00',
          leave_encashment: '5000.00',
          gratuity: '10000.00',
          arrears: '2500.00',
          other_credits: '1500.00',
          tds_deduction: '1200.00',
          pf_deduction: '600.00',
          loan_recovery: '0.00',
          other_deductions: '300.00',
          gross_payable: '44000.00',
          net_payable: '41900.00',
          notes: 'Finance approved settlement.',
          approved_at: '2026-06-03T10:00:00Z',
          paid_at: null,
          created_at: '2026-06-01T10:00:00Z',
          modified_at: '2026-06-03T10:00:00Z',
        },
      ],
    })

    for (const hook of [
      useCompleteEmployeeOffboarding,
      useDeleteEmployee,
      useEndEmployeeEmployment,
      useMarkEmployeeJoined,
      useMarkEmployeeProbationComplete,
      useUpdateEmployee,
      useUpdateEmployeeOffboarding,
      useUpdateEmployeeOffboardingTask,
    ]) {
      hook.mockReturnValue({ isPending: false, mutateAsync: vi.fn().mockResolvedValue(undefined) })
    }

    useEmployeeDetail.mockReturnValue({
      isLoading: false,
      data: {
        id: 'emp-1',
        employee_code: 'EMP001',
        suggested_employee_code: 'EMP001',
        full_name: 'Employee One',
        email: 'employee.one@test.com',
        designation: 'Engineer',
        employment_type: 'FULL_TIME',
        date_of_joining: '2026-04-01',
        probation_end_date: '2026-07-01',
        date_of_exit: '2026-05-31',
        status: 'RESIGNED',
        onboarding_status: 'COMPLETE',
        department: null,
        office_location: null,
        reporting_to: null,
        profile: {},
        education_records: [],
        government_ids: [],
        bank_accounts: [],
        family_members: [],
        emergency_contacts: [],
        leave_approval_workflow_id: null,
        leave_approval_workflow_name: null,
        on_duty_approval_workflow_id: null,
        on_duty_approval_workflow_name: null,
        attendance_regularization_approval_workflow_id: null,
        attendance_regularization_approval_workflow_name: null,
        effective_approval_workflows: {
          leave: { workflow_id: null, workflow_name: 'Default Leave', source: 'DEFAULT' },
          on_duty: { workflow_id: null, workflow_name: 'Default On Duty', source: 'DEFAULT' },
          attendance_regularization: { workflow_id: null, workflow_name: 'Default Attendance', source: 'DEFAULT' },
        },
        offboarding: {
          id: 'off-1',
          status: 'IN_PROGRESS',
          exit_status: 'RESIGNED',
          date_of_exit: '2026-05-31',
          exit_reason: 'Personal',
          exit_notes: '',
          started_at: '2026-05-15T10:00:00Z',
          completed_at: null,
          required_task_count: 2,
          completed_required_task_count: 1,
          pending_required_task_count: 1,
          pending_document_requests: 0,
          has_primary_bank_account: true,
          tasks: [
            {
              id: 'task-1',
              code: 'CLEARANCE',
              title: 'Clearance',
              description: 'Collect laptop and access card',
              owner: 'IT',
              status: 'PENDING',
              note: '',
              due_date: '2026-05-31',
              is_required: true,
              completed_at: null,
              completed_by_name: '',
            },
          ],
        },
      },
    })
  })

  it('shows the full and final settlement summary inside offboarding', () => {
    renderPage()

    expect(screen.getByText('Full & Final Settlement')).toBeInTheDocument()
    expect(screen.getByText('Last working day: 2026-05-31')).toBeInTheDocument()
    expect(screen.getByText('₹41900.00')).toBeInTheDocument()
    expect(screen.getByText('Finance approved settlement.')).toBeInTheDocument()
    expect(screen.getByText('APPROVED')).toBeInTheDocument()
  })

  it('allows completing probation from employee detail', async () => {
    const user = userEvent.setup()
    const markProbationComplete = vi.fn().mockResolvedValue(undefined)
    useMarkEmployeeProbationComplete.mockReturnValue({ isPending: false, mutateAsync: markProbationComplete })

    renderPage()

    expect(screen.getByText('Probation ends')).toBeInTheDocument()
    expect(screen.getByText('2026-07-01')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Mark probation complete' }))
    await user.click(screen.getByRole('button', { name: 'Mark complete' }))

    await waitFor(() => {
      expect(markProbationComplete).toHaveBeenCalled()
    })
  })
})
