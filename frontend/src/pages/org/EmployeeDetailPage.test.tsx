import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EmployeeDetailPage } from '@/pages/org/EmployeeDetailPage'

const useApprovalWorkflows = vi.fn()
const useCompleteEmployeeOffboarding = vi.fn()
const useCustomFieldDefinitions = vi.fn()
const useDeleteEmployee = vi.fn()
const useDepartments = vi.fn()
const useDesignations = vi.fn()
const useEmployeeCustomFieldValues = vi.fn()
const useEmployeeDetail = vi.fn()
const useEmployeeCareerTimeline = vi.fn()
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
const useUpdateEmployeeCustomFieldValues = vi.fn()
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
  useCustomFieldDefinitions: () => useCustomFieldDefinitions(),
  useDeleteEmployee: () => useDeleteEmployee(),
  useDepartments: () => useDepartments(),
  useDesignations: () => useDesignations(),
  useEmployeeCustomFieldValues: (id: string) => useEmployeeCustomFieldValues(id),
  useEmployeeDetail: (id: string) => useEmployeeDetail(id),
  useEmployeeCareerTimeline: (id: string) => useEmployeeCareerTimeline(id),
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
  useUpdateEmployeeCustomFieldValues: (id: string) => useUpdateEmployeeCustomFieldValues(id),
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
    useCustomFieldDefinitions.mockReturnValue({
      data: [
        {
          id: 'field-1',
          name: 'Shirt size',
          field_key: 'shirt_size',
          field_type: 'TEXT',
          placement: 'CUSTOM',
          is_required: false,
          display_order: 1,
          dropdown_options: [],
          placeholder: 'Enter shirt size',
          help_text: 'Used for welcome kit orders.',
          is_active: true,
          created_at: '2026-04-01T00:00:00Z',
        },
      ],
    })
    useDepartments.mockReturnValue({ data: [] })
    useDesignations.mockReturnValue({ data: [{ id: 'des-1', name: 'Engineer', level: 1, is_active: true }] })
    useEmployeeCustomFieldValues.mockReturnValue({
      data: [
        {
          id: 'value-1',
          field_definition: 'field-1',
          field_name: 'Shirt size',
          field_type: 'TEXT',
          value_text: 'M',
          value_number: null,
          value_date: null,
          value_boolean: false,
          display_value: 'M',
        },
      ],
    })
    useEmployeeDocumentDownload.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({ url: 'https://example.com' }) })
    useEmployeeCareerTimeline.mockReturnValue({ isLoading: false, data: [] })
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
      useUpdateEmployeeCustomFieldValues,
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
        expense_approval_workflow_id: null,
        expense_approval_workflow_name: null,
        effective_approval_workflows: {
          leave: { workflow_id: null, workflow_name: 'Default Leave', source: 'DEFAULT' },
          on_duty: { workflow_id: null, workflow_name: 'Default On Duty', source: 'DEFAULT' },
          attendance_regularization: { workflow_id: null, workflow_name: 'Default Attendance', source: 'DEFAULT' },
          expense_claim: { workflow_id: null, workflow_name: 'Default Expense', source: 'DEFAULT' },
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
          asset_summary: {
            active_assignments: 1,
            returned_assignments: 0,
            has_unresolved: true,
            unresolved_assets: [
              {
                id: 'assignment-1',
                asset_id: 'asset-1',
                asset_name: 'MacBook Pro',
                asset_tag: 'LAP-300',
                category_name: 'Laptops',
                assigned_at: '2026-05-01T10:00:00Z',
                expected_return_date: '2026-05-31',
              },
            ],
          },
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

  it('renders the employee career timeline when career events are available', () => {
    useEmployeeCareerTimeline.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 'promotion-1',
          type: 'PROMOTION',
          date: '2026-06-01',
          status: 'APPROVED',
          from_department: 'People Operations',
          to_department: 'People Operations',
          from_location: 'Registered Office',
          to_location: 'Registered Office',
          from_designation: 'Engineer',
          to_designation: 'Senior Engineer',
          has_compensation_change: true,
          reason: 'Strong performance',
          requested_by: 'Aditi Rao',
          approved_by: 'Rohan Mehta',
        },
      ],
    })

    renderPage()

    expect(screen.getByText('Career timeline')).toBeInTheDocument()
    expect(screen.getByText('Promotion')).toBeInTheDocument()
    expect(screen.getByText(/Engineer → Senior Engineer/)).toBeInTheDocument()
    expect(screen.getByText('Compensation revision included')).toBeInTheDocument()
    expect(screen.getByText(/Rohan Mehta/)).toBeInTheDocument()
  })

  it('renders and updates custom employee fields', async () => {
    const user = userEvent.setup()
    renderPage()

    const customFieldInput = screen.getByLabelText('Shirt size')
    expect(customFieldInput).toHaveValue('M')

    await user.clear(customFieldInput)
    await user.type(customFieldInput, 'L')
    await user.click(screen.getByRole('button', { name: 'Save custom fields' }))

    await waitFor(() => {
      expect(useUpdateEmployeeCustomFieldValues('emp-1').mutateAsync).toHaveBeenCalledWith({
        custom_fields: [
          {
            field_definition_id: 'field-1',
            value_text: 'L',
            value_number: null,
            value_date: null,
            value_boolean: false,
          },
        ],
      })
    })
  })
})
